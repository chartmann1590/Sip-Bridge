"""TTS client for openai-edge-tts integration."""
import io
import httpx
from typing import Optional, Tuple

from .config import Config
from .database import db
from .websocket import ws_manager


class TTSClient:
    """Client for interacting with openai-edge-tts service."""
    
    def __init__(self):
        pass
    
    @property
    def base_url(self) -> str:
        """Get base URL (allows runtime updates)."""
        return Config.TTS_URL
    
    @property
    def api_key(self) -> str:
        """Get API key (allows runtime updates)."""
        return Config.TTS_API_KEY
    
    @property
    def voice(self) -> str:
        """Get voice setting (allows runtime updates)."""
        return Config.TTS_VOICE
    
    async def synthesize(self, text: str, call_id: Optional[str] = None,
                         voice: Optional[str] = None) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Synthesize text to speech using openai-edge-tts.
        
        Args:
            text: The text to synthesize
            call_id: Optional call ID for logging
            voice: Optional voice override
        
        Returns:
            Tuple of (audio_bytes, error_message)
        """
        if not text:
            return None, "Empty input text"
        
        if not self.api_key:
            error = "TTS API key not configured"
            db.add_log('error', 'tts_failed', error, call_id)
            return None, error
        
        try:
            # openai-edge-tts uses OpenAI-compatible endpoint
            url = f"{self.base_url}/v1/audio/speech"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            data = {
                'model': 'tts-1',
                'input': text,
                'voice': voice or self.voice,
                'response_format': 'mp3',
            }
            
            db.add_log('info', 'tts_request', f'Synthesizing: {text[:100]}...', call_id)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    audio_data = response.content
                    db.add_log('info', 'tts_success', f'Generated {len(audio_data)} bytes of audio', call_id)
                    return audio_data, None
                else:
                    error = f"TTS API error: {response.status_code} - {response.text}"
                    db.add_log('error', 'tts_failed', error, call_id)
                    return None, error
        
        except httpx.TimeoutException:
            error = "TTS API request timed out"
            db.add_log('error', 'tts_failed', error, call_id)
            return None, error
        except httpx.ConnectError:
            error = f"Cannot connect to TTS API at {self.base_url}"
            db.add_log('error', 'tts_failed', error, call_id)
            return None, error
        except Exception as e:
            error = f"TTS error: {str(e)}"
            db.add_log('error', 'tts_failed', error, call_id)
            return None, error
    
    def synthesize_sync(self, text: str, call_id: Optional[str] = None,
                        voice: Optional[str] = None) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Synchronous version of synthesize.
        
        Args:
            text: The text to synthesize
            call_id: Optional call ID for logging
            voice: Optional voice override
        
        Returns:
            Tuple of (audio_bytes, error_message)
        """
        if not text:
            return None, "Empty input text"
        
        if not self.api_key:
            error = "TTS API key not configured"
            db.add_log('error', 'tts_failed', error, call_id)
            return None, error
        
        try:
            url = f"{self.base_url}/v1/audio/speech"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            data = {
                'model': 'tts-1',
                'input': text,
                'voice': voice or self.voice,
                'response_format': 'mp3',
            }
            
            db.add_log('info', 'tts_request', f'Synthesizing: {text[:100]}...', call_id)
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    audio_data = response.content
                    db.add_log('info', 'tts_success', f'Generated {len(audio_data)} bytes of audio', call_id)
                    return audio_data, None
                else:
                    error = f"TTS API error: {response.status_code} - {response.text}"
                    db.add_log('error', 'tts_failed', error, call_id)
                    return None, error
        
        except httpx.TimeoutException:
            error = "TTS API request timed out"
            db.add_log('error', 'tts_failed', error, call_id)
            return None, error
        except httpx.ConnectError:
            error = f"Cannot connect to TTS API at {self.base_url}"
            db.add_log('error', 'tts_failed', error, call_id)
            return None, error
        except Exception as e:
            error = f"TTS error: {str(e)}"
            db.add_log('error', 'tts_failed', error, call_id)
            return None, error
    
    def get_available_voices(self) -> list:
        """Get list of available voices from openai-edge-tts."""
        # Common Microsoft Edge TTS voices
        return [
            'en-US-GuyNeural',
            'en-US-JennyNeural',
            'en-US-AriaNeural',
            'en-US-DavisNeural',
            'en-US-AmberNeural',
            'en-US-AnaNeural',
            'en-US-AndrewNeural',
            'en-US-EmmaNeural',
            'en-US-BrianNeural',
            'en-US-ChristopherNeural',
            'en-US-CoraNeural',
            'en-US-ElizabethNeural',
            'en-US-EricNeural',
            'en-US-JacobNeural',
            'en-US-MichelleNeural',
            'en-US-MonicaNeural',
            'en-US-SaraNeural',
            'en-GB-SoniaNeural',
            'en-GB-RyanNeural',
            'en-AU-NatashaNeural',
            'en-AU-WilliamNeural',
        ]
    
    def check_health(self) -> bool:
        """Check if TTS API is accessible."""
        if not self.api_key:
            return False
        try:
            with httpx.Client(timeout=5.0) as client:
                # Try a simple request to check connectivity
                response = client.get(f"{self.base_url}/health")
                return response.status_code in [200, 404]  # 404 is ok, means server is up
        except:
            return False


# Global TTS client instance
tts_client = TTSClient()


