"""Ollama client for local LLM integration."""
import httpx
import json
from typing import Optional, Tuple, List, Dict
from .config import Config
from .database import db
from .websocket import ws_manager

import logging
logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with local Ollama instance."""
    
    DEFAULT_MODEL = 'llama3.1'
    
    def __init__(self):
        self._available_models: List[str] = []
        self._last_model_fetch = 0
    
    @property
    def base_url(self) -> str:
        """Get base URL for Ollama (allows runtime updates)."""
        # Use host.docker.internal for Docker to access host's Ollama
        return Config.OLLAMA_URL
    
    @property
    def model(self) -> str:
        """Get current model name."""
        return Config.OLLAMA_MODEL or self.DEFAULT_MODEL
    
    def get_available_models(self) -> List[Dict]:
        """
        Get list of available models from Ollama.
        
        Returns:
            List of model info dicts with 'name', 'size', 'modified_at'
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get('models', [])
                    
                    # Extract model info
                    result = []
                    for model in models:
                        result.append({
                            'name': model.get('name', ''),
                            'size': model.get('size', 0),
                            'modified_at': model.get('modified_at', ''),
                            'digest': model.get('digest', '')[:12] if model.get('digest') else ''
                        })
                    
                    # Cache model names
                    self._available_models = [m['name'] for m in result]
                    logger.info(f"Found {len(result)} Ollama models: {self._available_models}")
                    return result
                else:
                    logger.error(f"Failed to get models: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching Ollama models: {e}")
            return []
    
    def pull_model(self, model_name: str) -> Tuple[bool, Optional[str]]:
        """
        Pull a model from Ollama library.
        
        Args:
            model_name: Name of model to pull (e.g., 'llama3.1', 'mistral')
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            db.add_log('info', 'ollama_pull', f'Pulling model: {model_name}')
            
            with httpx.Client(timeout=600.0) as client:  # Long timeout for large models
                response = client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name, "stream": False}
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully pulled model: {model_name}")
                    db.add_log('info', 'ollama_pull_complete', f'Pulled model: {model_name}')
                    return True, None
                else:
                    error = f"Failed to pull model: {response.status_code} - {response.text}"
                    logger.error(error)
                    return False, error
        except httpx.TimeoutException:
            return False, "Model pull timed out (this can take several minutes for large models)"
        except Exception as e:
            error = f"Error pulling model: {str(e)}"
            logger.error(error)
            return False, error
    
    def _get_ollama_response(self, text: str, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Internal method to get response from Ollama."""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": text,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 256,
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('response', '').strip(), None
                else:
                    return None, f"Ollama Error: {response.status_code}"
        except Exception as e:
            return None, str(e)

    def _get_groq_response(self, text: str, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Internal method to get response from Groq."""
        if not Config.GROQ_API_KEY:
            return None, "No Groq API key configured"
            
        try:
            headers = {
                "Authorization": f"Bearer {Config.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Using configured Groq LLM model
            model = Config.GROQ_LLM_MODEL 
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": text}],
                        "temperature": 0.7,
                        "max_completion_tokens": 256
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get('choices', [])
                    if choices:
                        return choices[0].get('message', {}).get('content', '').strip(), None
                    return None, "Empty response from Groq"
                else:
                    return None, f"Groq Error: {response.status_code} - {response.text}"
        except Exception as e:
            return None, str(e)

    async def get_response(self, text: str, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str], str]:
        """
        Get a response from LLM with fallback (Async).
        Returns: (response_text, error_message, model_used)
        """
        if not text:
            return None, "Empty input text", "none"
        
        # 1. Try Ollama (Async)
        try:
            db.add_log('info', 'llm_request_ollama', f'Prompt: {text[:50]}...', call_id)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": text,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 256}
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    res_text = data.get('response', '').strip()
                    if res_text:
                        return res_text, None, f"Ollama ({self.model})"
                    else:
                        raise Exception("Empty response")
                else:
                    raise Exception(f"Status {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"Ollama async failed: {e}. Trying Groq fallback.")

        # 2. Try Groq (Async logic, but reusing sync method for now as it's a fallback)
        # Ideally should use async http here too, but for quick fix:
        try:
            return await asyncio.to_thread(self.get_response_sync, text, call_id)
        except Exception as e:
            return None, f"All providers failed. {e}", "none"

    def get_response_sync(self, text: str, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str], str]:
        """
        Synchronous version of get_response with fallback to Groq.
        Returns: (response_text, error_message, model_used)
        """
        if not text:
            return None, "Empty input text", "none"

        # 1. Try Ollama
        try:
            db.add_log('info', 'llm_request', f'Trying Ollama ({self.model})...', call_id)
            logger.info(f"Sending to Ollama ({self.model})...")
            
            response, error = self._get_ollama_response(text, call_id)
            if response:
                db.add_log('info', 'llm_response', f'Ollama response: {response[:50]}...', call_id)
                return response, None, f"Ollama ({self.model})"
            
            logger.warning(f"Ollama failed: {error}. Failing over to Groq...")
        except Exception as e:
            logger.error(f"Ollama exception: {e}")
        
        # 2. Fallback to Groq
        try:
            db.add_log('info', 'llm_fallback', 'Trying Groq fallback...', call_id)
            response, error = self._get_groq_response(text, call_id)
            if response:
                db.add_log('info', 'llm_response_groq', f'Groq response: {response[:50]}...', call_id)
                return response, None, f"Groq ({Config.GROQ_LLM_MODEL})"
            
            logger.error(f"Groq failed: {error}")
            return None, f"All providers failed. Ollama: {error}", "none"
        except Exception as e:
            logger.error(f"Groq exception: {e}")
            return None, f"All providers failed with exception: {e}", "none"

    def _get_ollama_chat_response(self, messages: list, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Internal method to get chat response from Ollama."""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 256}
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get('message', {}).get('content', '').strip(), None
                else:
                    return None, f"Ollama Error: {response.status_code}"
        except Exception as e:
            return None, str(e)

    def _get_groq_chat_response(self, messages: list, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Internal method to get chat response from Groq."""
        if not Config.GROQ_API_KEY:
            return None, "No Groq API key configured"
        try:
            headers = {
                "Authorization": f"Bearer {Config.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            model = Config.GROQ_LLM_MODEL
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_completion_tokens": 256
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get('choices', [])
                    if choices:
                        return choices[0].get('message', {}).get('content', '').strip(), None
                    return None, "Empty response from Groq"
                else:
                    return None, f"Groq Error: {response.status_code} - {response.text}"
        except Exception as e:
            return None, str(e)

    def get_chat_response_sync(self, messages: list, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str], str]:
        """
        Get response using chat endpoint with fallback.
        Returns: (response_text, error_message, model_used)
        """
        if not messages:
            return None, "No messages provided", "none"

        # 1. Try Ollama
        try:
            db.add_log('info', 'llm_chat_request', f'Trying Ollama ({self.model})...', call_id)
            response, error = self._get_ollama_chat_response(messages, call_id)
            if response:
                return response, None, f"Ollama ({self.model})"
            logger.warning(f"Ollama chat failed: {error}. Failing over to Groq...")
        except Exception as e:
            logger.error(f"Ollama chat exception: {e}")

        # 2. Fallback to Groq
        try:
            db.add_log('info', 'llm_chat_fallback', 'Trying Groq fallback...', call_id)
            # Check if messages need any format adjustment? 
            # Both standard format is {role:..., content:...}, mostly compatible.
            response, error = self._get_groq_chat_response(messages, call_id)
            if response:
                return response, None, f"Groq ({Config.GROQ_LLM_MODEL})"
            return None, f"All providers failed. Ollama: {error}", "none"
        except Exception as e:
            logger.error(f"Groq chat exception: {e}")
            return None, f"All providers failed with exception: {e}", "none"

    def check_health(self) -> bool:
        """Check if Ollama is accessible."""
        # We only check Ollama health for now as it's the primary
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(self.base_url)
                return response.status_code == 200
        except:
            return False


# Global client instance
gpt_client = OllamaClient()
