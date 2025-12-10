"""
SIP client for handling VoIP calls - Pure socket-based implementation.
Based on proven SIP-Mumble bridge implementation (NO registration needed).
The PBX should be configured to route calls to this bridge's IP:5060.
"""
import io
import os
import time
import wave
import socket
import struct
import threading
import random
import re
import uuid
import hashlib
from typing import Optional, Callable
from dataclasses import dataclass
from collections import deque

from .config import Config
from .database import db
from .websocket import ws_manager
from .transcription import transcriber
from .gpt_client import gpt_client
from .tts_client import tts_client
from .calendar_client import calendar_client
from .email_client import email_client
from .weather_client import weather_client
from .tomtom_client import tomtom_client

from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytz

import logging
logger = logging.getLogger(__name__)

# Try to import audioop (built into Python 3.11)
try:
    import audioop
except ImportError:
    audioop = None
    logger.warning("audioop not available - audio processing will be limited")


@dataclass
class CallState:
    """State for an active call."""
    call_id: str
    caller_id: str
    conversation_id: Optional[int] = None
    from_tag: Optional[str] = None
    to_tag: Optional[str] = None


class SIPCall:
    """Represents a single SIP call with RTP audio."""
    
    def __init__(self, invite_msg: str, caller_addr: tuple, sip_socket: socket.socket):
        self.invite_msg = invite_msg
        self.caller_addr = caller_addr
        self.sip_socket = sip_socket
        self.rtp_socket: Optional[socket.socket] = None
        self.rtp_port: Optional[int] = None
        self.remote_rtp_ip: Optional[str] = None
        self.remote_rtp_port: Optional[int] = None
        self.running = False
        self.call_id: Optional[str] = None
        self.from_tag: Optional[str] = None
        self.to_tag: Optional[str] = None
        self.session_started = False
        
        # RTP sequence and timestamp tracking
        self._rtp_sequence = random.randint(0, 65535)
        self._rtp_timestamp = random.randint(0, 0xFFFFFFFF)
        self._rtp_ssrc = random.randint(0, 0xFFFFFFFF)
    
    def parse_sdp(self) -> bool:
        """Parse SDP from INVITE message to get remote RTP info."""
        try:
            lines = self.invite_msg.split('\r\n')
            
            # Find connection address (c=)
            for line in lines:
                if line.startswith('c='):
                    # c=IN IP4 10.0.0.66
                    parts = line.split()
                    if len(parts) >= 3:
                        self.remote_rtp_ip = parts[2]
            
            # Find media port (m=audio) and codecs
            for line in lines:
                if line.startswith('m=audio'):
                    # m=audio 16970 RTP/AVP 0 8 101
                    parts = line.split()
                    if len(parts) >= 2:
                        self.remote_rtp_port = int(parts[1])
                        # Extract payload types (codecs)
                        if len(parts) >= 4:
                            codecs = ' '.join(parts[3:])
                            logger.info(f"Client offered codecs (payload types): {codecs}")
            
            logger.info(f"Parsed SDP: Remote RTP at {self.remote_rtp_ip}:{self.remote_rtp_port}")
            return bool(self.remote_rtp_ip and self.remote_rtp_port)
        
        except Exception as e:
            logger.error(f"Error parsing SDP: {e}")
            return False
    
    def create_rtp_socket(self) -> bool:
        """Create RTP socket for audio within configured port range."""
        try:
            self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try to bind to a port in the configured range
            rtp_min = int(os.getenv('RTP_PORT_MIN', 10000))
            rtp_max = int(os.getenv('RTP_PORT_MAX', 10100))
            
            for port in range(rtp_min, rtp_max + 1):
                try:
                    self.rtp_socket.bind(('0.0.0.0', port))
                    self.rtp_port = port
                    logger.info(f"Created RTP socket on port {self.rtp_port}")
                    return True
                except OSError:
                    continue
            
            # If all ports in range are busy, use any available port
            self.rtp_socket.bind(('0.0.0.0', 0))
            self.rtp_port = self.rtp_socket.getsockname()[1]
            logger.warning(f"RTP port range exhausted, using port {self.rtp_port}")
            return True
        
        except Exception as e:
            logger.error(f"Error creating RTP socket: {e}")
            return False
    
    def send_rtp(self, audio_data: bytes, payload_type: int = 0) -> None:
        """Send RTP packet with audio data."""
        try:
            if not self.rtp_socket or not self.remote_rtp_ip:
                return
            
            # Build RTP header (12 bytes)
            version = 2
            padding = 0
            extension = 0
            cc = 0
            marker = 0
            
            header = struct.pack('!BBHII',
                (version << 6) | (padding << 5) | (extension << 4) | cc,
                (marker << 7) | payload_type,
                self._rtp_sequence & 0xFFFF,
                self._rtp_timestamp & 0xFFFFFFFF,
                self._rtp_ssrc
            )
            
            # Increment sequence and timestamp
            self._rtp_sequence = (self._rtp_sequence + 1) & 0xFFFF
            self._rtp_timestamp = (self._rtp_timestamp + 160) & 0xFFFFFFFF  # 20ms @ 8kHz
            
            packet = header + audio_data
            self.rtp_socket.sendto(packet, (self.remote_rtp_ip, self.remote_rtp_port))
        
        except Exception as e:
            logger.error(f"Error sending RTP: {e}")
    
    def close(self) -> None:
        """Close RTP socket."""
        self.running = False
        if self.rtp_socket:
            try:
                self.rtp_socket.close()
            except:
                pass
            self.rtp_socket = None


