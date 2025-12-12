import gevent.monkey
gevent.monkey.patch_all()

# Force IPv4 to fix DNS timeouts (still helpful for gevent)
from . import patch_dns
patch_dns.apply()

import os
import threading
import time
import logging
from pathlib import Path

# Configure logging BEFORE importing modules that use it
log_dir = Path(__file__).parent.parent.parent / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'sip_bridge.log')
    ]
)

# Reduce geventwebsocket logging noise during calls
logging.getLogger('geventwebsocket.handler').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Now import modules that use logging
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS

from .config import Config
from .database import db
from .websocket import ws_manager
from .transcription import transcriber
from .gpt_client import gpt_client
from .tts_client import tts_client
from .calendar_client import calendar_client
from .email_client import email_client

# Create Flask app
app = Flask(__name__, static_folder='../../frontend/dist', static_url_path='')
app.config['SECRET_KEY'] = os.urandom(24).hex()

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize SocketIO with gevent (better DNS handling than eventlet)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')
ws_manager.init_app(socketio)

# SIP client instance (will be initialized after import)
sip_client = None


def init_sip_client():
    """Initialize the SIP client in a separate thread."""
    global sip_client
    try:
        from .sip_client import SIPClient
        sip_client = SIPClient()
        sip_client.start()
        db.add_log('info', 'sip_initialized', 'SIP client started successfully')
        ws_manager.broadcast_sip_status(True, {'message': 'SIP client initialized'})
    except Exception as e:
        db.add_log('error', 'sip_init_failed', str(e))
        ws_manager.broadcast_sip_status(False, {'error': str(e)})


# =====================
# Static file serving
# =====================

@app.route('/api/recordings/<path:filename>')
def serve_recordings(filename):
    """Serve call recordings."""
    recordings_dir = os.path.join(os.getcwd(), 'data', 'recordings')
    return send_from_directory(recordings_dir, filename)


@app.route('/')
def serve_frontend():
    """Serve the React frontend."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


# =====================
# Health & Status APIs
# =====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    # Check calendar health only if URL is configured
    # Don't fail health check if calendar has issues (optional service)
    calendar_healthy = 'not_configured'
    if Config.CALENDAR_URL:
        calendar_client.set_calendar_url(Config.CALENDAR_URL)
        try:
            # Quick check with timeout protection
            calendar_healthy = calendar_client.check_health()
        except Exception as e:
            logger.warning(f"Calendar health check failed: {e}")
            calendar_healthy = False

    services = {
        'api': True,
        'database': True,
        'groq': transcriber.check_health(),
        'ollama': gpt_client.check_health(),
        'tts': tts_client.check_health(),
        'sip': sip_client.is_registered if sip_client else False,
        'calendar': calendar_healthy,
    }

    # Don't count calendar as critical for overall health
    critical_services = {k: v for k, v in services.items() if k != 'calendar'}
    all_healthy = all(v is True or v == 'not_configured' for v in critical_services.values())

    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'services': services,
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current bridge status."""
    return jsonify({
        'sip_registered': sip_client.is_registered if sip_client else False,
        'active_call': sip_client.current_call_id if sip_client else None,
        'config': Config.to_dict(),
    })


