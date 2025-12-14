# Changelog

This document tracks significant changes and improvements to the SIP AI Bridge.

## Recent Updates

### Dashboard Improvements
- **Recent Call Activity**: Added section showing last 10 calls with real-time updates
- **Enhanced Call Status**: Improved visual indicators for call states (Idle/Ringing/Connected)
- **Service Health Monitoring**: Added calendar service to health checks
- **Removed**: SIP Control section and Recent Logs (moved to more appropriate locations)

### Conversation List Enhancements
- **Pagination**: Added pagination support (10 conversations per page)
- **Improved Scrolling**: Disabled auto-scroll for new messages to allow reading past messages
- **Search Integration**: Pagination resets when searching

### Call Status Fixes
- **Ringing Status**: Added 'ringing' status broadcast when INVITE is received
- **Caller ID Extraction**: Enhanced extraction from SIP INVITE messages
- **Status Reset**: Automatically resets to 'idle' after call ends
- **Field Mapping**: Fixed snake_case to camelCase mapping in WebSocket events

## Feature History

### Notes Feature
- Voice-activated note-taking during calls
- Timestamped transcripts
- AI-generated summaries
- Web interface for managing notes

### TomTom Integration
- Driving directions between locations
- Traffic incident detection
- Points of interest search
- Automatic detection in conversations

### Calendar Integration
- iCalendar feed support
- Automatic event fetching
- 15-minute caching for performance
- Context injection for calendar-aware responses

### Email Integration
- IMAP email checking on-demand
- Gmail App Password support
- Privacy-focused (emails not permanently stored)
- Trigger-based email fetching

### Weather Integration
- OpenWeatherMap API integration
- Automatic weather detection
- Multiple temperature units
- Location-based weather queries
