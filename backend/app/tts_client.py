"""TTS client using edge-tts (Microsoft Edge TTS) with gTTS fallback - completely free, no API key required."""
import io
import asyncio
from typing import Optional, Tuple
import edge_tts
import logging
import threading
import sys

from .config import Config
from .database import db
from .websocket import ws_manager

logger = logging.getLogger(__name__)

# Import gTTS for fallback
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
    logger.info("gTTS fallback TTS is available")
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not available - final fallback TTS will not work")


class TTSClient:
    """Client for Microsoft Edge TTS with gTTS fallback."""

    def __init__(self):
        # Edge TTS is completely free and requires no API key
        # Create a dedicated event loop for TTS operations
        self._loop = None
        self._loop_thread = None
        self._lock = threading.Lock()
        self._initialization_failed = False
        try:
            self._start_event_loop()
        except Exception as e:
            logger.error(f"Failed to start TTS event loop on init: {e}", exc_info=True)
            self._initialization_failed = True

    def _start_event_loop(self):
        """Start a dedicated event loop in a background thread."""
        def run_loop(loop):
            try:
                asyncio.set_event_loop(loop)
                logger.info("TTS event loop thread started, running forever...")
                loop.run_forever()
            except Exception as e:
                logger.error(f"TTS event loop crashed: {e}", exc_info=True)

        with self._lock:
            if self._loop is None or self._loop.is_closed():
                try:
                    self._loop = asyncio.new_event_loop()
                    self._loop_thread = threading.Thread(
                        target=run_loop,
                        args=(self._loop,),
                        daemon=True,
                        name="TTS-EventLoop"
                    )
                    self._loop_thread.start()
                    logger.info("Started dedicated TTS event loop in background thread")
                    self._initialization_failed = False
                except Exception as e:
                    logger.error(f"Failed to create TTS event loop: {e}", exc_info=True)
                    self._initialization_failed = True
                    raise

    @property
    def voice(self) -> str:
        """Get voice setting (allows runtime updates)."""
        # Default to a natural-sounding US English voice if not configured
        voice = Config.TTS_VOICE
        if not voice or voice == 'alloy':  # 'alloy' was for OpenAI TTS
            return 'en-US-AriaNeural'  # Natural female voice
        return voice

    def _get_fallback_voices(self, primary_voice: str) -> list:
        """
        Get a list of fallback voices similar to the primary voice.
        Maintains same gender and style characteristics.
        Uses configured TTS_FALLBACK_VOICE if available.
        """
        # Start with primary voice
        voices = [primary_voice]

        # Add configured fallback voice if different from primary
        fallback_voice = getattr(Config, 'TTS_FALLBACK_VOICE', None)
        if fallback_voice and fallback_voice != primary_voice:
            voices.append(fallback_voice)

        # Map primary voices to additional similar fallbacks
        fallback_map = {
            # Male voices - professional/natural alternatives
            'en-US-GuyNeural': ['en-US-AndrewNeural', 'en-US-BrianNeural', 'en-US-DavisNeural', 'en-US-ChristopherNeural'],
            'en-US-AndrewNeural': ['en-US-GuyNeural', 'en-US-BrianNeural', 'en-US-DavisNeural'],
            'en-US-BrianNeural': ['en-US-AndrewNeural', 'en-US-GuyNeural', 'en-US-DavisNeural'],
            # Female voices - natural alternatives
            'en-US-AriaNeural': ['en-US-JennyNeural', 'en-US-EmmaNeural', 'en-US-MichelleNeural'],
            'en-US-JennyNeural': ['en-US-AriaNeural', 'en-US-EmmaNeural', 'en-US-MichelleNeural'],
        }

        # Add mapped fallbacks (avoid duplicates)
        if primary_voice in fallback_map:
            for v in fallback_map[primary_voice]:
                if v not in voices:
                    voices.append(v)

        # Add generic fallbacks based on gender detection (avoid duplicates)
        if 'Male' in primary_voice or 'Guy' in primary_voice or 'Andrew' in primary_voice or 'Brian' in primary_voice:
            for v in ['en-US-AndrewNeural', 'en-US-BrianNeural', 'en-US-GuyNeural']:
                if v not in voices:
                    voices.append(v)
        else:
            for v in ['en-US-JennyNeural', 'en-US-AriaNeural']:
                if v not in voices:
                    voices.append(v)

        return voices

    async def _synthesize_gtts(self, text: str, call_id: Optional[str] = None) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Ultimate fallback using Google TTS (gTTS).
        Returns MP3 audio data.
        """
        if not GTTS_AVAILABLE:
            return None, "gTTS not available"

        try:
            logger.info(f"Using gTTS fallback for: {text[:50]}...")
            db.add_log('info', 'tts_gtts_fallback', f'Using Google TTS fallback: {text[:100]}...', call_id)

            # Create gTTS object
            tts = gTTS(text=text, lang='en', slow=False)

            # Save to BytesIO buffer
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            audio_data = audio_buffer.read()

            if audio_data:
                logger.info(f"gTTS SUCCESS: Generated {len(audio_data)} bytes")
                db.add_log('info', 'tts_success', f'Generated {len(audio_data)} bytes with gTTS fallback', call_id)
                return audio_data, None
            else:
                error = "gTTS returned no audio data"
                logger.error(error)
                return None, error

        except Exception as e:
            error = f"gTTS fallback failed: {str(e)}"
            logger.error(error, exc_info=True)
            db.add_log('error', 'tts_gtts_failed', error, call_id)
            return None, error

    async def synthesize(self, text: str, call_id: Optional[str] = None,
                        voice: Optional[str] = None) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Synthesize text to speech using Microsoft Edge TTS with automatic fallback to gTTS.

        Args:
            text: The text to synthesize
            call_id: Optional call ID for logging
            voice: Optional voice override

        Returns:
            Tuple of (audio_bytes, error_message)
        """
        if not text:
            return None, "Empty input text"

        primary_voice = voice or self.voice
        fallback_voices = self._get_fallback_voices(primary_voice)

        logger.info(f"TTS synthesize with fallback chain: {fallback_voices}")

        # Try each voice in the fallback chain
        last_error = None
        for voice_idx, voice_to_use in enumerate(fallback_voices):
            # Try each voice up to 2 times before moving to next fallback
            max_attempts = 2 if voice_idx < len(fallback_voices) - 1 else 3

            for attempt in range(max_attempts):
                try:
                    is_fallback = voice_to_use != primary_voice
                    fallback_note = " (FALLBACK)" if is_fallback else ""

                    db.add_log('info', 'tts_request',
                              f'Synthesizing with {voice_to_use}{fallback_note} (attempt {attempt + 1}/{max_attempts}): {text[:100]}...',
                              call_id)
                    logger.info(f"TTS attempt {attempt + 1}/{max_attempts} with voice {voice_to_use}{fallback_note}: {text[:50]}...")

                    # Create communicate object
                    communicate = edge_tts.Communicate(text, voice_to_use)

                    # Collect audio data with WAV header handling
                    audio_data = b''
                    chunk_count = 0
                    empty_chunks = 0
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            chunk_data = chunk["data"]
                            chunk_count += 1
                            
                            # Skip empty chunks
                            if not chunk_data or len(chunk_data) == 0:
                                empty_chunks += 1
                                logger.debug(f"Empty chunk {chunk_count} received from {voice_to_use}")
                                continue
                            
                            # Check for and strip WAV headers (44 bytes starting with "RIFF")
                            if chunk_data.startswith(b"RIFF") and len(chunk_data) > 44:
                                # This chunk has a WAV header, strip it
                                audio_data += chunk_data[44:]
                                logger.debug(f"Stripped WAV header from chunk {chunk_count} (was {len(chunk_data)} bytes, now {len(chunk_data) - 44} bytes)")
                            else:
                                # No WAV header or too small, use as-is
                                audio_data += chunk_data

                    # Validate audio data
                    if audio_data and len(audio_data) > 44:  # Must be more than just a WAV header
                        success_msg = f'Generated {len(audio_data)} bytes of audio with voice {voice_to_use}{fallback_note}'
                        if empty_chunks > 0:
                            logger.warning(f"Skipped {empty_chunks} empty chunks from {voice_to_use}")
                        db.add_log('info', 'tts_success', success_msg, call_id)
                        logger.info(f"TTS SUCCESS: {success_msg}")
                        if is_fallback:
                            logger.warning(f"Using fallback voice {voice_to_use} instead of {primary_voice}")
                        return audio_data, None
                    elif audio_data and len(audio_data) <= 44:
                        # Only WAV header or very small data
                        logger.warning(f"Audio data from {voice_to_use} is too small ({len(audio_data)} bytes), likely only header")
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(0.5)
                            continue
                    else:
                        logger.warning(f"No audio data generated with {voice_to_use} on attempt {attempt + 1} (processed {chunk_count} chunks, {empty_chunks} empty)")
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(0.5)  # Brief wait before retry
                            continue

                except Exception as e:
                    error_msg = str(e)
                    last_error = error_msg
                    
                    # Detect specific error types
                    is_rate_limit = '403' in error_msg or 'rate limit' in error_msg.lower() or 'too many requests' in error_msg.lower()
                    is_unauthorized = '401' in error_msg or 'unauthorized' in error_msg.lower()
                    is_network_error = 'connection' in error_msg.lower() or 'network' in error_msg.lower() or 'timeout' in error_msg.lower()
                    
                    error_type = "unknown"
                    if is_rate_limit:
                        error_type = "rate_limit"
                    elif is_unauthorized:
                        error_type = "unauthorized"
                    elif is_network_error:
                        error_type = "network"
                    
                    logger.error(f"TTS attempt {attempt + 1}/{max_attempts} with {voice_to_use} failed ({error_type}): {error_msg}", exc_info=True)
                    db.add_log('error', 'tts_attempt_failed', 
                              f'Attempt {attempt + 1}/{max_attempts} with {voice_to_use} failed ({error_type}): {error_msg[:100]}', 
                              call_id)

                    # If not the last attempt for this voice, retry with appropriate delay
                    if attempt < max_attempts - 1:
                        # Use longer delay for rate limit errors (3-5 seconds)
                        if is_rate_limit:
                            delay = 3.0 + (attempt * 0.5)  # 3s, 3.5s, 4s...
                            logger.info(f"Rate limit detected, waiting {delay:.1f}s before retry...")
                            await asyncio.sleep(delay)
                        else:
                            # Shorter delay for other errors
                            await asyncio.sleep(0.5)
                        continue

            # If we get here, all attempts with this voice failed, try next fallback
            logger.warning(f"All attempts with voice {voice_to_use} failed, trying next fallback...")

        # All edge-tts voices failed, try gTTS as ultimate fallback
        logger.warning("All edge-tts voices failed, attempting gTTS fallback...")
        db.add_log('warning', 'tts_edge_failed', 
                   f'All edge-tts voices failed. Last error: {last_error}. Attempting gTTS fallback...', 
                   call_id)
        
        # Check if gTTS is available before attempting
        if not GTTS_AVAILABLE:
            error = f"TTS error: All edge-tts voices failed and gTTS is not available. Last edge-tts error: {last_error}"
            db.add_log('error', 'tts_failed', error, call_id)
            logger.error(error)
            return None, error
        
        # Attempt gTTS fallback
        gtts_result = await self._synthesize_gtts(text, call_id)
        if gtts_result[0] is not None and len(gtts_result[0]) > 0:
            logger.info(f"gTTS fallback SUCCESS: Generated {len(gtts_result[0])} bytes of audio")
            db.add_log('info', 'tts_gtts_success', 
                       f'gTTS fallback succeeded: Generated {len(gtts_result[0])} bytes', 
                       call_id)
            return gtts_result

        # Everything failed
        error = f"TTS error: All fallback voices and gTTS failed. Last edge-tts error: {last_error}, gTTS error: {gtts_result[1] if gtts_result else 'gTTS not available'}"
        db.add_log('error', 'tts_failed', error, call_id)
        logger.error(error)
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
            logger.info(f"TTS synthesize_sync called for: {text[:50]}...")

            # Ensure event loop is running
            if self._loop is None or self._loop.is_closed() or self._initialization_failed:
                logger.warning("Event loop was closed or failed, restarting...")
                self._start_event_loop()
                # Give it a moment to start
                import time
                time.sleep(0.1)

            if self._loop is None:
                error = "Failed to start TTS event loop"
                logger.error(error)
                db.add_log('error', 'tts_failed', error, call_id)
                return None, error

            # Schedule the coroutine on the dedicated event loop
            logger.debug("Scheduling TTS coroutine on event loop...")
            future = asyncio.run_coroutine_threadsafe(
                self.synthesize(text, call_id, voice),
                self._loop
            )

            # Wait for result with timeout (30 seconds)
            logger.debug("Waiting for TTS result...")
            result = future.result(timeout=30)
            logger.info(f"TTS synthesize_sync completed: {result[0] is not None}")
            return result

        except Exception as e:
            error = f"TTS sync error: {str(e)}"
            db.add_log('error', 'tts_failed', error, call_id)
            logger.error(error, exc_info=True)
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
        """Check if TTS is available (either edge-tts or gTTS)."""
        try:
            # Check edge-tts
            import edge_tts
            edge_tts_healthy = self._loop is not None and not self._loop.is_closed() and not self._initialization_failed

            # Consider healthy if either edge-tts OR gTTS is available
            is_healthy = edge_tts_healthy or GTTS_AVAILABLE

            if not is_healthy:
                logger.warning(f"TTS health check failed: edge-tts_healthy={edge_tts_healthy}, gtts_available={GTTS_AVAILABLE}")
            return is_healthy
        except ImportError:
            # If edge-tts not available, check if gTTS is
            logger.warning("edge-tts module not available!")
            return GTTS_AVAILABLE


# Global TTS client instance
logger.info("Initializing global TTS client...")
tts_client = TTSClient()
logger.info(f"TTS client initialized: healthy={tts_client.check_health()}, gTTS_available={GTTS_AVAILABLE}")
