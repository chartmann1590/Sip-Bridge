"""WebSocket manager for real-time updates."""
from typing import Dict, Any, Optional, Callable
from flask_socketio import SocketIO, emit
import json
from datetime import datetime


class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self, socketio: Optional[SocketIO] = None):
        self.socketio = socketio
        self._event_handlers: Dict[str, Callable] = {}
    
    def init_app(self, socketio: SocketIO) -> None:
        """Initialize with Flask-SocketIO instance."""
        self.socketio = socketio
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register WebSocket event handlers."""
        if not self.socketio:
            return
        
        @self.socketio.on('connect')
        def handle_connect():
            emit('connected', {'status': 'connected', 'timestamp': datetime.utcnow().isoformat()})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            pass
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Handle client subscription to specific events."""
            channel = data.get('channel', 'all')
            emit('subscribed', {'channel': channel})
    
    def broadcast_call_status(self, status: str, call_id: Optional[str] = None,
                              caller_id: Optional[str] = None, details: Optional[Dict] = None) -> None:
        """Broadcast call status update to all connected clients."""
        if self.socketio:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Broadcasting call status: {status} for call {call_id}")
            self.socketio.emit('call_status', {
                'status': status,
                'call_id': call_id,
                'caller_id': caller_id,
                'details': details or {},
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def broadcast_message(self, conversation_id: int, role: str, content: str,
                          call_id: Optional[str] = None,
                          calendar_refs: Optional[list] = None,
                          email_refs: Optional[list] = None,
                          weather_refs: Optional[list] = None,
                          tomtom_refs: Optional[list] = None,
                          model: Optional[str] = None) -> None:
        """Broadcast a new message to all connected clients."""
        if self.socketio:
            message_data = {
                'conversation_id': conversation_id,
                'role': role,
                'content': content,
                'call_id': call_id,
                'model': model,
                'timestamp': datetime.utcnow().isoformat()
            }

            # Include references if provided
            if calendar_refs:
                message_data['calendar_refs'] = calendar_refs
            if email_refs:
                message_data['email_refs'] = email_refs
            if weather_refs:
                message_data['weather_refs'] = weather_refs
            if tomtom_refs:
                message_data['tomtom_refs'] = tomtom_refs

            self.socketio.emit('new_message', message_data)
    
    def broadcast_conversation_update(self, conversation: Dict[str, Any]) -> None:
        """Broadcast conversation update (new conversation, status change, duration update)."""
        if self.socketio:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Broadcasting conversation_update: {conversation.get('call_id')}")
            self.socketio.emit('conversation_update', {
                'conversation': conversation,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def broadcast_health_status(self, services: Dict[str, bool]) -> None:
        """Broadcast health status of all services."""
        if self.socketio:
            self.socketio.emit('health_status', {
                'services': services,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def broadcast_log(self, level: str, event: str, details: Optional[str] = None,
                      call_id: Optional[str] = None) -> None:
        """Broadcast a log entry to all connected clients."""
        if self.socketio:
            self.socketio.emit('log_entry', {
                'level': level,
                'event': event,
                'details': details,
                'call_id': call_id,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def broadcast_transcription(self, call_id: str, text: str, is_final: bool = False) -> None:
        """Broadcast transcription update (for real-time display)."""
        if self.socketio:
            self.socketio.emit('transcription', {
                'call_id': call_id,
                'text': text,
                'is_final': is_final,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def broadcast_sip_status(self, registered: bool, details: Optional[Dict] = None) -> None:
        """Broadcast SIP registration status."""
        if self.socketio:
            self.socketio.emit('sip_status', {
                'registered': registered,
                'details': details or {},
                'timestamp': datetime.utcnow().isoformat()
            })


# Global WebSocket manager instance
ws_manager = WebSocketManager()
