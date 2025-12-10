"""TTS client using edge-tts (Microsoft Edge TTS) - completely free, no API key required."""
import io
import asyncio
from typing import Optional, Tuple
import edge_tts
import logging
import threading

from .config import Config
from .database import db
from .websocket import ws_manager

logger = logging.getLogger(__name__)


class TTSClient:
    """Client for Microsoft Edge TTS using edge-tts library."""

    def __init__(self):
        # Edge TTS is completely free and requires no API key
        # Create a dedicated event loop for TTS operations
        self._loop = None
        self._loop_thread = None
        self._lock = threading.Lock()
        self._start_event_loop()

    def _start_event_loop(self):
        """Start a dedicated event loop in a background thread."""
        def run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        with self._lock:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                self._loop_thread = threading.Thread(target=run_loop, args=(self._loop,), daemon=True)
                self._loop_thread.start()
                logger.info("Started dedicated TTS event loop")

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

        voice_to_use = voice or self.voice

        # Try up to 3 times with different strategies
        for attempt in range(3):
            try:
                db.add_log('info', 'tts_request', f'Synthesizing with {voice_to_use} (attempt {attempt + 1}): {text[:100]}...', call_id)

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
                    logger.warning(f"No audio data generated on attempt {attempt + 1}")
                    if attempt < 2:
                        await asyncio.sleep(1)  # Wait before retry
                        continue

                    error = "No audio data generated after retries"
                    db.add_log('error', 'tts_failed', error, call_id)
                    return None, error

            except Exception as e:
                error_msg = str(e)
                logger.error(f"TTS attempt {attempt + 1} failed: {error_msg}")

                # If this is a 403 or connection error and we have more attempts, try again
                if attempt < 2 and ('403' in error_msg or 'Invalid response status' in error_msg):
                    logger.info(f"Retrying TTS after error (attempt {attempt + 1}/3)")
                    await asyncio.sleep(2)  # Wait longer before retry
                    continue

                # On final attempt, return the error
                if attempt == 2:
                    error = f"TTS error after 3 attempts: {error_msg}"
                    db.add_log('error', 'tts_failed', error, call_id)
                    return None, error

        # Should not reach here, but just in case
        error = "TTS failed: exceeded retry attempts"
        db.add_log('error', 'tts_failed', error, call_id)
        return None, error

    def synthesize_sync(self, text: str, call_id: Optional[str] = None,
                        voice: Optional[str] = None) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Synchronous version of synthesize - OPTIMIZED to reuse event loop.

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
            # Ensure event loop is running
            if self._loop is None or self._loop.is_closed():
                logger.warning("Event loop was closed, restarting...")
                self._start_event_loop()

            # Schedule the coroutine on the dedicated event loop
            future = asyncio.run_coroutine_threadsafe(
                self.synthesize(text, call_id, voice),
                self._loop
            )

            # Wait for result with timeout (30 seconds)
            result = future.result(timeout=30)
            return result

        except Exception as e:
            error = f"TTS sync error: {str(e)}"
            db.add_log('error', 'tts_failed', error, call_id)
            logger.error(error)
            return None, error

    def get_available_voices(self) -> list:
        """Get list of available Microsoft Edge TTS voices dynamically from edge-tts."""
        try:
            # Fetch all available voices from edge-tts
            async def _fetch_voices():
                voices_list = []
                voices = await edge_tts.list_voices()
                for voice in voices:
                    # Extract the 'ShortName' field from each voice object (this is what edge_tts.Communicate expects)
                    if 'ShortName' in voice:
                        voices_list.append(voice['ShortName'])
                return voices_list

            # Use the dedicated event loop
            if self._loop is None or self._loop.is_closed():
                self._start_event_loop()

            future = asyncio.run_coroutine_threadsafe(_fetch_voices(), self._loop)
            voices_list = future.result(timeout=10)

            # Sort alphabetically for better UX
            voices_list.sort()
            logger.info(f"Successfully fetched {len(voices_list)} voices from edge-tts")
            return voices_list

        except Exception as e:
            logger.error(f"Failed to fetch voices dynamically from edge-tts: {e}")
            # Fallback to a curated list of common voices if dynamic fetch fails
            logger.warning("Using fallback voice list")
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
            # Also check if our event loop is running
            return self._loop is not None and not self._loop.is_closed()
        except ImportError:
            return False


# Global TTS client instance
tts_client = TTSClient()
