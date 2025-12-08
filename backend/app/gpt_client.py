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
    
    async def get_response(self, text: str, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Get a response from Ollama.
        
        Args:
            text: The input text/question
            call_id: Optional call ID for logging
        
        Returns:
            Tuple of (response_text, error_message)
        """
        if not text:
            return None, "Empty input text"
        
        try:
            db.add_log('info', 'ollama_request', f'Model: {self.model}, Prompt: {text[:100]}...', call_id)
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": text,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 256,  # Limit response length for voice
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '').strip()
                    
                    if response_text:
                        db.add_log('info', 'ollama_response', f'Received: {response_text[:100]}...', call_id)
                        return response_text, None
                    else:
                        return None, "Empty response from Ollama"
                else:
                    error = f"Ollama API error: {response.status_code} - {response.text}"
                    db.add_log('error', 'ollama_failed', error, call_id)
                    return None, error
        
        except httpx.TimeoutException:
            error = "Ollama request timed out"
            db.add_log('error', 'ollama_failed', error, call_id)
            return None, error
        except httpx.ConnectError:
            error = f"Cannot connect to Ollama at {self.base_url}"
            db.add_log('error', 'ollama_failed', error, call_id)
            return None, error
        except Exception as e:
            error = f"Ollama error: {str(e)}"
            db.add_log('error', 'ollama_failed', error, call_id)
            return None, error
    
    def get_response_sync(self, text: str, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Synchronous version of get_response.

        Args:
            text: The input text/question
            call_id: Optional call ID for logging

        Returns:
            Tuple of (response_text, error_message)
        """
        if not text:
            return None, "Empty input text"

        try:
            db.add_log('info', 'ollama_request', f'Model: {self.model}, Prompt: {text[:100]}...', call_id)
            logger.info(f"Sending to Ollama ({self.model}): {text[:100]}...")

            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": text,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 256,  # Limit response length for voice
                        }
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '').strip()

                    if response_text:
                        logger.info(f"Ollama response: {response_text[:100]}...")
                        db.add_log('info', 'ollama_response', f'Received: {response_text[:100]}...', call_id)
                        return response_text, None
                    else:
                        return None, "Empty response from Ollama"
                else:
                    error = f"Ollama API error: {response.status_code} - {response.text}"
                    logger.error(error)
                    db.add_log('error', 'ollama_failed', error, call_id)
                    return None, error

        except httpx.TimeoutException:
            error = "Ollama request timed out"
            logger.error(error)
            db.add_log('error', 'ollama_failed', error, call_id)
            return None, error
        except httpx.ConnectError:
            error = f"Cannot connect to Ollama at {self.base_url}"
            logger.error(error)
            db.add_log('error', 'ollama_failed', error, call_id)
            return None, error
        except Exception as e:
            error = f"Ollama error: {str(e)}"
            logger.error(error)
            db.add_log('error', 'ollama_failed', error, call_id)
            return None, error

    def get_chat_response_sync(self, messages: list, call_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Get response using Ollama chat endpoint with conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            call_id: Optional call ID for logging

        Returns:
            Tuple of (response_text, error_message)
        """
        if not messages:
            return None, "No messages provided"

        try:
            logger.info(f"Sending chat to Ollama ({self.model}) with {len(messages)} messages")

            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 256,  # Limit response length for voice
                        }
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    message = data.get('message', {})
                    response_text = message.get('content', '').strip()

                    if response_text:
                        logger.info(f"Ollama chat response: {response_text[:100]}...")
                        db.add_log('info', 'ollama_response', f'Received: {response_text[:100]}...', call_id)
                        return response_text, None
                    else:
                        return None, "Empty response from Ollama"
                else:
                    error = f"Ollama API error: {response.status_code} - {response.text}"
                    logger.error(error)
                    db.add_log('error', 'ollama_failed', error, call_id)
                    return None, error

        except httpx.TimeoutException:
            error = "Ollama request timed out"
            logger.error(error)
            db.add_log('error', 'ollama_failed', error, call_id)
            return None, error
        except httpx.ConnectError:
            error = f"Cannot connect to Ollama at {self.base_url}"
            logger.error(error)
            db.add_log('error', 'ollama_failed', error, call_id)
            return None, error
        except Exception as e:
            error = f"Ollama error: {str(e)}"
            logger.error(error)
            db.add_log('error', 'ollama_failed', error, call_id)
            return None, error
    
    def check_health(self) -> bool:
        """Check if Ollama is accessible and responding."""
        try:
            with httpx.Client(timeout=5.0) as client:
                # Ollama root endpoint returns version info
                response = client.get(self.base_url)
                if response.status_code == 200:
                    logger.debug("Ollama health check passed")
                    return True
                
                # Also try the tags endpoint
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False


# Global client instance (keeping name for compatibility)
gpt_client = OllamaClient()
