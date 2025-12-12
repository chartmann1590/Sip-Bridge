# SIP AI Bridge Flutter App

A mobile companion app for the SIP AI Bridge system that provides real-time monitoring and control of your SIP-to-AI voice bridge.

## Features

- **Real-time Dashboard**: Monitor call status, service health, and system metrics
- **Conversation History**: Browse and search past conversations with full message transcripts
- **Voice Notes**: Create, edit, and manage notes from call transcripts
- **Settings Management**: Configure SIP, AI services, and integrations
- **WebSocket Integration**: Real-time updates for calls, messages, and system status
- **Dark/Light Theme**: Beautiful UI with theme support

## Screens

### Dashboard
- Current call status with hangup controls
- Service health monitoring for all components
- AI integration status
- Recent call activity
- Quick statistics

### Conversations
- List of all conversations with search and filtering
- Detailed conversation view with message history
- Real-time message updates during active calls
- Message attachments (calendar events, emails, weather, maps)

### Notes
- Create new notes from call transcripts
- Edit and delete existing notes
- Search and filter notes
- View note summaries and full transcripts

### Settings
- **SIP Configuration**: SIP server settings and credentials
- **AI Configuration**: Ollama, Groq, TTS settings
- **Integrations**: Calendar, Email, Weather, TomTom configuration
- **Service Testing**: Test connections to integrated services

## Architecture

### State Management
- **Provider Pattern**: Global state management with ChangeNotifier
- **AppState**: Connection status, call state, service health
- **ConversationProvider**: Conversation and message management
- **NotesProvider**: Note CRUD operations
- **SettingsProvider**: Configuration management

### Services
- **ApiClient**: HTTP API client for backend communication
- **WebSocketService**: Real-time WebSocket integration
- **WebSocketMessageHandler**: Message routing and processing

### Models
- **Conversation**: Call metadata and status
- **Message**: User/AI exchanges with rich attachments
- **Note**: Voice notes with transcripts
- **ServiceStatus**: Health monitoring
- **AppSettings**: Complete configuration

## Setup

### Prerequisites
- Flutter SDK 3.0.0+
- Dart SDK
- Android Studio / Xcode for mobile development
- Running SIP AI Bridge backend

### Configuration

1. **Backend URL**: Update the API base URL in providers if needed
   - Default: `http://localhost:5001`
   - For production: Update to your server's IP/URL

2. **WebSocket URL**: Update in AppState if needed
   - Default: `ws://localhost:5001`
   - Should match your backend WebSocket endpoint

### Running the App

```bash
# Install dependencies
flutter pub get

# Run on Android
flutter run -d android

# Run on iOS
flutter run -d ios

# Build APK
flutter build apk

# Build App Bundle
flutter build appbundle

# Build iOS
flutter build ios
```

## WebSocket Integration

The app connects to the backend via WebSocket for real-time updates:

- **call_status**: Current call information (caller ID, status)
- **message**: New messages in conversations
- **sip_status**: SIP registration status
- **service_status**: Service health updates

## API Endpoints

The app communicates with the following backend endpoints:

### Health & Status
- `GET /api/health` - Service health status
- `GET /api/status` - Current system status

### Conversations
- `GET /api/conversations` - List conversations
- `GET /api/conversations/{callId}` - Get conversation details

### Notes
- `GET /api/notes` - List all notes
- `GET /api/notes/{noteId}` - Get note details
- `POST /api/notes` - Create new note
- `PUT /api/notes/{noteId}` - Update note
- `DELETE /api/notes/{noteId}` - Delete note

### Settings
- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration

### SIP Control
- `POST /api/sip/restart` - Restart SIP client
- `POST /api/sip/hangup` - Hang up current call

### Testing
- `GET /api/calendar/test` - Test calendar connection
- `GET /api/email/test` - Test email connection

## Error Handling

The app includes comprehensive error handling:
- Network error detection
- API error responses
- WebSocket reconnection logic
- User-friendly error messages
- Retry mechanisms

## Theming

The app supports both light and dark themes:
- **Light Theme**: Clean, professional appearance
- **Dark Theme**: Reduced eye strain, modern look
- **Custom Colors**: Blue for primary actions, green for success states

## Dependencies

### Core
- `provider`: State management
- `go_router`: Navigation
- `http`: API client
- `web_socket_channel`: WebSocket integration

### UI
- `flutter_svg`: SVG support
- `lucide_icons`: Beautiful icon set
- `google_fonts`: Inter font family

### Utilities
- `intl`: Internationalization
- `shared_preferences`: Local storage
- `url_launcher`: External links
- `audioplayers`: Audio playback

## Future Enhancements

- Push notifications for incoming calls
- Audio playback of call recordings
- Voice note creation from microphone
- Biometric authentication
- Multi-language support
- Advanced analytics and reporting

## License

MIT License - See LICENSE file for details.