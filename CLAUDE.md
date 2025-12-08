# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SIP AI Bridge is a Docker-based voice bridge that connects VoIP calls to AI services. It receives SIP calls, transcribes speech to text via Groq's Whisper API, processes requests through a local Ollama LLM, and responds with synthesized speech using openai-edge-tts.

## Commands

### Docker Operations
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down

# Rebuild after code changes
docker build -t sip-ai-bridge .
```

### Backend Development
```bash
cd backend
pip install -r requirements.txt
python -m app.main  # Runs Flask API on port 5001
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev      # Development server
npm run build    # Production build
npm run lint     # ESLint check
```

## Architecture

### Core Components

**SIP Client (`backend/app/sip_client.py`)**
- Pure socket-based SIP implementation (NO PJSUA2 library)
- Does NOT register with PBX - PBX routes calls directly to port 5060
- Handles SIP signaling: INVITE, ACK, BYE, OPTIONS
- Manages RTP audio streams on ports 10000-10100
- Voice activity detection with adaptive threshold calibration
- Audio muting during TTS playback to prevent feedback loops

**Audio Processing Pipeline**
1. Receive μ-law encoded RTP packets (8kHz)
2. Convert to 16-bit PCM
3. Voice activity detection with adaptive threshold
4. Buffer audio until silence detected (1.5s threshold)
5. Upsample to 16kHz for transcription
6. Process through AI pipeline
7. Send TTS response as μ-law RTP packets

**Service Integration**
- `transcription.py`: Groq Whisper Large V3 for speech-to-text
- `gpt_client.py`: Local Ollama LLM (default: llama3.1)
- `tts_client.py`: openai-edge-tts for voice synthesis
- All services use httpx for HTTP requests (both sync and async versions)

**Database (`backend/app/database.py`)**
- SQLite with SQLAlchemy ORM
- Tables: Conversation, Message, Settings, CallLog
- Tracks call duration from `answered_at` (after welcome message) to `ended_at`
- WebSocket broadcasts for real-time updates

**WebSocket (`backend/app/websocket.py`)**
- Flask-SocketIO with eventlet async mode
- Events: call_status, new_message, conversation_update, sip_status, transcription, health_status
- Used for real-time dashboard updates

### Key Design Patterns

**Configuration Management**
- Environment variables loaded from `.env` file via `config.py`
- Runtime configuration updates via API endpoints saved to database
- Config class properties allow runtime updates without restart

**Call Session Lifecycle**
1. SIP server receives INVITE → sends 180 Ringing → sends 200 OK with SDP
2. Receives ACK → starts CallSession
3. Plays welcome message while muted
4. Marks call as answered, unmutes, starts adaptive threshold calibration
5. Records utterances based on voice activity detection
6. Processes: transcribe → LLM → TTS → RTP playback
7. BYE received → ends conversation, calculates duration

**Audio Feedback Prevention**
- Incoming audio is muted during TTS playback (`CallSession.muted` flag with `mute_lock`)
- Audio buffer cleared after TTS completes
- 0.5s delay after playback for acoustic echo to settle

### Frontend Architecture

**Technology Stack**
- React 18 with TypeScript
- Vite build tool
- TailwindCSS for styling
- Socket.io-client for WebSocket connection

**Structure**
- `App.tsx`: Main component with tabbed interface
- `components/`: Dashboard, Conversations, Settings, Logs views
- `hooks/useWebSocket.ts`: WebSocket connection management
- `utils/timezone.ts`: Timezone handling for display

## Important Implementation Details

### SIP Configuration
- Server listens on UDP port 5060
- NO registration needed - this is a server, not a client
- PBX must be configured to route calls to this server's IP:5060
- RTP ports: 10000-10100 (configurable via RTP_PORT_MIN/MAX env vars)
- Uses socket-level SIP implementation, not PJSUA2

### Audio Processing
- RTP payload type 0 = PCMU (μ-law) at 8kHz
- Upsamples to 16kHz for Groq transcription
- Voice threshold starts at 100, calibrates adaptively during first 3 seconds
- Silence threshold: 1.5 seconds of RMS below threshold
- Audio normalization: targets 90% of maximum amplitude

### Database Migrations
- `_migrate_answered_at_column()` handles schema changes automatically
- Duration calculation uses `answered_at` if available, otherwise `started_at`
- Active conversations auto-marked as completed if older than 5 minutes and not in active sessions

### Timezone Support
- Configurable via TIMEZONE env var or Settings UI
- Used for display formatting throughout frontend
- Defaults to UTC if not specified

## External Service URLs

- Groq API: `https://api.groq.com/openai/v1/audio/transcriptions`
- Ollama: Configurable (default: `http://host.docker.internal:11434` in Docker)
- TTS: Configurable openai-edge-tts instance

## Ports

- 5060: SIP (UDP/TCP)
- 5001: Flask API
- 3002: Web UI (served by Flask in production)
- 10000-10100: RTP media streams

## Testing

Use the API test endpoints:
- `POST /api/test/transcribe` - Upload audio file for transcription test
- `POST /api/test/ollama` - Test LLM with text input
- `POST /api/test/tts` - Test TTS synthesis
- `POST /api/sip/simulate` - Simulate a call without SIP connection
