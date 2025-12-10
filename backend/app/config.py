"""Configuration management for SIP AI Bridge."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Application configuration."""
    
    # Groq API (for speech-to-text)
    GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
    GROQ_API_URL: str = 'https://api.groq.com/openai/v1/audio/transcriptions'
    GROQ_MODEL: str = os.getenv('GROQ_MODEL', 'whisper-large-v3')
    # Groq LLM (for text generation fallback)
    GROQ_LLM_MODEL: str = os.getenv('GROQ_LLM_MODEL', 'llama-3.1-8b-instant')
    
    # SIP Configuration
    SIP_HOST: str = os.getenv('SIP_HOST', '10.0.0.87')
    SIP_PORT: int = int(os.getenv('SIP_PORT', '5060'))
    SIP_USERNAME: str = os.getenv('SIP_USERNAME', 'mumble-bridge')
    SIP_PASSWORD: str = os.getenv('SIP_PASSWORD', 'bridge123')
    SIP_EXTENSION: str = os.getenv('SIP_EXTENSION', '5000')
    
    # Ollama (local LLM)
    # Use host.docker.internal to access host's Ollama from Docker
    OLLAMA_URL: str = os.getenv('OLLAMA_URL', 'http://host.docker.internal:11434')
    OLLAMA_MODEL: str = os.getenv('OLLAMA_MODEL', 'llama3.1')
    
    # TTS Service (openai-edge-tts)
    TTS_URL: str = os.getenv('TTS_URL', 'http://10.0.0.59:5050')
    TTS_API_KEY: str = os.getenv('TTS_API_KEY', '')
    TTS_VOICE: str = os.getenv('TTS_VOICE', 'en-US-GuyNeural')
    
    # Web Interface
    WEB_PORT: int = int(os.getenv('WEB_PORT', '3002'))
    API_PORT: int = int(os.getenv('API_PORT', '5001'))
    
    # Database
    DATA_DIR: Path = Path(__file__).parent.parent.parent / 'data'
    DATABASE_PATH: Path = DATA_DIR / 'bridge.db'
    
    # Audio settings
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1
    AUDIO_FORMAT: str = 'wav'
    
    # Timezone
    TIMEZONE: str = os.getenv('TIMEZONE', 'UTC')

    # Bot Persona
    BOT_PERSONA: str = os.getenv('BOT_PERSONA', 'You are a friendly AI assistant on a phone call. Keep your responses short, conversational, and to the point. Avoid long explanations, lists, or formatting. Speak naturally, as if you are talking to a friend on the phone.')

    # Calendar Integration
    CALENDAR_URL: str = os.getenv('CALENDAR_URL', '')

    # Email Integration (IMAP)
    EMAIL_ADDRESS: str = os.getenv('EMAIL_ADDRESS', '')
    EMAIL_APP_PASSWORD: str = os.getenv('EMAIL_APP_PASSWORD', '')
    EMAIL_IMAP_SERVER: str = os.getenv('EMAIL_IMAP_SERVER', 'imap.gmail.com')
    EMAIL_IMAP_PORT: int = int(os.getenv('EMAIL_IMAP_PORT', '993'))

    # OpenWeatherMap API
    OPENWEATHER_API_KEY: str = os.getenv('OPENWEATHER_API_KEY', '')

    # TomTom API
    TOMTOM_API_KEY: str = os.getenv('TOMTOM_API_KEY', '')

    @classmethod
    def ensure_data_dir(cls) -> None:
        """Ensure data directory exists."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def to_dict(cls) -> dict:
        """Return configuration as dictionary."""
        return {
            'sip_host': cls.SIP_HOST,
            'sip_port': cls.SIP_PORT,
            'sip_username': cls.SIP_USERNAME,
            'sip_extension': cls.SIP_EXTENSION,
            'ollama_url': cls.OLLAMA_URL,
            'ollama_model': cls.OLLAMA_MODEL,
            'tts_url': cls.TTS_URL,
            'tts_api_key': cls.TTS_API_KEY,
            'tts_voice': cls.TTS_VOICE,
            'groq_api_key': cls.GROQ_API_KEY,
            'timezone': cls.TIMEZONE,
            'bot_persona': cls.BOT_PERSONA,
            'calendar_url': cls.CALENDAR_URL,
            'email_address': cls.EMAIL_ADDRESS,
            'email_imap_server': cls.EMAIL_IMAP_SERVER,
            'email_imap_port': cls.EMAIL_IMAP_PORT,
            'openweather_api_key': cls.OPENWEATHER_API_KEY,
            'tomtom_api_key': cls.TOMTOM_API_KEY,
            'web_port': cls.WEB_PORT,
            'api_port': cls.API_PORT,
            'has_groq_key': bool(cls.GROQ_API_KEY),
            'has_tts_key': bool(cls.TTS_API_KEY),
            'has_email_password': bool(cls.EMAIL_APP_PASSWORD),
            'has_weather_key': bool(cls.OPENWEATHER_API_KEY),
            'has_tomtom_key': bool(cls.TOMTOM_API_KEY),
        }
    
    @classmethod
    def update_from_dict(cls, data: dict) -> None:
        """Update configuration from dictionary."""
        if 'sip_host' in data:
            cls.SIP_HOST = data['sip_host']
        if 'sip_port' in data:
            cls.SIP_PORT = int(data['sip_port'])
        if 'sip_username' in data:
            cls.SIP_USERNAME = data['sip_username']
        if 'sip_password' in data:
            cls.SIP_PASSWORD = data['sip_password']
        if 'sip_extension' in data:
            cls.SIP_EXTENSION = data['sip_extension']
        if 'ollama_url' in data:
            cls.OLLAMA_URL = data['ollama_url']
        if 'ollama_model' in data:
            cls.OLLAMA_MODEL = data['ollama_model']
        if 'tts_url' in data:
            cls.TTS_URL = data['tts_url']
        if 'tts_api_key' in data:
            cls.TTS_API_KEY = data['tts_api_key']
        if 'tts_voice' in data:
            cls.TTS_VOICE = data['tts_voice']
        if 'groq_api_key' in data:
            cls.GROQ_API_KEY = data['groq_api_key']
        if 'timezone' in data:
            cls.TIMEZONE = data['timezone']
        if 'bot_persona' in data:
            cls.BOT_PERSONA = data['bot_persona']
        if 'calendar_url' in data:
            cls.CALENDAR_URL = data['calendar_url']
        if 'email_address' in data:
            cls.EMAIL_ADDRESS = data['email_address']
        if 'email_app_password' in data:
            cls.EMAIL_APP_PASSWORD = data['email_app_password']
        if 'email_imap_server' in data:
            cls.EMAIL_IMAP_SERVER = data['email_imap_server']
        if 'email_imap_port' in data:
            cls.EMAIL_IMAP_PORT = int(data['email_imap_port'])
        if 'openweather_api_key' in data:
            cls.OPENWEATHER_API_KEY = data['openweather_api_key']
        if 'tomtom_api_key' in data:
            cls.TOMTOM_API_KEY = data['tomtom_api_key']


# Initialize data directory
Config.ensure_data_dir()