# =====================
# Configuration APIs
# =====================

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration (excluding sensitive data)."""
    # Get the base config
    config = Config.to_dict()
    
    # Override with any database-saved values to ensure we return the most up-to-date settings
    saved_settings = db.get_all_settings()
    config_settings = {k.replace('config_', ''): v for k, v in saved_settings.items() if k.startswith('config_')}
    if config_settings:
        config.update(config_settings)
    
    return jsonify(config)


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    Config.update_from_dict(data)
    
    # Save to database for persistence
    for key, value in data.items():
        db.set_setting(f'config_{key}', value)
    
    db.add_log('info', 'config_updated', f'Configuration updated: {list(data.keys())}')
    
    # Restart SIP client if SIP settings changed
    sip_keys = ['sip_host', 'sip_port', 'sip_username', 'sip_password', 'sip_extension']
    if any(key in data for key in sip_keys):
        if sip_client:
            sip_client.restart()
    
    return jsonify({'status': 'updated', 'config': Config.to_dict()})


@app.route('/api/voices', methods=['GET'])
def get_voices():
    """Get available TTS voices."""
    return jsonify({'voices': tts_client.get_available_voices()})


# =====================
# Calendar APIs
# =====================

@app.route('/api/calendar/test', methods=['GET'])
def test_calendar():
    """Test calendar connection and fetch events."""
    if not Config.CALENDAR_URL:
        return jsonify({'error': 'No calendar URL configured'}), 400

    # Update calendar client URL
    calendar_client.set_calendar_url(Config.CALENDAR_URL)

    # Fetch events
    events, error = calendar_client.fetch_calendar()

    if error:
        return jsonify({'error': error}), 500

    # Get upcoming events (next 30 days)
    upcoming_events = calendar_client.get_upcoming_events(days=30, limit=20, user_timezone=Config.TIMEZONE)

    return jsonify({
        'status': 'success',
        'total_events': len(events) if events else 0,
        'upcoming_events': [event.to_dict() for event in upcoming_events],
    })


@app.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    """Get calendar events."""
    if not Config.CALENDAR_URL:
        return jsonify({'error': 'No calendar URL configured'}), 400

    # Get query parameters
    days = request.args.get('days', 30, type=int)
    limit = request.args.get('limit', 50, type=int)

    # Update calendar client URL
    calendar_client.set_calendar_url(Config.CALENDAR_URL)

    # Get upcoming events
    upcoming_events = calendar_client.get_upcoming_events(days=days, limit=limit, user_timezone=Config.TIMEZONE)

    return jsonify({
        'events': [event.to_dict() for event in upcoming_events],
        'count': len(upcoming_events),
    })


# =====================
# Email APIs
# =====================

@app.route('/api/email/test', methods=['GET'])
def test_email():
    """Test email connection and fetch unread emails."""
    if not Config.EMAIL_ADDRESS or not Config.EMAIL_APP_PASSWORD:
        return jsonify({'error': 'Email credentials not configured'}), 400

    # Update email client credentials
    email_client.set_credentials(
        Config.EMAIL_ADDRESS,
        Config.EMAIL_APP_PASSWORD,
        Config.EMAIL_IMAP_SERVER,
        Config.EMAIL_IMAP_PORT
    )

    # Fetch unread emails
    emails, error = email_client.fetch_unread_emails(limit=3)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'status': 'success',
        'count': len(emails) if emails else 0,
        'emails': [email.to_dict() for email in emails] if emails else [],
    })


@app.route('/api/email/unread', methods=['GET'])
def get_unread_emails():
    """Get unread emails."""
    if not Config.EMAIL_ADDRESS or not Config.EMAIL_APP_PASSWORD:
        return jsonify({'error': 'Email credentials not configured'}), 400

    # Get query parameters
    limit = request.args.get('limit', 3, type=int)

    # Update email client credentials
    email_client.set_credentials(
        Config.EMAIL_ADDRESS,
        Config.EMAIL_APP_PASSWORD,
        Config.EMAIL_IMAP_SERVER,
        Config.EMAIL_IMAP_PORT
    )

    # Fetch unread emails
    emails, error = email_client.fetch_unread_emails(limit=limit)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'emails': [email.to_dict() for email in emails] if emails else [],
        'count': len(emails) if emails else 0,
    })


# =====================
# Ollama Model APIs
# =====================

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available Ollama models."""
    models = gpt_client.get_available_models()
    current_model = Config.OLLAMA_MODEL
    return jsonify({
        'models': models,
        'current_model': current_model,
    })


@app.route('/api/models/pull', methods=['POST'])
def pull_model():
    """Pull a model from Ollama library."""
    data = request.get_json()
    if not data or 'model' not in data:
        return jsonify({'error': 'No model name provided'}), 400
    
    model_name = data['model']
    success, error = gpt_client.pull_model(model_name)
    
    if success:
        return jsonify({'status': 'success', 'model': model_name})
    else:
        return jsonify({'error': error}), 500


@app.route('/api/models/select', methods=['POST'])
def select_model():
    """Select which model to use for responses."""
    data = request.get_json()
    if not data or 'model' not in data:
        return jsonify({'error': 'No model name provided'}), 400
    
    model_name = data['model']
    Config.OLLAMA_MODEL = model_name
    
    # Save to database for persistence
    db.set_setting('config_ollama_model', model_name)
    db.add_log('info', 'model_changed', f'Model changed to: {model_name}')
    
    return jsonify({'status': 'success', 'model': model_name})