class SimpleSIPServer:
    """
    SIP server with proper SDP/RTP support.
    NO registration needed - PBX should route calls directly to this server.
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5060):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.call_handler: Optional[Callable] = None
        self.active_calls: dict = {}
        self._listen_thread: Optional[threading.Thread] = None
    
    def start(self) -> bool:
        """Start the SIP server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.running = True
            
            logger.info(f"SIP Server listening on {self.host}:{self.port}")
            
            # Start listening thread
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to start SIP server: {e}")
            return False
    
    @property
    def is_registered(self) -> bool:
        """For compatibility - always True since we don't need registration."""
        return self.running
    
    def _listen_loop(self) -> None:
        """Listen for incoming SIP messages."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(8192)
                message = data.decode('utf-8', errors='ignore')
                
                logger.debug(f"Received SIP message from {addr}:\n{message[:300]}")
                
                # Handle SIP message
                self._handle_sip_message(message, addr)
            
            except Exception as e:
                if self.running:
                    logger.error(f"Error in listen loop: {e}")
    
    def _handle_sip_message(self, message: str, addr: tuple) -> None:
        """Handle incoming SIP message."""
        lines = message.split('\r\n')
        if not lines:
            return
        
        request_line = lines[0]
        
        if request_line.startswith('INVITE'):
            logger.info(f"Incoming INVITE from {addr}")
            self._handle_invite(message, addr)
        
        elif request_line.startswith('ACK'):
            logger.info(f"ACK received from {addr}")
            # Call is now established, trigger handler
            call_id = self._extract_header(message, 'Call-ID')
            if call_id and call_id in self.active_calls:
                call = self.active_calls[call_id]
                # Only start handler once per call
                if not call.session_started:
                    call.session_started = True
                    if self.call_handler:
                        threading.Thread(target=self.call_handler, args=(call,), daemon=True).start()
                else:
                    logger.debug(f"ACK for already-started call {call_id}, ignoring")
        
        elif request_line.startswith('BYE'):
            logger.info(f"BYE received - Call ended by {addr}")
            self._send_response(200, 'OK', addr, message)

            # Clean up call and notify session
            call_id = self._extract_header(message, 'Call-ID')
            if call_id and call_id in self.active_calls:
                call = self.active_calls[call_id]
                call.close()
                del self.active_calls[call_id]

                # Mark call as ended in database
                logger.info(f"Ending conversation for call {call_id}")
                db.add_message_by_call_id(call_id, 'system', 'User hung up')
                db.end_conversation(call_id)
        
        elif request_line.startswith('OPTIONS'):
            self._send_response(200, 'OK', addr, message)
        
        elif request_line.startswith('CANCEL'):
            logger.info(f"Call cancelled by {addr}")
            self._send_response(200, 'OK', addr, message)
    
    def _handle_invite(self, message: str, addr: tuple) -> None:
        """Handle INVITE - send 180 Ringing then 200 OK with SDP."""
        try:
            # Check if this is a retransmitted INVITE for an existing call
            call_id = self._extract_header(message, 'Call-ID')
            if call_id and call_id in self.active_calls:
                logger.debug(f"Retransmitted INVITE for existing call {call_id}, re-sending 200 OK")
                call = self.active_calls[call_id]
                # Re-send responses
                self._send_response(100, 'Trying', addr, message)
                time.sleep(0.1)
                self._send_response(180, 'Ringing', addr, message, to_tag=call.to_tag)
                time.sleep(0.2)
                self._send_invite_ok(addr, message, call)
                return
            
            # Create call object
            call = SIPCall(message, addr, self.socket)
            
            # Parse SDP to get remote RTP info
            if not call.parse_sdp():
                logger.error("Failed to parse SDP from INVITE")
                self._send_response(400, 'Bad Request', addr, message)
                return
            
            # Create RTP socket
            if not call.create_rtp_socket():
                logger.error("Failed to create RTP socket")
                self._send_response(500, 'Internal Server Error', addr, message)
                return
            
            # Extract call info
            call.call_id = call_id
            from_header = self._extract_header(message, 'From')

            # Extract caller ID from From header
            caller_id = 'Unknown'
            if from_header:
                # Try to extract display name or SIP URI
                if '<' in from_header:
                    # Format: "Display Name" <sip:user@host>
                    display_name = from_header.split('<')[0].strip().strip('"')
                    if display_name:
                        caller_id = display_name
                    else:
                        # Extract user from SIP URI
                        sip_uri = from_header.split('<')[1].split('>')[0]
                        if '@' in sip_uri:
                            caller_id = sip_uri.split(':')[1].split('@')[0]
                else:
                    # Format: sip:user@host
                    if '@' in from_header:
                        caller_id = from_header.split(':')[1].split('@')[0]

            # Extract from-tag
            if from_header and 'tag=' in from_header:
                call.from_tag = from_header.split('tag=')[1].split(';')[0].split('>')[0]

            # Generate to-tag
            call.to_tag = f"tag-{random.randint(100000, 999999)}"

            # Store call
            if call.call_id:
                self.active_calls[call.call_id] = call

            # Send 100 Trying
            self._send_response(100, 'Trying', addr, message)

            # Broadcast 'ringing' status
            ws_manager.broadcast_call_status('ringing', call_id, caller_id)
            logger.info(f"Incoming call from {caller_id} (Call-ID: {call_id})")

            # Send 180 Ringing
            time.sleep(0.1)
            self._send_response(180, 'Ringing', addr, message, to_tag=call.to_tag)
            
            # Send 200 OK with SDP
            time.sleep(0.2)
            self._send_invite_ok(addr, message, call)
        
        except Exception as e:
            logger.error(f"Error handling INVITE: {e}", exc_info=True)
            self._send_response(500, 'Internal Server Error', addr, message)
    
    def _send_invite_ok(self, addr: tuple, request: str, call: SIPCall) -> None:
        """Send 200 OK response with SDP."""
        try:
            # Use the IP that the PBX sent the INVITE to (from the request line)
            # This ensures we advertise the externally accessible IP
            request_lines = request.split('\r\n')
            request_line = request_lines[0]
            
            # Extract IP from "INVITE sip:10.0.0.56:5060 SIP/2.0"
            local_ip = self._get_local_ip()
            if 'sip:' in request_line:
                try:
                    uri_part = request_line.split('sip:')[1].split()[0]
                    if ':' in uri_part:
                        local_ip = uri_part.split(':')[0]
                    else:
                        local_ip = uri_part
                except:
                    pass
            
            # Build SDP
            sdp = f"""v=0
