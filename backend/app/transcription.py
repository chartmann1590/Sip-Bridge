"""Groq API integration for speech-to-text transcription."""
import io
import httpx
from typing import Optional, Tuple
from pathlib import Path

from .config import Config
from .database import db
from .websocket import ws_manager


class GroqTranscriber:
    """Handles audio transcription using Groq's Whisper API."""
    
    def __init__(self):
        self.api_url = Config.GROQ_API_URL
        self.model = Config.GROQ_MODEL
    
    @property
    def api_key(self) -> str:
        """Get API key (allows runtime updates)."""
        return Config.GROQ_API_KEY
    
    async def transcribe(self, audio_data: bytes, call_id: Optional[str] = None,
                         format: str = 'wav') -> Tuple[Optional[str], Optional[str]]:
        """
        Transcribe audio data to text using Groq API.
        
        Args:
            audio_data: Raw audio bytes
            call_id: Optional call ID for logging
            format: Audio format (wav, mp3, etc.)
        
        Returns:
            Tuple of (transcribed_text, error_message)
        """
        if not self.api_key:
            error = "Groq API key not configured"
            db.add_log('error', 'transcription_failed', error, call_id)
            return None, error
        
        try:
            # Prepare the audio file for upload
            files = {
                'file': (f'audio.{format}', io.BytesIO(audio_data), f'audio/{format}'),
            }
            data = {
                'model': self.model,
                'response_format': 'text',
                'language': 'en',
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    data=data
                )
                
                if response.status_code == 200:
                    text = response.text.strip()
                    db.add_log('info', 'transcription_success', f'Transcribed: {text[:100]}...', call_id)
                    
                    # Broadcast transcription result
                    if call_id:
                        ws_manager.broadcast_transcription(call_id, text, is_final=True)
                    
                    return text, None
                else:
                    error = f"Groq API error: {response.status_code} - {response.text}"
                    db.add_log('error', 'transcription_failed', error, call_id)
                    return None, error
        
        except httpx.TimeoutException:
            error = "Groq API request timed out"
            db.add_log('error', 'transcription_failed', error, call_id)
            return None, error
        except Exception as e:
            error = f"Transcription error: {str(e)}"
            db.add_log('error', 'transcription_failed', error, call_id)
            return None, error
    
    def transcribe_sync(self, audio_data: bytes, call_id: Optional[str] = None,
                        format: str = 'wav') -> Tuple[Optional[str], Optional[str]]:
        """
        Synchronous version of transcribe for use in non-async contexts.
        
        Args:
            audio_data: Raw audio bytes
            call_id: Optional call ID for logging
            format: Audio format (wav, mp3, etc.)
        
        Returns:
            Tuple of (transcribed_text, error_message)
        """
        if not self.api_key:
            error = "Groq API key not configured"
            db.add_log('error', 'transcription_failed', error, call_id)
            return None, error
        
        try:
            files = {
                'file': (f'audio.{format}', io.BytesIO(audio_data), f'audio/{format}'),
            }
            data = {
                'model': self.model,
                'response_format': 'text',
                'language': 'en',
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
            }

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    data=data
                )
                
                if response.status_code == 200:
                    text = response.text.strip()
                    db.add_log('info', 'transcription_success', f'Transcribed: {text[:100]}...', call_id)
                    
                    if call_id:
                        ws_manager.broadcast_transcription(call_id, text, is_final=True)
                    
                    return text, None
                else:
                    error = f"Groq API error: {response.status_code} - {response.text}"
                    db.add_log('error', 'transcription_failed', error, call_id)
                    return None, error
        
        except httpx.TimeoutException:
            error = "Groq API request timed out"
            db.add_log('error', 'transcription_failed', error, call_id)
            return None, error
        except Exception as e:
            error = f"Transcription error: {str(e)}"
            db.add_log('error', 'transcription_failed', error, call_id)
            return None, error
    
    def check_health(self) -> bool:
        """Check if Groq API is accessible."""
        return bool(self.api_key)


# Global transcriber instance
transcriber = GroqTranscriber()