# =====================
# Conversation APIs
# =====================

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get conversation history."""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Get active call IDs from SIP client
    active_call_ids = []
    if sip_client and hasattr(sip_client, '_active_sessions'):
        active_call_ids = [call_id for call_id, session in sip_client._active_sessions.items() 
                          if session.active and session.call_state]
    
    conversations = db.get_conversations(limit=limit, offset=offset, active_call_ids=active_call_ids)
    return jsonify({
        'conversations': [c.to_dict() for c in conversations],
        'limit': limit,
        'offset': offset,
    })


@app.route('/api/conversations/<call_id>', methods=['GET'])
def get_conversation(call_id):
    """Get a specific conversation by call ID."""
    conv = db.get_conversation_by_call_id(call_id)
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404

    # Get messages with calendar/email references
    messages = db.get_messages_with_refs(conv.id)
    return jsonify({
        'conversation': conv.to_dict(),
        'messages': messages,
    })


@app.route('/api/messages', methods=['GET'])
def get_recent_messages():
    """Get recent messages across all conversations."""
    limit = request.args.get('limit', 100, type=int)
    messages = db.get_recent_messages(limit=limit)
    return jsonify({'messages': messages})


@app.route('/api/messages/<int:message_id>', methods=['GET'])
def get_message_with_refs(message_id):
    """Get a specific message with its calendar and email references."""
    message = db.get_message_with_refs(message_id)
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    return jsonify(message)


@app.route('/api/calendar/events/<int:event_id>', methods=['GET'])
def get_calendar_event(event_id):
    """Get full calendar event details by ID."""
    event = db.get_calendar_event(event_id)
    if not event:
        return jsonify({'error': 'Calendar event not found'}), 404
    return jsonify(event)


@app.route('/api/emails/<int:email_id>', methods=['GET'])
def get_email_message(email_id):
    """Get full email message details by ID."""
    email = db.get_email_message(email_id)
    if not email:
        return jsonify({'error': 'Email not found'}), 404
    return jsonify(email)


# =====================
# Notes API
# =====================

@app.route('/api/notes', methods=['GET'])
def get_all_notes():
    """Get all notes."""
    notes = db.get_all_notes()
    return jsonify({'notes': notes})


@app.route('/api/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a note by ID."""
    note = db.get_note(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    return jsonify(note)


@app.route('/api/notes', methods=['POST'])
def create_note():
    """Create a new note."""
    data = request.get_json()

    if not data or 'title' not in data or 'transcript' not in data:
        return jsonify({'error': 'Missing required fields: title, transcript'}), 400

    note_id = db.create_note(
        title=data['title'],
        transcript=data['transcript'],
        summary=data.get('summary'),
        call_id=data.get('call_id')
    )

    note = db.get_note(note_id)
    return jsonify(note), 201


@app.route('/api/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a note."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    success = db.update_note(
        note_id=note_id,
        title=data.get('title'),
        summary=data.get('summary'),
        transcript=data.get('transcript')
    )

    if not success:
        return jsonify({'error': 'Note not found'}), 404

    note = db.get_note(note_id)
    return jsonify(note)


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a note."""
    success = db.delete_note(note_id)

    if not success:
        return jsonify({'error': 'Note not found'}), 404

    return jsonify({'success': True})


# =====================
# Logs API
# =====================

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get call logs."""
    limit = request.args.get('limit', 100, type=int)
    level = request.args.get('level')
    call_id = request.args.get('call_id')
    
    logs = db.get_logs(limit=limit, level=level, call_id=call_id)
    return jsonify({'logs': [l.to_dict() for l in logs]})


# =====================
# Manual Test APIs
# =====================

@app.route('/api/test/transcribe', methods=['POST'])
def test_transcribe():
    """Test transcription with uploaded audio."""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    audio_data = audio_file.read()
    
    text, error = transcriber.transcribe_sync(audio_data)
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({'transcription': text})


@app.route('/api/test/ollama', methods=['POST'])
def test_ollama():
    """Test Ollama with text input."""
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    response, error, model = gpt_client.get_response_sync(data['text'])
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'response': response,
        'model': model,
    })


@app.route('/api/test/tts', methods=['POST'])
def test_tts():
    """Test TTS with text input."""
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    voice = data.get('voice')
    audio, error = tts_client.synthesize_sync(data['text'], voice=voice)
    if error:
        return jsonify({'error': error}), 500

    # Return audio as base64 for testing
    import base64
    return jsonify({
        'audio': base64.b64encode(audio).decode('utf-8'),
        'format': 'mp3',
    })


@app.route('/api/preview/voice', methods=['POST'])
def preview_voice():
    """Preview a TTS voice."""
    data = request.get_json()
    if not data or 'voice' not in data:
        return jsonify({'error': 'No voice provided'}), 400

    voice = data['voice']
    preview_text = "Hello! This is a preview of how I sound. I hope you like my voice!"

    audio, error = tts_client.synthesize_sync(preview_text, voice=voice)
    if error:
        return jsonify({'error': error}), 500

    # Return raw audio for browser playback
    from flask import Response
    return Response(audio, mimetype='audio/mpeg')