o=SIPBridge 0 0 IN IP4 {local_ip}
s=Call
c=IN IP4 {local_ip}
t=0 0
m=audio {call.rtp_port} RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=ptime:20
a=sendrecv
"""
            
            # Extract headers from request
            call_id = self._extract_header(request, 'Call-ID')
            from_header = self._extract_header(request, 'From')
            to_header = self._extract_header(request, 'To')
            cseq = self._extract_header(request, 'CSeq')
            via = self._extract_header(request, 'Via')
            
            # Add to-tag if not present
            if to_header and 'tag=' not in to_header:
                to_header = f"{to_header};{call.to_tag}"
            
            # Build response
            response = f"SIP/2.0 200 OK\r\n"
            if via:
                response += f"Via: {via}\r\n"
            if from_header:
                response += f"From: {from_header}\r\n"
            if to_header:
                response += f"To: {to_header}\r\n"
            else:
                response += f"To: <sip:{Config.SIP_EXTENSION}@{local_ip}>;{call.to_tag}\r\n"
            if call_id:
                response += f"Call-ID: {call_id}\r\n"
            if cseq:
                response += f"CSeq: {cseq}\r\n"
            
            response += f"Contact: <sip:{Config.SIP_USERNAME}@{local_ip}:{self.port}>\r\n"
            response += f"Content-Type: application/sdp\r\n"
            response += f"Content-Length: {len(sdp)}\r\n"
            response += "\r\n"
            response += sdp
            
            self.socket.sendto(response.encode('utf-8'), addr)
            logger.info(f"Sent 200 OK with SDP to {addr}")
            logger.debug(f"SDP:\n{sdp}")
        
        except Exception as e:
            logger.error(f"Error sending 200 OK: {e}", exc_info=True)
    
    def _send_response(self, code: int, reason: str, addr: tuple, request: str, 
                       to_tag: Optional[str] = None) -> None:
        """Send SIP response."""
        try:
            # Extract headers from request
            call_id = self._extract_header(request, 'Call-ID')
            from_header = self._extract_header(request, 'From')
            to_header = self._extract_header(request, 'To')
            cseq = self._extract_header(request, 'CSeq')
            via = self._extract_header(request, 'Via')
            
            # Add to-tag if provided and not already present
            if to_tag and to_header and 'tag=' not in to_header:
                to_header = f"{to_header};{to_tag}"
            
            response = f"SIP/2.0 {code} {reason}\r\n"
            if via:
                response += f"Via: {via}\r\n"
            if from_header:
                response += f"From: {from_header}\r\n"
            if to_header:
                response += f"To: {to_header}\r\n"
            if call_id:
                response += f"Call-ID: {call_id}\r\n"
            if cseq:
                response += f"CSeq: {cseq}\r\n"
            response += f"Content-Length: 0\r\n"
            response += "\r\n"
            
            self.socket.sendto(response.encode('utf-8'), addr)
            logger.debug(f"Sent {code} {reason} to {addr}")
        
        except Exception as e:
            logger.error(f"Error sending response: {e}")
    
    def _extract_header(self, message: str, header_name: str) -> Optional[str]:
        """Extract header value from SIP message."""
        for line in message.split('\r\n'):
            if line.startswith(f"{header_name}:"):
                return line.split(':', 1)[1].strip()
        return None
    
    def _get_local_ip(self) -> str:
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((Config.SIP_HOST, Config.SIP_PORT))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return '127.0.0.1'
    
    def set_call_handler(self, handler: Callable) -> None:
        """Set callback for incoming calls."""
        self.call_handler = handler
    
    def stop(self) -> None:
        """Stop the SIP server."""
        self.running = False
        
        # Close all active calls
        for call in list(self.active_calls.values()):
            call.close()
        self.active_calls.clear()
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        logger.info("SIP server stopped")


class CallSession:
    """Manages a single call session with RTP audio and AI pipeline."""
    
    def __init__(self, sip_call: SIPCall):
        self.sip_call = sip_call
        self.active = False
        self.rtp_thread: Optional[threading.Thread] = None
        
        # Voice activity detection on 8kHz PCM
        # Voice activity detection on 8kHz PCM
        self.voice_threshold = 150  # Initial threshold (higher to avoid noise)
        self.adaptive_threshold = True
        self.silence_threshold = 1.5  # seconds
        self.recording = False
        self.last_audio_time: Optional[float] = None
        self.audio_buffer_8k: list = []  # list of 16-bit PCM @8kHz
        self.pre_speech_buffer = deque(maxlen=20) # 20 frames * 20ms = 400ms buffer
        self.consecutive_speech_frames = 0
        self.processing = False
        
        # RMS monitoring
        self.rms_samples = deque(maxlen=200)  # Only keep last 200 samples to prevent memory leak
        self.max_rms = 0
        
        # Adaptive threshold calibration
        self.baseline_rms_samples = deque(maxlen=200)  # 3 seconds * 50 frames/sec = 150 max, use 200 for safety
        self.baseline_collection_time = 3.0  # seconds
        self.baseline_collected = False

        # Call tracking
        self.call_state: Optional[CallState] = None

        # Audio muting during TTS playback
        self.muted = True  # Start muted during welcome
        self.mute_lock = threading.Lock()

        # Inactivity detection
        self.last_user_speech = time.time()
        self.inactivity_timeout = 45.0  # End call after 45s of no user speech

        # Thinking sound control
        self.stop_thinking = False

        # Call recording
        self.recording_file_path: Optional[str] = None
        self.wav_file: Optional[wave.Wave_write] = None
        self.wav_lock = threading.Lock()
    
    def start(self) -> bool:
        """Start the call session."""
        try:
            logger.info(f"Starting call session with {self.sip_call.caller_addr}")
            
            # Extract caller info
            caller_id = self._extract_caller_id()
            call_id = str(uuid.uuid4())
            
            # Create conversation in database
            conv = db.create_conversation(call_id, caller_id)
            
            self.call_state = CallState(
                call_id=call_id,
                caller_id=caller_id,
                conversation_id=conv.id,
                from_tag=self.sip_call.from_tag,
                to_tag=self.sip_call.to_tag
            )
            
            self.active = True
            self.sip_call.running = True
            
            # Broadcast call status
            ws_manager.broadcast_call_status('connected', call_id, caller_id)
            db.add_log('info', 'call_started', f'Call from {caller_id}', call_id)
            
            # Start RTP receive thread first (starts muted)
            self.rtp_thread = threading.Thread(target=self._rtp_receive_loop, daemon=True)
            self.rtp_thread.start()
            
            # Small delay to ensure RTP loop is running
            time.sleep(0.2)
            
            # Play welcome message
            self._play_welcome()
            
            # Mark call as answered after welcome message finishes
            if self.call_state:
                db.mark_call_answered(self.call_state.call_id)
            
            # Clear any accumulated audio buffer and reset baseline
            with self.mute_lock:
                self.audio_buffer_8k = []
                self.recording = False
                self.last_audio_time = None
                self.baseline_rms_samples = []
                self.baseline_collected = False
                self.muted = False
            
            # Start recording
            try:
                recordings_dir = Path("data/recordings")
                recordings_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"call_{timestamp}_{call_id}.wav"
                self.recording_file_path = str(recordings_dir / filename)
                
                self.wav_file = wave.open(self.recording_file_path, 'wb')
                self.wav_file.setnchannels(1)
                self.wav_file.setsampwidth(2) # 16-bit
                self.wav_file.setframerate(8000) # 8kHz
                logger.info(f"Recording call to {self.recording_file_path}")
            except Exception as e:
                logger.error(f"Failed to start call recording: {e}")

            logger.info("Call session active, ready for user input. Adaptive threshold calibration will begin.")
            return True
        
        except Exception as e:
            logger.error(f"Error starting call session: {e}")
            self.stop()
            return False
    
    def _extract_caller_id(self) -> str:
        """Extract caller ID from SIP INVITE."""
        try:
            m = re.search(r"^From:\s*(.*)$", self.sip_call.invite_msg, re.MULTILINE)
            if m:
                from_val = m.group(1)
                # Try display name "Name" <sip:user@host>
                mname = re.search(r'"([^"]+)"', from_val)
                if mname:
                    return mname.group(1)
                # Try user part sip:user@
                muser = re.search(r'sip:([^@;>]+)', from_val)
                if muser:
                    return muser.group(1)
            return "Unknown"
        except:
            return "Unknown"
    
    def _rtp_receive_loop(self) -> None:
        """Receive RTP packets, detect utterances, and run AI pipeline."""
        logger.info("RTP receive loop started")
        
        if not self.sip_call.rtp_socket:
            logger.error("No RTP socket available")
            return
        
        self.sip_call.rtp_socket.settimeout(0.1)
        packet_count = 0
        
        while self.active and self.sip_call.running:
            try:
                # Check for inactivity - REMOVED
                # time_since_speech = time.time() - self.last_user_speech
                # if packet_count % 100 == 0:
                #      logger.info(f"Silence check: {time_since_speech:.1f}s / {self.inactivity_timeout}s")

                # if time_since_speech > self.inactivity_timeout:
                #     logger.info(f"No user speech for {self.inactivity_timeout}s, ending call due to inactivity")
                #     if self.call_state:
                #         db.add_message_by_call_id(self.call_state.call_id, 'system', 'Call ended (inactivity)')
                #         db.end_conversation(self.call_state.call_id)
                #     self.stop()
                #     break

                data, addr = self.sip_call.rtp_socket.recvfrom(2048)
                
                if len(data) < 12:
                    continue  # Invalid RTP packet
                
                # Parse RTP header (12 bytes)
                header = struct.unpack('!BBHII', data[:12])
                payload = data[12:]
                
                # Extract payload type from header
                payload_type = header[1] & 0x7F  # Lower 7 bits
                
                packet_count += 1
                if packet_count % 100 == 1:
                    logger.debug(f"Received RTP packet {packet_count}, payload type: {payload_type}, size: {len(payload)} bytes")
                
                if not audioop:
                    continue
                
                # μ-law (8-bit) -> 16-bit PCM @8kHz
                try:
                    pcm_8k = audioop.ulaw2lin(payload, 2)
                    
                    # Record incoming audio (User)
                    self._write_audio_to_recording(pcm_8k)
                    
                    # Check if we're muted (bot is speaking)
                    with self.mute_lock:
                        is_muted = self.muted
                    
                    if is_muted:
                        # Bot is speaking, discard incoming audio
                        rms = audioop.rms(pcm_8k, 2)
                        self.rms_samples.append(rms)
                        if packet_count % 200 == 1:
                            avg_rms = sum(list(self.rms_samples)[-200:]) / min(len(self.rms_samples), 200)
                            logger.debug(f"Audio muted (bot speaking) - RMS: {rms}, Avg: {avg_rms:.1f}")
                        continue
                    
                    # Voice activity detection
                    rms = audioop.rms(pcm_8k, 2)
                    
                    # Track RMS statistics
                    self.rms_samples.append(rms)
                    if rms > self.max_rms:
                        self.max_rms = rms
                    
                    # Adaptive threshold: collect baseline noise floor
                    if self.adaptive_threshold and not self.baseline_collected:
                        self.baseline_rms_samples.append(rms)
                        if len(self.baseline_rms_samples) >= int(self.baseline_collection_time * 50):
                            # Calculate noise floor statistics
                            sorted_baseline = sorted(self.baseline_rms_samples)
                            noise_floor = sorted_baseline[len(sorted_baseline) // 2]  # Median
                            percentile_75_idx = int(len(sorted_baseline) * 0.75)
                            peak_noise = sorted_baseline[percentile_75_idx]
                            
                            # Set adaptive threshold
                            adaptive_value = noise_floor + int((peak_noise - noise_floor) * 2.0)
                            # Allow higher threshold for noisy lines (up to 2000 RMS)
                            self.voice_threshold = max(150, min(2000, adaptive_value))
                            self.baseline_collected = True
                            logger.info(f"Adaptive threshold calibrated: noise_floor={noise_floor}, peak_noise={peak_noise}, threshold={self.voice_threshold}")
                    
                    # Log RMS levels for debugging (reduced frequency)
                    if packet_count % 200 == 1:
                        avg_rms = sum(list(self.rms_samples)[-200:]) / min(len(self.rms_samples), 200)
                        status = "CALIBRATING" if (self.adaptive_threshold and not self.baseline_collected) else "ACTIVE"
                        logger.info(f"Audio [{status}] - RMS: {rms}, Avg: {avg_rms:.1f}, Max: {self.max_rms}, Threshold: {self.voice_threshold}")
                    
                    # Always update pre-speech buffer
                    self.pre_speech_buffer.append(pcm_8k)

                    if rms > self.voice_threshold:
                        self.consecutive_speech_frames += 1
                        
                        # Only start recording if we have 3 consecutive frames of "speech" (60ms)
                        # This filters out clicks
                        if not self.recording and self.consecutive_speech_frames > 3:
                            self.recording = True
                            logger.info(f"Started recording from caller (RMS: {rms}, threshold: {self.voice_threshold})")
                            # Add pre-speech buffer to grab the start of the word
                            self.audio_buffer_8k.extend(self.pre_speech_buffer)
                            self.pre_speech_buffer.clear()
                            
                        # If already recording, just append
                        if self.recording:
                            self.audio_buffer_8k.append(pcm_8k)
                            self.last_audio_time = time.time()
                            
                    elif self.recording:
                        # Reset consecutive counter if below threshold
                        self.consecutive_speech_frames = 0
                        # Still buffer tail during trailing silence
                        self.audio_buffer_8k.append(pcm_8k)
                    else:
                        self.consecutive_speech_frames = 0
                    
                    # Check for end of utterance
                    if self.recording and self.last_audio_time:
                        if (time.time() - self.last_audio_time) >= self.silence_threshold and not self.processing:
                            # Finalize current buffer and process in background
                            audio_chunks = self.audio_buffer_8k
                            self.audio_buffer_8k = []
                            self.recording = False
                            self.last_audio_time = None
                            self.consecutive_speech_frames = 0 # Reset
                            self.processing = True
                            threading.Thread(
                                target=self._process_utterance,
                                args=(audio_chunks,),
                                daemon=True
                            ).start()
                
                except Exception as e:
                    logger.error(f"Error handling incoming audio: {e}", exc_info=True)
            
            except socket.timeout:
                # Timeout is normal for UDP socket with timeout
                continue
            except OSError as e:
                if e.errno == 9:  # EBADF - Socket closed
                    logger.info("RTP socket closed, stopping receive loop")
                    break
                elif self.active:
                    logger.error(f"Error in RTP receive: {e}")
                    break
            except Exception as e:
                if self.active:
                    logger.error(f"Error in RTP receive: {e}")

        logger.info("RTP receive loop stopped")
        self.stop()

    def _build_system_context(self, user_text: str) -> tuple[list, list, list, list, list]:
        """
        Build system prompt and context for LLM.
        Returns: (messages, calendar_event_ids, email_ids, weather_data_list, tomtom_data_list)
        """
        messages = []
        calendar_event_ids = []
        email_ids = []
        weather_data_list = []
        tomtom_data_list = []
        
        # Base Persona
        persona = Config.BOT_PERSONA
        
        # 1. Unconditionally inject current date/time
        try:
            user_tz = pytz.timezone(Config.TIMEZONE)
            current_time = datetime.now(user_tz)
            datetime_str = current_time.strftime("%A, %B %d, %Y at %I:%M %p %Z")
            current_date_str = current_time.strftime("%A, %B %d, %Y")
            tomorrow_date = current_time + timedelta(days=1)
            tomorrow_date_str = tomorrow_date.strftime("%A, %B %d, %Y")
            persona = f"{persona}\n\nCurrent date and time: {datetime_str}"
            persona += f"\n\nIMPORTANT - Date interpretation (all dates are in {Config.TIMEZONE} timezone):"
            persona += f"\n- 'Today' refers to {current_date_str}"
            persona += f"\n- 'Tomorrow' refers to {tomorrow_date_str}"
            persona += f"\n- When the user asks about 'tomorrow', they mean events on {tomorrow_date_str}, NOT today"
            persona += f"\n- Always interpret relative dates (today, tomorrow, etc.) based on the current date shown above"
            logger.info(f"Injected current date/time: {datetime_str}")
        except Exception as e:
            logger.warning(f"Could not inject date/time: {e}")
            # Fallback to UTC if timezone is invalid
            current_time = datetime.now(timezone.utc)
            current_date_str = current_time.strftime("%A, %B %d, %Y")
            tomorrow_date = current_time + timedelta(days=1)
            tomorrow_date_str = tomorrow_date.strftime("%A, %B %d, %Y")
            persona = f"{persona}\n\nCurrent date and time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p UTC')}"
            persona += f"\n\nIMPORTANT - Date interpretation (all dates are in UTC timezone):"
            persona += f"\n- 'Today' refers to {current_date_str}"
            persona += f"\n- 'Tomorrow' refers to {tomorrow_date_str}"
            persona += f"\n- When the user asks about 'tomorrow', they mean events on {tomorrow_date_str}, NOT today"
            persona += f"\n- Always interpret relative dates (today, tomorrow, etc.) based on the current date shown above"

        # 2. Add email context (on-demand)
        email_keywords = ['email', 'e-mail', 'mail', 'inbox', 'message']
        is_asking_about_email = any(keyword in user_text.lower() for keyword in email_keywords)

        if is_asking_about_email and Config.EMAIL_ADDRESS and Config.EMAIL_APP_PASSWORD:
            try:
                email_client.set_credentials(
                    Config.EMAIL_ADDRESS,
                    Config.EMAIL_APP_PASSWORD,
                    Config.EMAIL_IMAP_SERVER,
                    Config.EMAIL_IMAP_PORT
                )
                unread_emails, error = email_client.fetch_unread_emails(limit=3)
                if not error and unread_emails:
                    email_info, e_ids = email_client.format_emails_for_llm_with_refs(unread_emails)
                    persona = f"{persona}\n\n{email_info}"
                    email_ids = e_ids
                    logger.info(f"Added {len(unread_emails)} unread emails to context")
                elif not error and unread_emails is not None:
                    persona = f"{persona}\n\nYou have no unread emails."
            except Exception as e:
                logger.warning(f"Could not fetch emails: {e}")

        # 2.5. Add weather context (on-demand)
        weather_keywords = ['weather', 'temperature', 'temp', 'rain', 'snow', 'sunny', 'cloudy', 'forecast', 'humid', 'wind']
        is_asking_about_weather = any(keyword in user_text.lower() for keyword in weather_keywords)

        if is_asking_about_weather and Config.OPENWEATHER_API_KEY:
            try:
                # Try to extract location from user text
                import re
                # Common patterns: "weather in [location]", "weather for [location]", etc.
                location_patterns = [
                    r'(?:weather|temperature|temp|forecast|rain|snow|sunny|cloudy)\s+(?:in|at|for)\s+([a-zA-Z\s,]+?)(?:\s+today|\s+tomorrow|\s*\?|\s*$)',
                    r'(?:how\'s|what\'s|hows|whats)\s+(?:the\s+)?(?:weather|temperature)\s+(?:in|at|for)\s+([a-zA-Z\s,]+?)(?:\s+today|\s+tomorrow|\s*\?|\s*$)',
                    r'(?:is\s+it|will\s+it)\s+(?:rain|snow|sunny|cloudy)(?:ing)?\s+(?:in|at)\s+([a-zA-Z\s,]+?)(?:\s+today|\s+tomorrow|\s*\?|\s*$)',
                    r'(?:what|how).*?(?:weather|temperature).*?(?:is|like).*?(?:in|at|for)\s+([a-zA-Z\s,]+?)(?:\s+today|\s+tomorrow|\s*\?|\s*$)',
                    r'(?:weather|temperature).*?(?:like|is).*?(?:in|at|for)\s+([a-zA-Z\s,]+?)(?:\s+today|\s+tomorrow|\s*\?|\s*$)',
                    r'(?:can you|could you).*?(?:tell|let me know|check).*?(?:weather|temperature).*?(?:in|at|for)\s+([a-zA-Z\s,]+?)(?:\s+today|\s+tomorrow|\s*\?|\s*$)',
                ]

                location = None
                for pattern in location_patterns:
                    match = re.search(pattern, user_text.lower())
                    if match:
                        location = match.group(1).strip()
                        break

                if location:
                    # Clean up location (remove extra words)
                    location = re.sub(r'\s+(today|tomorrow|right now|currently)$', '', location)

                    # Get weather data
                    weather_data = weather_client.get_weather(location, units="imperial")

                    if weather_data:
                        # Store weather data for database reference
                        weather_data_list.append(weather_data)

                        # Format weather info with marker
                        units_symbol = "°F" if weather_data.get("units") == "imperial" else "°C"
                        weather_info = f"\n\nWeather data [WEATHER:0]:"
                        weather_info += f"\n- Location: {weather_data['location']}, {weather_data.get('country', '')}"
                        weather_info += f"\n- Temperature: {weather_data['temperature']}{units_symbol}"
                        weather_info += f"\n- Feels like: {weather_data.get('feels_like')}{units_symbol}"
                        weather_info += f"\n- Conditions: {weather_data['description']}"
                        weather_info += f"\n- Humidity: {weather_data.get('humidity')}%"
                        if weather_data.get('wind_speed'):
                            weather_info += f"\n- Wind speed: {weather_data['wind_speed']} mph"

                        persona = f"{persona}{weather_info}"
                        logger.info(f"Added weather for {location} to context: {weather_data['temperature']}°F, {weather_data['description']}")
                    else:
                        persona = f"{persona}\n\nNote: Could not fetch weather for '{location}'. The location might not be found or the API key might be invalid. Ask the user to provide a valid city name."
                else:
                    # User is asking about weather but didn't specify location
                    persona = f"{persona}\n\nNote: User is asking about weather but didn't specify a location. Ask them which city or location they want weather for."

            except Exception as e:
                logger.warning(f"Could not fetch weather: {e}")

        # 2.75. Add TomTom context (on-demand for traffic, directions, POI)
        tomtom_keywords = {
            'directions': ['directions', 'route', 'drive', 'navigate', 'how do i get', 'how to get'],
            'traffic': ['traffic', 'congestion', 'delays', 'accidents', 'incidents'],
            'poi': ['find', 'nearest', 'nearby', 'restaurants', 'gas station', 'hotel', 'cafe', 'coffee', 'food', 'atm', 'pharmacy']
        }

        is_asking_tomtom = False
        tomtom_type = None

        for tt_type, keywords in tomtom_keywords.items():
            if any(keyword in user_text.lower() for keyword in keywords):
                is_asking_tomtom = True
                tomtom_type = tt_type
                break

        if is_asking_tomtom and Config.TOMTOM_API_KEY:
            try:
                import re

                tomtom_data = None

                if tomtom_type == 'directions':
                    # Extract origin and destination
                    # Patterns: "directions from X to Y", "how do I get from X to Y", "navigate from X to Y"
                    patterns = [
                        r'(?:directions|route|drive|navigate|get)\s+from\s+([^to]+?)\s+to\s+(.+?)(?:\s+would|\s+please|\s+thanks|\.|\?|$)',
                        r'(?:how do i get|how to get)\s+from\s+([^to]+?)\s+to\s+(.+?)(?:\s+would|\s+please|\s+thanks|\.|\?|$)',
                    ]

                    origin = None
                    destination = None

                    for pattern in patterns:
                        match = re.search(pattern, user_text.lower())
                        if match:
                            origin = match.group(1).strip()
                            destination = match.group(2).strip()

                            # Clean up extra words at the end
                            origin = re.sub(r'\s+(would|please|thanks|thank you|be great|be good).*$', '', origin)
                            destination = re.sub(r'\s+(would|please|thanks|thank you|be great|be good).*$', '', destination)

                            break

                    if origin and destination:
                        tomtom_data = tomtom_client.get_directions(origin, destination)
                        if tomtom_data:
                            tomtom_data_list.append(tomtom_data)
                            dist_miles = tomtom_data.get('distance_miles', 0)
                            time_min = tomtom_data.get('travel_time_minutes', 0)

                            persona += f"\n\nDirections [TOMTOM:0]:"
                            persona += f"\n- From: {origin}"
                            persona += f"\n- To: {destination}"
                            persona += f"\n- Distance: {dist_miles} miles"
                            persona += f"\n- Travel time: {time_min} minutes"

                            logger.info(f"Added directions from {origin} to {destination}")
                    else:
                        persona += f"\n\nNote: User is asking for directions but didn't specify origin and destination. Ask them for both locations."

                elif tomtom_type == 'traffic':
                    # Extract location for traffic check
                    patterns = [
                        r'traffic\s+(?:in|near|around|on)\s+([a-zA-Z\s,]+?)(?:\?|$)',
                        r'(?:is there|any)\s+traffic\s+(?:in|near|on)\s+([a-zA-Z\s,]+?)(?:\?|$)',
                        r'traffic.*?(?:like|is).*?(?:in|near|around|on)\s+([a-zA-Z\s,]+?)(?:\?|$)',
                        r'(?:what|how).*?traffic.*?(?:in|near|around|on)\s+([a-zA-Z\s,]+?)(?:\?|$)',
                        r'check.*?traffic.*?(?:in|near|around|on)\s+([a-zA-Z\s,]+?)(?:\?|$)',
                    ]

                    location = None

                    for pattern in patterns:
                        match = re.search(pattern, user_text.lower())
                        if match:
                            location = match.group(1).strip()
                            break

                    if location:
                        tomtom_data = tomtom_client.get_traffic_incidents(location, radius_km=10)
                        if tomtom_data:
                            tomtom_data_list.append(tomtom_data)
                            incident_count = tomtom_data.get('incident_count', 0)

                            persona += f"\n\nTraffic information [TOMTOM:0]:"
                            persona += f"\n- Location: {location}"
                            persona += f"\n- Incidents found: {incident_count}"

                            if incident_count > 0:
                                for i, incident in enumerate(tomtom_data.get('incidents', [])[:3], 1):
                                    persona += f"\n- Incident {i}: {incident['description']} on {incident['road']}"

                            logger.info(f"Added traffic info for {location}: {incident_count} incidents")
                    else:
                        persona += f"\n\nNote: User is asking about traffic but didn't specify a location. Ask them where they want to check traffic."

                elif tomtom_type == 'poi':
                    # Extract POI search query
                    patterns = [
                        r'(?:find|nearest|nearby|locate)\s+(?:me\s+)?(?:a\s+)?(?:some\s+)?([a-zA-Z\s]+?)(?:\s+near|\s+in|\s+around|\?|$)',
                        r'where (?:is|are|can i find)\s+(?:the\s+)?(?:nearest|closest|a|some)?\s*([a-zA-Z\s]+?)(?:\s+near|\s+in|\?|$)',
                        r'(?:looking for|search for|need)\s+(?:a\s+)?(?:some\s+)?([a-zA-Z\s]+?)(?:\s+near|\s+in|\s+around|\?|$)',
                    ]

                    poi_query = None

                    for pattern in patterns:
                        match = re.search(pattern, user_text.lower())
                        if match:
                            poi_query = match.group(1).strip()
                            break

                    if poi_query:
                        tomtom_data = tomtom_client.search_poi(poi_query, limit=5)
                        if tomtom_data:
                            tomtom_data_list.append(tomtom_data)
                            results = tomtom_data.get('results', [])

                            persona += f"\n\nPoints of Interest [TOMTOM:0]:"
                            persona += f"\n- Search: {poi_query}"
                            persona += f"\n- Results found: {len(results)}"

                            for i, poi in enumerate(results[:3], 1):
                                persona += f"\n- {i}. {poi['name']} - {poi['address']}"

                            logger.info(f"Added POI search for '{poi_query}': {len(results)} results")
                    else:
                        persona += f"\n\nNote: User is searching for a place but query is unclear. Ask them what they're looking for."

            except Exception as e:
                logger.warning(f"Could not fetch TomTom data: {e}")

        # 3. Add calendar context
        if Config.CALENDAR_URL:
            try:
                calendar_client.set_calendar_url(Config.CALENDAR_URL)
                # Fetch next 30 days of events
                upcoming_events = calendar_client.get_upcoming_events(days=30, limit=20, user_timezone=Config.TIMEZONE)
                
                if upcoming_events:
                    calendar_info, c_ids = calendar_client.format_events_for_llm_with_refs(upcoming_events, Config.TIMEZONE)
                    persona = f"{persona}\n\nYou have access to the user's calendar. {calendar_info}"
                    calendar_event_ids = c_ids
                    logger.info(f"Added {len(upcoming_events)} calendar events to context")
            except Exception as e:
                logger.warning(f"Could not fetch calendar events: {e}")

        # 4. Add marker instructions if needed
        if calendar_event_ids or email_ids or weather_data_list or tomtom_data_list:
            persona += """

