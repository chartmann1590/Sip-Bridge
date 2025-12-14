# API Reference

Complete reference for all SIP AI Bridge API endpoints.

Base URL: `http://localhost:5001/api`

## Health & Status

### GET /api/health

Health check for all services.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "api": true,
    "database": true,
    "groq": true,
    "ollama": true,
    "tts": true,
    "sip": true,
    "calendar": true
  }
}
```

### GET /api/status

Get current bridge status.

**Response:**
```json
{
  "sip_registered": true,
  "active_call": "abc123",
  "config": { ... }
}
```

## Configuration

### GET /api/config

Get current configuration (excluding sensitive data).

**Response:**
```json
{
  "groq_api_key": "***",
  "ollama_url": "http://host.docker.internal:11434",
  "ollama_model": "llama3.1",
  "tts_url": "http://localhost:5050",
  "timezone": "America/New_York",
  ...
}
```

### POST /api/config

Update configuration.

**Request Body:**
```json
{
  "ollama_model": "llama3.2",
  "timezone": "Europe/London",
  "calendar_url": "https://..."
}
```

**Response:**
```json
{
  "status": "updated",
  "config": { ... }
}
```

### GET /api/voices

List available TTS voices.

**Response:**
```json
{
  "voices": [
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    ...
  ]
}
```

## Conversations

### GET /api/conversations

List conversations with pagination.

**Query Parameters:**
- `limit` (default: 50) - Maximum number of conversations
- `offset` (default: 0) - Offset for pagination

**Response:**
```json
{
  "conversations": [
    {
      "id": 1,
      "call_id": "abc123",
      "caller_id": "+1234567890",
      "started_at": "2025-01-15T10:00:00Z",
      "ended_at": "2025-01-15T10:05:00Z",
      "duration_seconds": 300,
      "status": "completed"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

### GET /api/conversations/:call_id

Get a specific conversation with messages.

**Response:**
```json
{
  "conversation": {
    "id": 1,
    "call_id": "abc123",
    ...
  },
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "Hello",
      "calendar_refs": [...],
      "email_refs": [...],
      "weather_refs": [...],
      "tomtom_refs": [...],
      "note_refs": [...]
    }
  ]
}
```

### GET /api/messages

Get recent messages across all conversations.

**Query Parameters:**
- `limit` (default: 100) - Maximum number of messages

**Response:**
```json
{
  "messages": [
    {
      "id": 1,
      "conversation_id": 1,
      "role": "user",
      "content": "Hello",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

### GET /api/messages/:message_id

Get a specific message with all references.

**Response:**
```json
{
  "id": 1,
  "role": "user",
  "content": "What's the weather?",
  "calendar_refs": [...],
  "email_refs": [...],
  "weather_refs": [
    {
      "ref_index": 0,
      "weather": {
        "location": "New York",
        "temperature": 72,
        "description": "sunny"
      }
    }
  ],
  "tomtom_refs": [...],
  "note_refs": [...]
}
```

## Calendar

### GET /api/calendar/test

Test calendar connection and fetch events.

**Response:**
```json
{
  "status": "success",
  "total_events": 25,
  "upcoming_events": [
    {
      "id": 1,
      "summary": "Meeting",
      "start": "2025-01-16T14:00:00Z",
      "end": "2025-01-16T15:00:00Z",
      "location": "Office"
    }
  ]
}
```

### GET /api/calendar/events

Get upcoming calendar events.

**Query Parameters:**
- `days` (default: 30) - Number of days to look ahead
- `limit` (default: 50) - Maximum number of events

**Response:**
```json
{
  "events": [...],
  "count": 7
}
```

### GET /api/calendar/events/:event_id

Get full calendar event details by ID.

**Response:**
```json
{
  "id": 1,
  "summary": "Meeting",
  "description": "Team meeting",
  "start": "2025-01-16T14:00:00Z",
  "end": "2025-01-16T15:00:00Z",
  "location": "Office",
  "organizer": "john@example.com"
}
```

## Email

### GET /api/email/test

Test email connection and fetch unread emails.

**Response:**
```json
{
  "status": "success",
  "count": 3,
  "emails": [
    {
      "id": 1,
      "subject": "Meeting Tomorrow",
      "sender": "john@example.com",
      "date": "2025-01-15T10:30:00Z",
      "body": "Just a reminder..."
    }
  ]
}
```

### GET /api/email/unread

Get unread emails.

**Query Parameters:**
- `limit` (default: 3) - Maximum number of emails

**Response:**
```json
{
  "emails": [...],
  "count": 3
}
```

### GET /api/emails/:email_id

Get full email message details by ID.

**Response:**
```json
{
  "id": 1,
  "subject": "Meeting Tomorrow",
  "sender": "john@example.com",
  "sender_name": "John Smith",
  "date": "2025-01-15T10:30:00Z",
  "body": "Full email body...",
  "message_id": "<...>"
}
```

## Notes

### GET /api/notes

Get all notes.

**Response:**
```json
{
  "notes": [
    {
      "id": 1,
      "title": "Meeting Notes",
      "summary": "AI-generated summary",
      "transcript": "[03:45:23 PM EST] Meeting with John...",
      "call_id": "abc123",
      "created_at": "2025-01-15T20:45:23Z",
      "updated_at": "2025-01-15T20:45:23Z"
    }
  ]
}
```

### GET /api/notes/:note_id

Get a specific note.

**Response:**
```json
{
  "id": 1,
  "title": "Meeting Notes",
  "summary": "AI-generated summary",
  "transcript": "[03:45:23 PM EST] Meeting with John...",
  "call_id": "abc123",
  "created_at": "2025-01-15T20:45:23Z",
  "updated_at": "2025-01-15T20:45:23Z"
}
```

### POST /api/notes

Create a new note.

**Request Body:**
```json
{
  "title": "Note Title",
  "transcript": "Full transcript text",
  "summary": "Optional AI summary",
  "call_id": "optional-call-id"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Note Title",
  ...
}
```

### PUT /api/notes/:note_id

Update a note.

**Request Body:**
```json
{
  "title": "Updated Title",
  "summary": "Updated summary",
  "transcript": "Updated transcript"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Updated Title",
  ...
}
```

### DELETE /api/notes/:note_id

Delete a note.

**Response:**
```json
{
  "success": true
}
```

## Ollama Models

### GET /api/models

Get available Ollama models.

**Response:**
```json
{
  "models": [
    "llama3.1",
    "llama3.2",
    "mistral"
  ],
  "current_model": "llama3.1"
}
```

### POST /api/models/pull

Pull a model from Ollama library.

**Request Body:**
```json
{
  "model": "llama3.2"
}
```

**Response:**
```json
{
  "status": "success",
  "model": "llama3.2"
}
```

### POST /api/models/select

Select which model to use for responses.

**Request Body:**
```json
{
  "model": "llama3.2"
}
```

**Response:**
```json
{
  "status": "success",
  "model": "llama3.2"
}
```

## SIP Control

### POST /api/sip/restart

Restart SIP client.

**Response:**
```json
{
  "status": "restarted"
}
```

### POST /api/sip/hangup

Hang up current call.

**Response:**
```json
{
  "status": "hung_up"
}
```

## Testing

### POST /api/test/transcribe

Test transcription with uploaded audio file.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `audio` (file)

**Response:**
```json
{
  "transcription": "Hello, this is a test"
}
```

### POST /api/test/ollama

Test Ollama with text input.

**Request Body:**
```json
{
  "text": "Hello, how are you?"
}
```

**Response:**
```json
{
  "response": "I'm doing well, thank you!",
  "model": "llama3.1"
}
```

### POST /api/test/tts

Test TTS synthesis.

**Request Body:**
```json
{
  "text": "Hello, this is a test"
}
```

**Response:**
- Returns audio file (binary)

## Logs

### GET /api/logs

Get call logs.

**Query Parameters:**
- `limit` (default: 100) - Maximum number of logs
- `level` - Filter by log level (info, warning, error)
- `call_id` - Filter by call ID

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "level": "info",
      "category": "sip_initialized",
      "message": "SIP client started successfully",
      "call_id": null,
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

## WebSocket Events

The API also supports WebSocket connections for real-time updates via Socket.IO.

**Connection:**
```javascript
import io from 'socket.io-client';
const socket = io('http://localhost:5001');
```

### Events

#### call_status
Emitted when call status changes.

```javascript
socket.on('call_status', (data) => {
  // data: { status, call_id, caller_id, timestamp }
});
```

#### new_message
Emitted when a new message is added to a conversation.

```javascript
socket.on('new_message', (data) => {
  // data: { conversation_id, role, content, ... }
});
```

#### conversation_update
Emitted when a conversation is updated.

```javascript
socket.on('conversation_update', (data) => {
  // data: { conversation object }
});
```

#### sip_status
Emitted when SIP registration status changes.

```javascript
socket.on('sip_status', (data) => {
  // data: { registered: true/false, message: "..." }
});
```

#### health_status
Emitted when service health status changes.

```javascript
socket.on('health_status', (data) => {
  // data: { services: {...} }
});
```

#### note_created
Emitted when a new note is created.

```javascript
socket.on('note_created', (data) => {
  // data: { note object }
});
```

#### note_updated
Emitted when a note is updated.

```javascript
socket.on('note_updated', (data) => {
  // data: { note object }
});
```

#### note_deleted
Emitted when a note is deleted.

```javascript
socket.on('note_deleted', (data) => {
  // data: { id: note_id }
});
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error message description"
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created (for POST requests)
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

## Authentication

Currently, the API does not require authentication. All endpoints are accessible without credentials. For production deployments, consider adding authentication middleware.

## Rate Limiting

No rate limiting is currently implemented. For production deployments, consider adding rate limiting to prevent abuse.