@app.route('/api/generate/persona', methods=['POST'])
def generate_persona():
    """Generate an enhanced bot persona using AI."""
    data = request.get_json()
    if not data or 'draft' not in data:
        return jsonify({'error': 'No draft persona provided'}), 400

    draft = data['draft']

    # Use Ollama to expand and enhance the persona
    prompt = f"""You are an AI assistant helping to create a detailed bot persona for a voice AI assistant.

The user has provided this draft persona:
{draft}

Please expand this into a comprehensive, detailed persona that includes:
- Personality traits and communication style
- Tone and manner of speaking
- Areas of expertise or focus
- How they should respond to questions
- Any specific behaviors or characteristics

Keep it concise but detailed (2-3 paragraphs max). Write in second person ("You are...").

Enhanced persona:"""

    response, error, _ = gpt_client.get_response_sync(prompt)
    if error or not response:
        return jsonify({'error': 'Failed to generate persona'}), 500

    return jsonify({'persona': response})


# =====================
# SIP Control APIs
# =====================

@app.route('/api/sip/restart', methods=['POST'])
def restart_sip():
    """Restart the SIP client."""
    if sip_client:
        sip_client.restart()
        return jsonify({'status': 'restarting'})
    else:
        threading.Thread(target=init_sip_client, daemon=True).start()
        return jsonify({'status': 'starting'})


@app.route('/api/sip/hangup', methods=['POST'])
def hangup_call():
    """Hang up the current call."""
    if sip_client and sip_client.current_call_id:
        sip_client.hangup()
        return jsonify({'status': 'hanging up'})
    return jsonify({'error': 'No active call'}), 400


@app.route('/api/sip/simulate', methods=['POST'])
def simulate_call():
    """Simulate a call for testing purposes."""
    data = request.get_json() or {}
    caller_id = data.get('caller_id', 'test-caller')
    message = data.get('message', 'Hello, this is a test message.')
    
    if sip_client:
        result = sip_client.simulate_call(caller_id, message)
        return jsonify(result)
    return jsonify({'error': 'SIP client not initialized'}), 500


# =====================
# WebSocket Events
# =====================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    db.add_log('info', 'websocket_connected', 'Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    db.add_log('info', 'websocket_disconnected', 'Client disconnected')


# =====================
# Application Entry Point
# =====================

def update_active_conversations():
    """Periodically update durations for active conversations."""
    while True:
        try:
            time.sleep(2)  # Update every 2 seconds
            # Get active call IDs from SIP client
            active_call_ids = []
            if sip_client and hasattr(sip_client, '_active_sessions'):
                active_call_ids = [call_id for call_id, session in sip_client._active_sessions.items()
                                  if session.active and session.call_state]

            # Get conversations from database (this creates new conversation objects)
            with db.get_session() as session:
                from .database import Conversation as ConvModel
                conversations = session.query(ConvModel).filter_by(status='active').limit(100).all()

                for conv in conversations:
                    # Only update duration for truly active conversations
                    # Don't end them here - let BYE handler do that
                    if conv.call_id in active_call_ids:
                        # Update duration for active conversation
                        db.update_conversation_duration(conv.call_id)
                    else:
                        # Call may have ended but BYE not received yet
                        # Check if conversation has been active for too long without updates (stale)
                        if conv.started_at:
                            from datetime import datetime, timezone
                            started = datetime.fromisoformat(str(conv.started_at))
                            if started.tzinfo is None:
                                started = started.replace(tzinfo=timezone.utc)
                            age_minutes = (datetime.now(timezone.utc) - started).total_seconds() / 60

                            # Only auto-end if call has been active for > 10 minutes without being in active sessions
                            # This handles cases where BYE was never received
                            if age_minutes > 10:
                                logger.warning(f"Auto-ending stale conversation: {conv.call_id} (age: {age_minutes:.1f} minutes)")
                                db.add_message_by_call_id(conv.call_id, 'system', 'Call ended (timeout)')
                                db.end_conversation(conv.call_id)
        except Exception as e:
            logger.error(f"Error updating active conversations: {e}")


def main():
    """Main entry point."""
    # Ensure data directory exists
    Config.ensure_data_dir()
    
    # Load saved settings from database
    saved_settings = db.get_all_settings()
    config_settings = {k.replace('config_', ''): v for k, v in saved_settings.items() if k.startswith('config_')}
    if config_settings:
        Config.update_from_dict(config_settings)
    
    db.add_log('info', 'server_starting', f'Starting SIP AI Bridge on port {Config.API_PORT}')
    
    # Initialize SIP client in background
    threading.Thread(target=init_sip_client, daemon=True).start()
    
    # Start background thread to update active conversation durations
    threading.Thread(target=update_active_conversations, daemon=True).start()
    
    # Run the Flask app with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=Config.API_PORT,
        debug=False,
        use_reloader=False
    )


if __name__ == '__main__':
    main()

