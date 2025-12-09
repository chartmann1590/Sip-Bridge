"""SQLite database models and queries for SIP AI Bridge."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .config import Config
from .websocket import ws_manager

logger = logging.getLogger(__name__)

Base = declarative_base()


class Conversation(Base):
    """Model for storing conversation logs."""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(String(100), index=True)
    caller_id = Column(String(100))
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    answered_at = Column(DateTime, nullable=True)  # When call was answered (after welcome message)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    status = Column(String(50), default='active')  # active, completed, failed
    recording_path = Column(String(255), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        # Calculate duration based on answered_at to ended_at (or now for active)
        duration = self.duration_seconds
        if duration == 0 or duration is None:
            # Use answered_at if available, otherwise fall back to started_at
            start_time = self.answered_at if self.answered_at else self.started_at
            if start_time:
                # Ensure timezone-aware
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)

                if self.ended_at:
                    # Completed conversation: calculate from answered_at/started_at to ended_at
                    end_time = self.ended_at
                    if end_time.tzinfo is None:
                        end_time = end_time.replace(tzinfo=timezone.utc)
                    duration = (end_time - start_time).total_seconds()
                else:
                    # Active conversation: calculate from answered_at/started_at to now
                    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Helper to format datetime with timezone
        def format_dt(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                # Assume UTC if no timezone
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        # Construct recording URL if path exists
        recording_url = None
        if self.recording_path:
            filename = Path(self.recording_path).name
            recording_url = f"/recordings/{filename}"

        return {
            'id': self.id,
            'call_id': self.call_id,
            'caller_id': self.caller_id,
            'started_at': format_dt(self.started_at),
            'answered_at': format_dt(self.answered_at),
            'ended_at': format_dt(self.ended_at),
            'duration_seconds': duration,
            'status': self.status,
            'recording_url': recording_url,
        }


class Message(Base):
    """Model for storing individual messages in conversations."""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    role = Column(String(20))  # user, assistant, system
    content = Column(Text)
    model = Column(String(50), nullable=True)  # llama3.1, groan-whisper, etc.
    audio_duration = Column(Float, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        # Format timestamp with UTC timezone
        ts = None
        if self.timestamp:
            if self.timestamp.tzinfo is None:
                ts = self.timestamp.replace(tzinfo=timezone.utc).isoformat()
            else:
                ts = self.timestamp.isoformat()

        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'timestamp': ts,
            'role': self.role,
            'content': self.content,
            'model': self.model,
            'audio_duration': self.audio_duration,
        }


class Settings(Base):
    """Model for storing application settings."""
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CallLog(Base):
    """Model for detailed call logging."""
    __tablename__ = 'call_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(20))  # info, warning, error
    event = Column(String(100))
    details = Column(Text, nullable=True)
    call_id = Column(String(100), nullable=True, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'event': self.event,
            'details': self.details,
            'call_id': self.call_id,
        }


class CalendarEvent(Base):
    """Model for storing calendar events from iCalendar sources."""
    __tablename__ = 'calendar_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_uid = Column(String(255), unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    attendees = Column(Text, nullable=True)  # JSON string of attendee objects
    is_all_day = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        # Parse attendees JSON
        attendees_list = []
        if self.attendees:
            try:
                attendees_list = json.loads(self.attendees)
            except:
                pass

        return {
            'id': self.id,
            'event_uid': self.event_uid,
            'summary': self.summary,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'description': self.description,
            'location': self.location,
            'attendees': attendees_list,
            'is_all_day': self.is_all_day,
        }


class EmailMessage(Base):
    """Model for storing email messages fetched via IMAP."""
    __tablename__ = 'email_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(500), unique=True, nullable=False, index=True)
    subject = Column(Text, nullable=False)
    sender = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)  # TTL for cleanup (24 hours)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'message_id': self.message_id,
            'subject': self.subject,
            'sender': self.sender,
            'date': self.date.isoformat() if self.date else None,
            'body': self.body,
        }


class MessageCalendarRef(Base):
    """Model for linking messages to calendar events."""
    __tablename__ = 'message_calendar_refs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, nullable=False, index=True)
    calendar_event_id = Column(Integer, nullable=False, index=True)
    ref_index = Column(Integer, nullable=False)  # Position in message (0, 1, 2...)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MessageEmailRef(Base):
    """Model for linking messages to email messages."""
    __tablename__ = 'message_email_refs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, nullable=False, index=True)
    email_message_id = Column(Integer, nullable=False, index=True)
    ref_index = Column(Integer, nullable=False)  # Position in message (0, 1, 2...)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Database:
    """Database manager for SIP AI Bridge."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        self._migrate_answered_at_column()
        self._migrate_recording_path_column()
        self._migrate_calendar_events_table()
        self._migrate_email_messages_table()
        self._migrate_calendar_events_table()
        self._migrate_email_messages_table()
        self._migrate_message_refs_tables()
        self._migrate_message_model_column()
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def _migrate_answered_at_column(self) -> None:
        """Add answered_at column to existing conversations table if it doesn't exist."""
        try:
            with self.engine.connect() as conn:
                # Check if column exists
                result = conn.execute(text("PRAGMA table_info(conversations)"))
                columns = [row[1] for row in result]
                if 'answered_at' not in columns:
                    # Add the column
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN answered_at DATETIME"))
                    conn.commit()
                    logger.info("Added answered_at column to conversations table")
        except Exception as e:
            # If migration fails, log but don't crash
            logger.warning(f"Could not migrate answered_at column: {e}")

    def _migrate_recording_path_column(self) -> None:
        """Add recording_path column to existing conversations table if it doesn't exist."""
        try:
            with self.engine.connect() as conn:
                # Check if column exists
                result = conn.execute(text("PRAGMA table_info(conversations)"))
                columns = [row[1] for row in result]
                if 'recording_path' not in columns:
                    # Add the column
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN recording_path VARCHAR(255)"))
                    conn.commit()
                    logger.info("Added recording_path column to conversations table")
        except Exception as e:
            # If migration fails, log but don't crash
            logger.warning(f"Could not migrate recording_path column: {e}")

    def _migrate_calendar_events_table(self) -> None:
        """Ensure calendar_events table exists with all columns."""
        try:
            with self.engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='calendar_events'"))
                if not result.fetchone():
                    logger.info("calendar_events table will be created by SQLAlchemy")
        except Exception as e:
            logger.warning(f"Could not check calendar_events table: {e}")

    def _migrate_email_messages_table(self) -> None:
        """Ensure email_messages table exists with all columns."""
        try:
            with self.engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='email_messages'"))
                if not result.fetchone():
                    logger.info("email_messages table will be created by SQLAlchemy")
                else:
                    # Check if expires_at column exists (added for TTL)
                    result = conn.execute(text("PRAGMA table_info(email_messages)"))
                    columns = [row[1] for row in result]
                    if 'expires_at' not in columns:
                        conn.execute(text("ALTER TABLE email_messages ADD COLUMN expires_at DATETIME"))
                        conn.commit()
                        logger.info("Added expires_at column to email_messages table")
        except Exception as e:
            logger.warning(f"Could not migrate email_messages table: {e}")

    def _migrate_message_refs_tables(self) -> None:
        """Ensure message reference tables exist."""
        try:
            with self.engine.connect() as conn:
                # Check if tables exist
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='message_calendar_refs'"))
                if not result.fetchone():
                    logger.info("message_calendar_refs table will be created by SQLAlchemy")

                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='message_email_refs'"))
                if not result.fetchone():
                    logger.info("message_email_refs table will be created by SQLAlchemy")
        except Exception as e:
            logger.warning(f"Could not check message reference tables: {e}")

    def _migrate_message_model_column(self) -> None:
        """Add model column to existing messages table if it doesn't exist."""
        try:
            with self.engine.connect() as conn:
                # Check if column exists
                result = conn.execute(text("PRAGMA table_info(messages)"))
                columns = [row[1] for row in result]
                if 'model' not in columns:
                    # Add the column
                    conn.execute(text("ALTER TABLE messages ADD COLUMN model VARCHAR(50)"))
                    conn.commit()
                    logger.info("Added model column to messages table")
        except Exception as e:
            # If migration fails, log but don't crash
            logger.warning(f"Could not migrate model column: {e}")
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    # Conversation methods
    def create_conversation(self, call_id: str, caller_id: str) -> Conversation:
        """Create a new conversation."""
        with self.get_session() as session:
            conv = Conversation(call_id=call_id, caller_id=caller_id)
            session.add(conv)
            session.commit()
            session.refresh(conv)
            # Add system message for call started
            if conv.id:
                msg = self.add_message(conv.id, 'system', 'Call started')
                # Broadcast system message via WebSocket
                if msg:
                    ws_manager.broadcast_message(conv.id, 'system', 'Call started', call_id)
            # Broadcast new conversation
            ws_manager.broadcast_conversation_update(conv.to_dict())
            return conv
    
    def mark_call_answered(self, call_id: str) -> Optional[Conversation]:
        """Mark a call as answered (after welcome message finishes)."""
        with self.get_session() as session:
            conv = session.query(Conversation).filter_by(call_id=call_id).first()
            if conv and not conv.answered_at:
                conv.answered_at = datetime.utcnow()
                session.commit()
                session.refresh(conv)
                # Add system message for call answered
                if conv.id:
                    msg = self.add_message(conv.id, 'system', 'Call answered')
                    # Broadcast system message via WebSocket
                    if msg:
                        ws_manager.broadcast_message(conv.id, 'system', 'Call answered', call_id)
                # Broadcast conversation update
                ws_manager.broadcast_conversation_update(conv.to_dict())
            return conv
    
    def end_conversation(self, call_id: str) -> Optional[Conversation]:
        """End a conversation and calculate duration."""
        with self.get_session() as session:
            conv = session.query(Conversation).filter_by(call_id=call_id).first()
            if conv:
                conv.ended_at = datetime.utcnow()
                conv.status = 'completed'
                # Calculate duration from answered_at if available, otherwise started_at
                start_time = conv.answered_at if conv.answered_at else conv.started_at
                if start_time:
                    conv.duration_seconds = (conv.ended_at - start_time).total_seconds()
                # Add system message for user hung up
                if conv.id:
                    msg = self.add_message(conv.id, 'system', 'User hung up')
                    # Broadcast system message via WebSocket
                    if msg:
                        ws_manager.broadcast_message(conv.id, 'system', 'User hung up', call_id)
                session.commit()
                session.refresh(conv)
                # Broadcast conversation update
                ws_manager.broadcast_conversation_update(conv.to_dict())
            return conv
    
    def update_conversation_duration(self, call_id: str) -> Optional[Conversation]:
        """Update duration for an active conversation."""
        with self.get_session() as session:
            conv = session.query(Conversation).filter_by(call_id=call_id).first()
            if conv and not conv.ended_at:
                # Use answered_at if available, otherwise started_at
                start_time = conv.answered_at if conv.answered_at else conv.started_at
                if start_time:
                    now = datetime.utcnow()
                    conv.duration_seconds = (now - start_time).total_seconds()
                    session.commit()
                    session.refresh(conv)
                    # Broadcast duration update
                    ws_manager.broadcast_conversation_update(conv.to_dict())
            return conv
    
    def get_conversations(self, limit: int = 50, offset: int = 0, active_call_ids: Optional[List[str]] = None) -> List[Conversation]:
        """Get recent conversations."""
        with self.get_session() as session:
            conversations = session.query(Conversation)\
                .order_by(Conversation.started_at.desc())\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            # Fix status and durations for conversations
            now = datetime.utcnow()
            active_ids = set(active_call_ids) if active_call_ids else set()
            
            for conv in conversations:
                # If conversation has ended_at, it should be marked as completed
                if conv.ended_at and conv.status != 'completed':
                    conv.status = 'completed'
                    session.commit()
                    session.refresh(conv)
                
                # If conversation is marked as active but has ended_at, fix status
                if conv.status == 'active' and conv.ended_at:
                    conv.status = 'completed'
                    session.commit()
                    session.refresh(conv)
                
                # If conversation is marked as active but is NOT in active sessions, mark as completed
                if conv.status == 'active' and conv.call_id not in active_ids:
                    # Check if conversation is old (started more than 5 minutes ago)
                    if conv.started_at:
                        time_since_start = (now - conv.started_at).total_seconds()
                        if time_since_start > 300:  # 5 minutes
                            if not conv.ended_at:
                                # Use answered_at if available, otherwise started_at + calculated duration
                                if conv.answered_at:
                                    # Calculate end time based on current duration if it exists
                                    if conv.duration_seconds and conv.duration_seconds > 0:
                                        from datetime import timedelta
                                        conv.ended_at = conv.answered_at + timedelta(seconds=conv.duration_seconds)
                                    else:
                                        # Use answered_at + 1 minute as default
                                        from datetime import timedelta
                                        conv.ended_at = conv.answered_at + timedelta(seconds=60)
                                else:
                                    # No answered_at, use started_at + duration or default
                                    if conv.duration_seconds and conv.duration_seconds > 0:
                                        from datetime import timedelta
                                        conv.ended_at = conv.started_at + timedelta(seconds=conv.duration_seconds)
                                    else:
                                        # Use started_at + 1 minute as default
                                        from datetime import timedelta
                                        conv.ended_at = conv.started_at + timedelta(seconds=60)
                            conv.status = 'completed'
                            session.commit()
                            session.refresh(conv)
                
                # Fix durations for completed conversations that have 0 duration
                if conv.status == 'completed' and conv.ended_at:
                    if conv.duration_seconds == 0 or conv.duration_seconds is None:
                        # Use answered_at if available, otherwise started_at
                        start_time = conv.answered_at if conv.answered_at else conv.started_at
                        if start_time and conv.ended_at:
                            conv.duration_seconds = (conv.ended_at - start_time).total_seconds()
                            # Ensure duration is at least 0
                            if conv.duration_seconds < 0:
                                conv.duration_seconds = 0
                            session.commit()
            
            return conversations
    
    def get_conversation_by_call_id(self, call_id: str) -> Optional[Conversation]:
        """Get conversation by call ID."""
        with self.get_session() as session:
            return session.query(Conversation).filter_by(call_id=call_id).first()
    
    # Message methods
    def add_message(self, conversation_id: int, role: str, content: str,
                    audio_duration: Optional[float] = None, model: Optional[str] = None) -> Message:
        """Add a message to a conversation."""
        with self.get_session() as session:
            msg = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                audio_duration=audio_duration,
                model=model
            )
            session.add(msg)
            session.commit()
            session.refresh(msg)
            # Also update conversation duration if active
            conv = session.query(Conversation).filter_by(id=conversation_id).first()
            if conv and conv.status == 'active':
                self.update_conversation_duration(conv.call_id)
            return msg

    def add_message_by_call_id(self, call_id: str, role: str, content: str,
                                audio_duration: Optional[float] = None, model: Optional[str] = None) -> Optional[Message]:
        """Add a message to a conversation by call_id."""
        with self.get_session() as session:
            conv = session.query(Conversation).filter_by(call_id=call_id).first()
            if not conv:
                return None

            msg = Message(
                conversation_id=conv.id,
                role=role,
                content=content,
                audio_duration=audio_duration,
                model=model
            )
            session.add(msg)
            session.commit()
            session.refresh(msg)
            return msg
    
    def get_messages(self, conversation_id: int) -> List[Message]:
        """Get all messages for a conversation."""
        with self.get_session() as session:
            return session.query(Message)\
                .filter_by(conversation_id=conversation_id)\
                .order_by(Message.timestamp.asc())\
                .all()
    
    def get_recent_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent messages across all conversations."""
        with self.get_session() as session:
            messages = session.query(Message)\
                .order_by(Message.timestamp.desc())\
                .limit(limit)\
                .all()
            return [m.to_dict() for m in messages]
    
    # Settings methods
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        with self.get_session() as session:
            setting = session.query(Settings).filter_by(key=key).first()
            if setting:
                try:
                    return json.loads(setting.value)
                except json.JSONDecodeError:
                    return setting.value
            return default
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value."""
        with self.get_session() as session:
            setting = session.query(Settings).filter_by(key=key).first()
            value_str = json.dumps(value) if not isinstance(value, str) else value
            if setting:
                setting.value = value_str
            else:
                setting = Settings(key=key, value=value_str)
                session.add(setting)
            session.commit()
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        with self.get_session() as session:
            settings = session.query(Settings).all()
            result = {}
            for s in settings:
                try:
                    result[s.key] = json.loads(s.value)
                except json.JSONDecodeError:
                    result[s.key] = s.value
            return result
    
    # Call log methods
    def add_log(self, level: str, event: str, details: Optional[str] = None,
                call_id: Optional[str] = None) -> CallLog:
        """Add a call log entry."""
        with self.get_session() as session:
            log = CallLog(level=level, event=event, details=details, call_id=call_id)
            session.add(log)
            session.commit()
            session.refresh(log)
            return log
    
    def get_logs(self, limit: int = 100, level: Optional[str] = None,
                 call_id: Optional[str] = None) -> List[CallLog]:
        """Get call logs with optional filtering."""
        with self.get_session() as session:
            query = session.query(CallLog)
            if level:
                query = query.filter_by(level=level)
            if call_id:
                query = query.filter_by(call_id=call_id)
            return query.order_by(CallLog.timestamp.desc()).limit(limit).all()

    # Calendar event methods
    def store_calendar_event(self, event_uid: str, summary: str, start_time: datetime,
                            end_time: datetime, description: Optional[str] = None,
                            location: Optional[str] = None, attendees: Optional[List[Dict]] = None,
                            is_all_day: bool = False) -> int:
        """Store or update a calendar event. Returns event ID."""
        with self.get_session() as session:
            # Check if event already exists by UID
            existing = session.query(CalendarEvent).filter_by(event_uid=event_uid).first()

            attendees_json = json.dumps(attendees) if attendees else None

            if existing:
                # Update existing event
                existing.summary = summary
                existing.start_time = start_time
                existing.end_time = end_time
                existing.description = description
                existing.location = location
                existing.attendees = attendees_json
                existing.is_all_day = is_all_day
                existing.updated_at = datetime.now(timezone.utc)
                session.commit()
                return existing.id
            else:
                # Create new event
                event = CalendarEvent(
                    event_uid=event_uid,
                    summary=summary,
                    start_time=start_time,
                    end_time=end_time,
                    description=description,
                    location=location,
                    attendees=attendees_json,
                    is_all_day=is_all_day
                )
                session.add(event)
                session.commit()
                session.refresh(event)
                return event.id

    def get_calendar_event(self, event_id: int) -> Optional[CalendarEvent]:
        """Get a calendar event by ID."""
        with self.get_session() as session:
            return session.query(CalendarEvent).filter_by(id=event_id).first()

    # Email message methods
    def store_email_message(self, message_id: str, subject: str, sender: str,
                           date: datetime, body: str) -> int:
        """Store an email message with 24-hour TTL. Returns email ID."""
        with self.get_session() as session:
            # Check if email already exists
            existing = session.query(EmailMessage).filter_by(message_id=message_id).first()

            if existing:
                return existing.id

            # Create new email with 24-hour expiry
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            email = EmailMessage(
                message_id=message_id,
                subject=subject,
                sender=sender,
                date=date,
                body=body,
                expires_at=expires_at
            )
            session.add(email)
            session.commit()
            session.refresh(email)
            return email.id

    def get_email_message(self, email_id: int) -> Optional[EmailMessage]:
        """Get an email message by ID."""
        with self.get_session() as session:
            return session.query(EmailMessage).filter_by(id=email_id).first()

    def cleanup_expired_emails(self) -> int:
        """Delete expired emails. Returns number of emails deleted."""
        with self.get_session() as session:
            now = datetime.now(timezone.utc)
            expired = session.query(EmailMessage).filter(EmailMessage.expires_at < now).all()
            count = len(expired)
            for email in expired:
                session.delete(email)
            session.commit()
            return count

    # Message reference methods
    def add_calendar_ref(self, message_id: int, calendar_event_id: int, ref_index: int) -> None:
        """Link a message to a calendar event."""
        with self.get_session() as session:
            # Check if reference already exists
            existing = session.query(MessageCalendarRef)\
                .filter_by(message_id=message_id, ref_index=ref_index)\
                .first()

            if not existing:
                ref = MessageCalendarRef(
                    message_id=message_id,
                    calendar_event_id=calendar_event_id,
                    ref_index=ref_index
                )
                session.add(ref)
                session.commit()

    def add_email_ref(self, message_id: int, email_message_id: int, ref_index: int) -> None:
        """Link a message to an email."""
        with self.get_session() as session:
            # Check if reference already exists
            existing = session.query(MessageEmailRef)\
                .filter_by(message_id=message_id, ref_index=ref_index)\
                .first()

            if not existing:
                ref = MessageEmailRef(
                    message_id=message_id,
                    email_message_id=email_message_id,
                    ref_index=ref_index
                )
                session.add(ref)
                session.commit()

    def get_message_with_refs(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Get a message with all its calendar and email references populated."""
        with self.get_session() as session:
            message = session.query(Message).filter_by(id=message_id).first()
            if not message:
                return None

            # Get calendar references
            calendar_refs = []
            cal_refs = session.query(MessageCalendarRef)\
                .filter_by(message_id=message_id)\
                .order_by(MessageCalendarRef.ref_index)\
                .all()

            for ref in cal_refs:
                event = session.query(CalendarEvent).filter_by(id=ref.calendar_event_id).first()
                if event:
                    calendar_refs.append({
                        'ref_index': ref.ref_index,
                        'event': event.to_dict()
                    })

            # Get email references
            email_refs = []
            em_refs = session.query(MessageEmailRef)\
                .filter_by(message_id=message_id)\
                .order_by(MessageEmailRef.ref_index)\
                .all()

            for ref in em_refs:
                email = session.query(EmailMessage).filter_by(id=ref.email_message_id).first()
                if email:
                    email_refs.append({
                        'ref_index': ref.ref_index,
                        'email': email.to_dict()
                    })

            # Build complete message dict
            result = message.to_dict()
            result['calendar_refs'] = calendar_refs
            result['email_refs'] = email_refs

            return result

    def get_messages_with_refs(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Get all messages for a conversation with references populated."""
        messages = self.get_messages(conversation_id)
        result = []
        for msg in messages:
            msg_with_refs = self.get_message_with_refs(msg.id)
            if msg_with_refs:
                result.append(msg_with_refs)
        return result

    def get_calendar_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get calendar event by ID."""
        with self.Session() as session:
            event = session.query(CalendarEvent).filter_by(id=event_id).first()
            if not event:
                return None

            return {
                'id': event.id,
                'event_uid': event.event_uid,
                'summary': event.summary,
                'start_time': event.start_time.isoformat() if event.start_time else None,
                'end_time': event.end_time.isoformat() if event.end_time else None,
                'description': event.description,
                'location': event.location,
                'attendees': json.loads(event.attendees) if event.attendees else [],
                'is_all_day': event.is_all_day,
                'created_at': event.created_at.isoformat() if event.created_at else None,
                'updated_at': event.updated_at.isoformat() if event.updated_at else None,
            }

    def get_email_message(self, email_id: int) -> Optional[Dict[str, Any]]:
        """Get email message by ID."""
        with self.Session() as session:
            email = session.query(EmailMessage).filter_by(id=email_id).first()
            if not email:
                return None

            return {
                'id': email.id,
                'message_id': email.message_id,
                'subject': email.subject,
                'sender': email.sender,
                'date': email.date.isoformat() if email.date else None,
                'body': email.body,
                'created_at': email.created_at.isoformat() if email.created_at else None,
                'expires_at': email.expires_at.isoformat() if email.expires_at else None,
            }


# Global database instance
db = Database()

