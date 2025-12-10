"""TTS client using edge-tts (Microsoft Edge TTS) - completely free, no API key required."""
import io
import asyncio
from typing import Optional, Tuple
import edge_tts

from .config import Config
from .database import db
from .websocket import ws_manager


class TTSClient:
    """Client for Microsoft Edge TTS using edge-tts library."""

    def __init__(self):
        # Edge TTS is completely free and requires no API key
        pass

    @property
    def voice(self) -> str:
        """Get voice setting (allows runtime updates)."""
        # Default to a natural-sounding US English voice if not configured
        voice = Config.TTS_VOICE
        if not voice or voice == 'alloy':  # 'alloy' was for OpenAI TTS
            return 'en-US-AriaNeural'  # Natural female voice
        return voice

    async def synthesize(self, text: str, call_id: Optional[str] = None,
                        voice: Optional[str] = None) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Synthesize text to speech using Microsoft Edge TTS.

        Args:
            text: The text to synthesize
            call_id: Optional call ID for logging
            voice: Optional voice override

        Returns:
            Tuple of (audio_bytes, error_message)
        """
        if not text:
            return None, "Empty input text"

        try:
            voice_to_use = voice or self.voice

            db.add_log('info', 'tts_request', f'Synthesizing with {voice_to_use}: {text[:100]}...', call_id)

            # Create communicate object
            communicate = edge_tts.Communicate(text, voice_to_use)

            # Collect audio data
            audio_data = b''
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if audio_data:
                db.add_log('info', 'tts_success', f'Generated {len(audio_data)} bytes of audio', call_id)
                return audio_data, None
            else:
                error = "No audio data generated"
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

        try:
            # Run the async function in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.synthesize(text, call_id, voice))
                return result
            finally:
                loop.close()
        except Exception as e:
            error = f"TTS sync error: {str(e)}"
            db.add_log('error', 'tts_failed', error, call_id)
            return None, error

    def get_available_voices(self) -> list:
        """Get list of available Microsoft Edge TTS voices."""
        # Common high-quality Microsoft Edge TTS voices
        return [
            # US English voices (Neural)
            'en-US-AriaNeural',        # Female, natural
            'en-US-GuyNeural',          # Male, natural
            'en-US-JennyNeural',        # Female, conversational
            'en-US-DavisNeural',        # Male, friendly
            'en-US-AmberNeural',        # Female, warm
            'en-US-AnaNeural',          # Female (child)
            'en-US-AndrewNeural',       # Male, professional
            'en-US-EmmaNeural',         # Female, professional
            'en-US-BrianNeural',        # Male, clear
            'en-US-ChristopherNeural',  # Male, mature
            'en-US-ElizabethNeural',    # Female, mature
            'en-US-EricNeural',         # Male, energetic
            'en-US-JacobNeural',        # Male, young
            'en-US-MichelleNeural',     # Female, clear
            'en-US-MonicaNeural',       # Female, friendly
            'en-US-SaraNeural',         # Female, soft
            # UK English voices
            'en-GB-SoniaNeural',        # Female, British
            'en-GB-RyanNeural',         # Male, British
            'en-GB-LibbyNeural',        # Female, British
            'en-GB-MiaNeural',          # Female, British
            # Australian English voices
            'en-AU-NatashaNeural',      # Female, Australian
            'en-AU-WilliamNeural',      # Male, Australian
            # Canadian English voices
            'en-CA-ClaraNeural',        # Female, Canadian
            'en-CA-LiamNeural',         # Male, Canadian
        ]

    def check_health(self) -> bool:
        """Check if edge-tts is available (always true since it's a local library)."""
        try:
            # edge-tts is a local library, so it's always available if imported
            import edge_tts
            return True
        except ImportError:
            return False


# Global TTS client instance
tts_client = TTSClient()