IMPORTANT: When referring to specific calendar events, emails, weather data, or TomTom results, use these markers:
- For calendar events: [CALENDAR:0], [CALENDAR:1], etc. (matching the indices shown above)
- For emails: [EMAIL:0], [EMAIL:1], etc. (matching the indices shown above)
- For weather data: [WEATHER:0], [WEATHER:1], etc. (matching the indices shown above)
- For TomTom data: [TOMTOM:0], [TOMTOM:1], etc. (matching the indices shown above)

Example: "You have a meeting tomorrow [CALENDAR:0] and an email from John [EMAIL:0]. The weather in New York is sunny [WEATHER:0]. The route to Boston is 200 miles [TOMTOM:0]."

Only use markers for events/emails/weather/TomTom data explicitly listed above. Do not hallucinate markers."""

        messages.append({'role': 'system', 'content': persona})

        return messages, calendar_event_ids, email_ids, weather_data_list, tomtom_data_list
    
    def _process_utterance(self, chunks_8k: list) -> None:
        """Process recorded audio through AI pipeline."""
        try:
            logger.info(f"Processing utterance ({len(chunks_8k)} chunks)...")
            
            if not chunks_8k:
                logger.warning("No audio chunks to process")
                self.processing = False
                return
            
            # Combine all 8kHz chunks
            combined_8k = b''.join(chunks_8k)
            duration_8k = len(combined_8k) / 2 / 8000  # 16-bit samples at 8kHz
            logger.info(f"Processing {duration_8k:.2f}s of audio ({len(combined_8k)} bytes @ 8kHz)")
            
            # Check if we have enough audio
            if duration_8k < 0.3:
                logger.warning(f"Audio too short ({duration_8k:.2f}s), skipping transcription")
                self.processing = False
                return
            
            # Upsample from 8kHz to 16kHz for better Whisper/Groq accuracy
            if audioop:
                logger.debug("Upsampling audio from 8kHz to 16kHz")
                combined_16k, _ = audioop.ratecv(combined_8k, 2, 1, 8000, 16000, None)
                
                # Apply audio normalization
                max_amp = audioop.max(combined_16k, 2)
                avg_amp = audioop.rms(combined_16k, 2)
                logger.info(f"Audio levels - Peak: {max_amp}, RMS: {avg_amp}")
                
                # Check if audio has sufficient energy
                if avg_amp < 50:
                    logger.warning(f"Audio RMS too low ({avg_amp}), likely silence/noise. Skipping.")
                    self.processing = False
                    return
                
                if max_amp > 0:
                    # Normalize to 90% of maximum
                    target_amp = int(32767 * 0.9)
                    factor = target_amp / max_amp
                    combined_16k = audioop.mul(combined_16k, 2, factor)
                    logger.info(f"Normalized audio by factor {factor:.2f}")
            else:
                combined_16k = combined_8k
            
            # Write to WAV
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)  # 16kHz for better transcription
                w.writeframes(combined_16k)
            wav_data = wav_buffer.getvalue()
            
            # Transcribe
            call_id = self.call_state.call_id if self.call_state else None
            text, error = transcriber.transcribe_sync(wav_data, call_id, format='wav')
            
            if error or not text:
                logger.warning(f"Transcription failed: {error}")
                self.processing = False
                return
            
            # Filter out common hallucinations
            hallucinations = [
                "thank you", "thank you.", "thanks", "thanks.",
                "bye", "bye.", "goodbye", "goodbye.",
                "thank you for watching", "you", "you."
            ]
            if text.strip().lower() in hallucinations:
                logger.warning(f"Detected hallucination: '{text}' - skipping")
                self.processing = False
                return
            
            logger.info(f"Transcribed: {text}")

            # Update last user speech time
            self.last_user_speech = time.time()

            # Save user message
            if self.call_state and self.call_state.conversation_id:
                db.add_message(self.call_state.conversation_id, 'user', text)
                ws_manager.broadcast_message(
                    self.call_state.conversation_id, 'user', text, call_id
                )

            # Play gentle "thinking" sound while processing
            thinking_thread = threading.Thread(target=self._play_thinking_sound, daemon=True)
            thinking_thread.start()

            try:
                # Build system context with unconditional date/time
                conversation_messages, calendar_event_ids, email_ids, weather_data_list, tomtom_data_list = self._build_system_context(text)

                if self.call_state and self.call_state.conversation_id:
                    messages = db.get_messages(self.call_state.conversation_id)
                    # Get last 10 non-system messages
                    recent_messages = [m for m in messages if m.role != 'system'][-10:]
                    for msg in recent_messages:
                        conversation_messages.append({
                            'role': msg.role,
                            'content': msg.content
                        })

                # Get Ollama response using chat endpoint with history
                response, error, model = gpt_client.get_chat_response_sync(conversation_messages, call_id)

                if error or not response:
                    response = "I'm sorry, I couldn't process that request."

                logger.info(f"Response: {response}")
            finally:
                # Stop thinking sound
                self.stop_thinking = True
                thinking_thread.join(timeout=1.0)

            # Store weather data in database
            weather_data_ids = []
            for weather_data in weather_data_list:
                try:
                    weather_id = db.add_weather_data(weather_data)
                    if weather_id:
                        weather_data_ids.append(weather_id)
                        logger.info(f"Stored weather data for {weather_data['location']}: ID {weather_id}")
                except Exception as e:
                    logger.error(f"Failed to store weather data: {e}")

            # Store TomTom data in database
            tomtom_data_ids = []
            for tomtom_data in tomtom_data_list:
                try:
                    tomtom_id = db.add_tomtom_data(tomtom_data)
                    if tomtom_id:
                        tomtom_data_ids.append(tomtom_id)
                        logger.info(f"Stored TomTom data ({tomtom_data['type']}): ID {tomtom_id}")
                except Exception as e:
                    logger.error(f"Failed to store TomTom data: {e}")

            # Save assistant message and parse markers for references
            if self.call_state and self.call_state.conversation_id:
                # Save message first to get message_id
                saved_message = db.add_message(self.call_state.conversation_id, 'assistant', response, model=model)

                # Parse AI response for markers and create reference records
                if saved_message and (calendar_event_ids or email_ids or weather_data_ids or tomtom_data_ids):
                    try:
                        # Extract calendar markers [CALENDAR:N]
                        calendar_markers = re.findall(r'\[CALENDAR:(\d+)\]', response)
                        for marker_index_str in calendar_markers:
                            marker_index = int(marker_index_str)
                            if marker_index < len(calendar_event_ids):
                                db.add_calendar_ref(
                                    saved_message.id,
                                    calendar_event_ids[marker_index],
                                    marker_index
                                )
                                logger.info(f"Created calendar reference: message={saved_message.id}, event={calendar_event_ids[marker_index]}, index={marker_index}")
                            else:
                                logger.warning(f"AI used invalid calendar marker index: {marker_index} (max: {len(calendar_event_ids) - 1})")

                        # Extract email markers [EMAIL:N]
                        email_markers = re.findall(r'\[EMAIL:(\d+)\]', response)
                        for marker_index_str in email_markers:
                            marker_index = int(marker_index_str)
                            if marker_index < len(email_ids):
                                db.add_email_ref(
                                    saved_message.id,
                                    email_ids[marker_index],
                                    marker_index
                                )
                                logger.info(f"Created email reference: message={saved_message.id}, email={email_ids[marker_index]}, index={marker_index}")
                            else:
                                logger.warning(f"AI used invalid email marker index: {marker_index} (max: {len(email_ids) - 1})")

                        # Extract weather markers [WEATHER:N]
                        weather_markers = re.findall(r'\[WEATHER:(\d+)\]', response)
                        for marker_index_str in weather_markers:
                            marker_index = int(marker_index_str)
                            if marker_index < len(weather_data_ids):
                                db.add_weather_ref(
                                    saved_message.id,
                                    weather_data_ids[marker_index],
                                    marker_index
                                )
                                logger.info(f"Created weather reference: message={saved_message.id}, weather={weather_data_ids[marker_index]}, index={marker_index}")
                            else:
                                logger.warning(f"AI used invalid weather marker index: {marker_index} (max: {len(weather_data_ids) - 1})")

                        # Extract TomTom markers [TOMTOM:N]
                        tomtom_markers = re.findall(r'\[TOMTOM:(\d+)\]', response)
                        for marker_index_str in tomtom_markers:
                            marker_index = int(marker_index_str)
                            if marker_index < len(tomtom_data_ids):
                                db.add_tomtom_ref(
                                    saved_message.id,
                                    tomtom_data_ids[marker_index],
                                    marker_index
                                )
                                logger.info(f"Created TomTom reference: message={saved_message.id}, tomtom={tomtom_data_ids[marker_index]}, index={marker_index}")
                            else:
                                logger.warning(f"AI used invalid TomTom marker index: {marker_index} (max: {len(tomtom_data_ids) - 1})")
                    except Exception as e:
                        logger.error(f"Error creating message references: {e}", exc_info=True)

                # Fetch full message with refs for broadcasting
                calendar_refs_data = None
                email_refs_data = None
                weather_refs_data = None
                tomtom_refs_data = None
                if saved_message and (calendar_event_ids or email_ids or weather_data_ids or tomtom_data_ids):
                    full_message = db.get_message_with_refs(saved_message.id)
                    if full_message:
                        calendar_refs_data = full_message.get('calendar_refs', [])
                        email_refs_data = full_message.get('email_refs', [])
                        weather_refs_data = full_message.get('weather_refs', [])
                        tomtom_refs_data = full_message.get('tomtom_refs', [])

                ws_manager.broadcast_message(
                    self.call_state.conversation_id, 'assistant', response, call_id,
                    calendar_refs=calendar_refs_data,
                    email_refs=email_refs_data,
                    weather_refs=weather_refs_data,
                    tomtom_refs=tomtom_refs_data,
                    model=model
                )
            
            # Generate and play TTS
            self._play_tts(response)
        
        except Exception as e:
            logger.error(f"Error processing utterance: {e}", exc_info=True)
        finally:
            self.processing = False
            # Force garbage collection to free memory
            import gc
            gc.collect()
    
    def _play_thinking_sound(self) -> None:
        """Play a gentle thinking sound while processing."""
        try:
            import math
            import numpy as np

            # Generate a soft, gentle tone (440 Hz, very quiet)
            sample_rate = 8000
            duration = 0.3  # 300ms beep
            frequency = 500  # Soft tone
            pause_duration = 0.5  # 500ms pause between beeps

            # Generate single beep
            t = np.linspace(0, duration, int(sample_rate * duration))
            beep = np.sin(2 * np.pi * frequency * t)

            # Apply fade in/out envelope for smooth sound
            fade_samples = int(sample_rate * 0.05)  # 50ms fade
            envelope = np.ones_like(beep)
            envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
            envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
            beep = beep * envelope

            # Very low volume (5% of max)
            beep = beep * 0.05
            beep = (beep * 32767).astype(np.int16)

            # Generate silence
            silence = np.zeros(int(sample_rate * pause_duration), dtype=np.int16)

            # Convert to bytes
            beep_bytes = beep.tobytes()
            silence_bytes = silence.tobytes()

            logger.debug("Playing thinking sound...")
            self.stop_thinking = False

            # Play beeps until stopped
            while not self.stop_thinking and self.active:
                # Play beep
                if audioop:
                    ulaw_beep = audioop.lin2ulaw(beep_bytes, 2)
                    for i in range(0, len(ulaw_beep), 160):  # 20ms chunks
                        if self.stop_thinking or not self.active:
                            break
                        chunk = ulaw_beep[i:i+160]
                        if len(chunk) == 160:
                            self.sip_call.send_rtp(chunk, payload_type=0)
                        time.sleep(0.02)

                # Play silence
                if self.stop_thinking or not self.active:
                    break
                for i in range(0, len(silence_bytes), 320):  # 20ms chunks at 8kHz
                    if self.stop_thinking or not self.active:
                        break
                    time.sleep(0.02)

            logger.debug("Thinking sound stopped")

        except ImportError:
            logger.warning("numpy not available, skipping thinking sound")
        except Exception as e:
            logger.error(f"Error playing thinking sound: {e}")

    def _play_welcome(self) -> None:
        """Play welcome message."""
        welcome = "Hello! How can I help you today?"
        db.add_log('info', 'playing_welcome', welcome,
                   self.call_state.call_id if self.call_state else None)
        logger.info(f"Playing welcome message: {welcome}")
        self._play_tts(welcome)
    
    def _play_tts(self, text: str) -> None:
        """Generate TTS and play over RTP while muting incoming audio."""
        try:
            # Mute incoming audio to prevent feedback loop
            with self.mute_lock:
                self.muted = True
            logger.debug("Muted incoming audio for TTS playback")

            # Reset inactivity timer since we're actively in conversation
            self.last_user_speech = time.time()

            call_id = self.call_state.call_id if self.call_state else None
            audio_data, error = tts_client.synthesize_sync(text, call_id)

            if error or not audio_data:
                logger.error(f"TTS failed: {error}")
                return

            # Convert and send over RTP
            self._send_audio_rtp(audio_data)

            # Add delay after playback for acoustic echo to settle
            time.sleep(0.5)

            # Reset inactivity timer after TTS finishes - user should respond soon
            self.last_user_speech = time.time()

        finally:
            # Clear any audio buffer that accumulated during playback
            with self.mute_lock:
                if self.audio_buffer_8k:
                    logger.debug(f"Clearing {len(self.audio_buffer_8k)} buffered audio chunks from feedback")
                    self.audio_buffer_8k = []
                    self.recording = False
                    self.last_audio_time = None
                # Unmute incoming audio
                self.muted = False
            logger.debug("Unmuted incoming audio after TTS playback")
    
    def _send_audio_rtp(self, audio_data: bytes) -> None:
        """Convert audio and send over RTP."""
        try:
            try:
                from pydub import AudioSegment
                
                # Load audio (MP3 from TTS)
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
                
                # Convert to 8kHz mono 16-bit
                audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(2)
                
                # Get raw PCM
                pcm = audio.raw_data
                
                # Record outgoing audio (Assistant)
                self._write_audio_to_recording(pcm)
                
                # Chunk into 20ms (160 samples @ 8kHz = 320 bytes)
                chunk_size = 160 * 2
                for i in range(0, len(pcm), chunk_size):
                    chunk = pcm[i:i + chunk_size]
                    if len(chunk) == 0:
                        continue
                    
                    # μ-law encode
                    if audioop:
                        ulaw = audioop.lin2ulaw(chunk, 2)
                        self.sip_call.send_rtp(ulaw, payload_type=0)
                    
                    time.sleep(0.02)  # 20ms
            
            except ImportError:
                logger.warning("pydub not available, cannot play TTS audio")
        
        except Exception as e:
            logger.error(f"Error sending audio RTP: {e}")
    
    def _write_audio_to_recording(self, pcm_data: bytes) -> None:
        """Write audio chunk to recording file."""
        if self.wav_file:
            try:
                with self.wav_lock:
                    self.wav_file.writeframes(pcm_data)
            except Exception as e:
                logger.error(f"Error writing to recording file: {e}")
        else:
            # Debug: wav_file is None
            if hasattr(self, 'active') and self.active and hasattr(self, 'recording_file_path') and self.recording_file_path:
                 logger.warning("Attempted to write to recording but wav_file is None")

    def stop(self) -> None:
        """Stop the call session."""
        self.active = False
        
        # Close recording
        if self.wav_file:
            try:
                with self.wav_lock:
                    self.wav_file.close()
                self.wav_file = None
                
                # Update DB with recording path
                if self.call_state and self.recording_file_path:
                    # Update conversation with recording path using SQL directly or existing method if needed
                    # Since we don't have a direct update method for just this field, 
                    # we can use the db session
                    try:
                        with db.get_session() as session:
                            from .database import Conversation
                            conv = session.query(Conversation).filter_by(call_id=self.call_state.call_id).first()
                            if conv:
                                conv.recording_path = self.recording_file_path
                                session.commit()
                                logger.info(f"Saved recording path to DB: {self.recording_file_path}")
                    except Exception as e:
                        logger.error(f"Error saving recording path to DB: {e}")
                        
            except Exception as e:
                logger.error(f"Error closing recording file: {e}")
        
        if self.call_state:
            db.end_conversation(self.call_state.call_id)
            ws_manager.broadcast_call_status('ended', self.call_state.call_id, self.call_state.caller_id)
            db.add_log('info', 'call_ended', 'Call ended', self.call_state.call_id)

            # After a brief delay, broadcast 'idle' status to reset UI
            import threading
            def reset_to_idle():
                time.sleep(1)
                ws_manager.broadcast_call_status('idle')
            threading.Thread(target=reset_to_idle, daemon=True).start()

        if self.sip_call:
            self.sip_call.close()

        logger.info("Call session stopped")


class SIPClient:
    """Main SIP client that manages the SIP server and calls."""
    
    def __init__(self):
        self.sip_server: Optional[SimpleSIPServer] = None
        self._running = False
        self._active_sessions: dict = {}
    
    @property
    def is_registered(self) -> bool:
        """Check if SIP server is running (no registration needed)."""
        return self.sip_server.is_registered if self.sip_server else False
    
    @property
    def current_call_id(self) -> Optional[str]:
        """Get current active call ID."""
        for session in self._active_sessions.values():
            if session.active and session.call_state:
                return session.call_state.call_id
        return None
    
    def start(self) -> None:
        """Start the SIP client."""
        try:
            self._running = True
            
            # Create and start SIP server
            self.sip_server = SimpleSIPServer(
                host='0.0.0.0',
                port=Config.SIP_PORT
            )
            
            # Set call handler
            self.sip_server.set_call_handler(self._handle_call)
            
            # Start server
            if self.sip_server.start():
                db.add_log('info', 'sip_started', f'SIP listening on port {Config.SIP_PORT}')
                ws_manager.broadcast_sip_status(True, {
                    'listening': True,
                    'port': Config.SIP_PORT,
                    'extension': Config.SIP_EXTENSION
                })
                logger.info(f"SIP server ready - configure your PBX to route extension {Config.SIP_EXTENSION} to this IP:5060")
            else:
                ws_manager.broadcast_sip_status(False, {'error': 'Failed to start SIP server'})
        
        except Exception as e:
            logger.error(f"Error starting SIP client: {e}")
            ws_manager.broadcast_sip_status(False, {'error': str(e)})
    
    def _handle_call(self, sip_call: SIPCall) -> None:
        """Handle incoming call after ACK."""
        try:
            logger.info(f"Handling call from {sip_call.caller_addr}")
            
            session = CallSession(sip_call)
            
            if session.start():
                if session.call_state:
                    self._active_sessions[session.call_state.call_id] = session
                logger.info("Call session started successfully")
            else:
                logger.error("Failed to start call session")
        
        except Exception as e:
            logger.error(f"Error handling call: {e}")
    
    def stop(self) -> None:
        """Stop the SIP client."""
        self._running = False
        
        # Stop all sessions
        for session in list(self._active_sessions.values()):
            session.stop()
        self._active_sessions.clear()
        
        # Stop SIP server
        if self.sip_server:
            self.sip_server.stop()
        
        ws_manager.broadcast_sip_status(False, {'message': 'SIP client stopped'})
        db.add_log('info', 'sip_stopped', 'SIP client stopped')
    
    def restart(self) -> None:
        """Restart the SIP client."""
        db.add_log('info', 'sip_restarting', 'Restarting SIP client')
        self.stop()
        time.sleep(1)
        self.start()
    
    def hangup(self) -> None:
        """Hang up the current call."""
        for call_id, session in list(self._active_sessions.items()):
            if session.active:
                session.stop()
                del self._active_sessions[call_id]
                break
    
    def simulate_call(self, caller_id: str = "test-caller", message: str = "Hello") -> dict:
        """Simulate a call for testing."""
        if not self._running:
            return {'error': 'SIP client not running'}
        
        call_id = str(uuid.uuid4())
        
        # Create conversation
        conv = db.create_conversation(call_id, caller_id)
        
        # Save user message
        db.add_message(conv.id, 'user', message)
        ws_manager.broadcast_message(conv.id, 'user', message, call_id)
        
        # Get response
        response, error, model = gpt_client.get_response_sync(message, call_id)
        
        if response:
            db.add_message(conv.id, 'assistant', response, model=model)
            ws_manager.broadcast_message(conv.id, 'assistant', response, call_id, model=model)
        
        # End conversation
        db.end_conversation(call_id)
        
        return {
            'call_id': call_id,
            'user_message': message,
            'assistant_response': response,
            'error': error,
            'model': model
        }
