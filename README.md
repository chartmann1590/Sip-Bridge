# SIP AI Bridge

A Docker-based SIP voice bridge that connects VoIP calls to AI services for intelligent voice interactions.

## Features

- **SIP Integration**: Connects to any SIP-compatible PBX on a configurable extension
- **Speech-to-Text**: Uses Groq's Whisper API for fast, accurate transcription
- **AI Responses**: Integrates with local Ollama instance for intelligent responses
- **Text-to-Speech**: Uses openai-edge-tts for natural voice synthesis
- **Web Dashboard**: Real-time monitoring and configuration interface
- **Persistent Storage**: SQLite database for conversation history and settings
- **Email Notifications**: Automated email alerts for logs and events

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Docker Container                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  SIP Client  │───▶│ Flask Backend│◀──▶│  React Frontend  │  │
│  │  (PJSUA2)    │    │  + WebSocket │    │  (Port 3000)     │  │
│  │  Port 5060   │    │  Port 5001   │    └──────────────────┘  │
│  └──────────────┘    └──────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────┐        ┌─────────┐        ┌─────────────┐
    │ SIP PBX │        │  Groq   │        │ Ollama + TTS │
    └─────────┘        └─────────┘        └─────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Groq API key (for speech-to-text)
- Running Ollama instance
- Running TTS service (openai-edge-tts)

### Configuration

1. Copy the environment template and edit with your settings:

```bash
cp .env.example .env
# Edit .env with your actual values
```

2. Configure the `.env` file:

```bash
# Groq API
GROQ_API_KEY=your_groq_api_key_here

# SIP Configuration
SIP_HOST=your_sip_server_ip
SIP_PORT=5060
SIP_USERNAME=mumble-bridge
SIP_PASSWORD=your_sip_password
SIP_EXTENSION=5000

# Ollama (local LLM)
# Use host.docker.internal to access host's Ollama from Docker
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1

# TTS Service (openai-edge-tts)
TTS_URL=http://your_tts_server_ip:5050
TTS_API_KEY=your_api_key_here
TTS_VOICE=en-US-GuyNeural

# Timezone (optional, defaults to UTC)
# Set the timezone for date and time displays throughout the application
# Examples: America/New_York, Europe/London, Asia/Tokyo, etc.
TIMEZONE=UTC
```

### Running with Docker Compose

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Accessing the Web Interface

Once running, access the web dashboard at:

- **Web UI**: http://localhost:3000
- **API**: http://localhost:5001

## Web Interface

### Dashboard

- Real-time service health monitoring
- Current call status and controls
- Recent activity logs
- Quick statistics

### Conversations

- Live message feed during calls
- Historical conversation browser
- Export conversations to text files
- Search and filter capabilities

### Settings

- SIP server configuration
- API keys management
- Voice selection for TTS
- Service endpoint configuration
- Timezone configuration (can be set in UI or .env file)

## API Endpoints

### Health & Status

- `GET /api/health` - Health check for all services
- `GET /api/status` - Current bridge status

### Configuration

- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration
- `GET /api/voices` - List available TTS voices

### Conversations

- `GET /api/conversations` - List conversations
- `GET /api/conversations/:call_id` - Get specific conversation
- `GET /api/messages` - Get recent messages

### SIP Control

- `POST /api/sip/restart` - Restart SIP client
- `POST /api/sip/hangup` - Hang up current call

### Testing

- `POST /api/test/transcribe` - Test transcription with audio file
- `POST /api/test/ollama` - Test Ollama with text
- `POST /api/test/tts` - Test TTS synthesis

## Development

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m app.main

# Frontend
cd frontend
npm install
npm run dev
```

### Building the Docker Image

```bash
docker build -t sip-ai-bridge .
```

## Services Integration

### Groq (Speech-to-Text)

Uses Groq's Whisper Large V3 model for transcription:
- API Docs: https://console.groq.com/docs/api-reference#audio-transcription

### Ollama (AI Responses)

Local LLM integration:
- Website: https://ollama.com
- Usage: `POST /api/generate` or `POST /api/chat`

### openai-edge-tts (Text-to-Speech)

OpenAI-compatible TTS endpoint:
- GitHub: https://github.com/travisvn/openai-edge-tts
- Endpoint: `POST /v1/audio/speech`

## Troubleshooting

### SIP Not Registering

1. Check SIP credentials in `.env`
2. Verify network connectivity to PBX
3. Check firewall allows UDP port 5060
4. View logs: `docker-compose logs -f`

### Transcription Failing

1. Verify Groq API key is valid
2. Check audio format (WAV, 16kHz recommended)
3. Ensure network access to api.groq.com

### TTS Not Working

1. Verify TTS API key is configured
2. Check TTS service is running
3. Test endpoint: `POST /api/test/tts`

## License

MIT License - See LICENSE file for details.

