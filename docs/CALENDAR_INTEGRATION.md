# Calendar Integration

The SIP AI Bridge now supports calendar integration, allowing the AI assistant to access and answer questions about your schedule during phone calls.

## Features

- **Automatic Context**: When configured, your upcoming calendar events (next 30 days) are automatically included in the AI's context during calls
- **Natural Queries**: Ask the AI questions like:
  - "What's on my calendar today?"
  - "Do I have any meetings tomorrow?"
  - "What time is my appointment on Friday?"
  - "Tell me about my schedule this week"
- **iCalendar Support**: Works with any calendar service that provides an iCalendar (.ics) feed URL

## Setup

### 1. Get Your Calendar URL

The calendar integration works with any calendar service that provides an iCalendar feed. Here are instructions for common services:

#### Google Calendar
1. Open Google Calendar
2. Click the three dots next to the calendar you want to share
3. Click "Settings and sharing"
4. Scroll down to "Integrate calendar"
5. Copy the "Secret address in iCal format" URL

#### Outlook/Office 365
1. Open Outlook Calendar
2. Click "Calendar" in the navigation pane
3. Right-click the calendar you want to share
4. Select "Sharing and permissions"
5. Copy the ICS link

#### Apple iCloud Calendar
1. Open iCloud Calendar
2. Click the share icon next to the calendar
3. Enable "Public Calendar"
4. Copy the webcal URL and change `webcal://` to `https://`

#### Cupla (Your Current Setup)
Your calendar URL is already configured:
```
https://api.cupla.app/api/calendars/mine/cupla/calendar.ics?username=1817111a-b2cb-43f0-8115-3f1c36ded340&password=gq8q9p
```

### 2. Configure in Settings

1. Open the SIP AI Bridge web interface (http://localhost:3002 or your configured port)
2. Navigate to the **Settings** tab
3. Scroll down to the **Calendar Integration** section
4. Paste your iCalendar URL into the "Calendar URL (iCalendar/ICS)" field
5. Click **Save Changes**

### 3. Verify Integration

After configuring your calendar URL, you can verify it's working:

1. Use the test endpoint:
   ```bash
   curl http://localhost:5001/api/calendar/test
   ```

2. Check the health endpoint:
   ```bash
   curl http://localhost:5001/api/health
   ```
   You should see `"calendar": true` in the response.

3. View your upcoming events:
   ```bash
   curl http://localhost:5001/api/calendar/events
   ```

## How It Works

1. **Event Fetching**: When a call is initiated, the AI fetches your upcoming events from the configured calendar URL
2. **Context Injection**: Events are formatted and added to the AI's system prompt, giving it awareness of your schedule
3. **Caching**: Events are cached for 15 minutes to improve performance and reduce API calls
4. **Privacy**: Your calendar URL is stored securely in the database and only accessed when needed

## API Endpoints

### `GET /api/calendar/test`
Test the calendar connection and fetch events.

**Response:**
```json
{
  "status": "success",
  "total_events": 25,
  "upcoming_events": [...]
}
```

### `GET /api/calendar/events`
Get upcoming calendar events.

**Query Parameters:**
- `days` (default: 30) - Number of days to look ahead
- `limit` (default: 50) - Maximum number of events to return

**Response:**
```json
{
  "events": [...],
  "count": 7
}
```

## Privacy & Security

- Calendar URLs often contain authentication tokens - keep them secure
- The calendar URL is stored in your local database and never shared
- Events are fetched in real-time and not permanently stored
- Consider using a read-only calendar share link when possible

## Troubleshooting

### "No calendar URL configured" Error
Make sure you've:
1. Entered a valid calendar URL in the Settings page
2. Clicked "Save Changes"
3. Restarted the SIP client if needed

### Calendar events not showing in AI responses
1. Check the health endpoint to verify calendar integration is working
2. Test the calendar endpoint directly to ensure events are being fetched
3. Make sure your calendar URL is publicly accessible (not behind authentication that expires)
4. Check the Docker logs for any calendar-related errors

### Calendar health check fails
1. Verify your calendar URL is correct and accessible
2. Make sure the URL starts with `https://` (not `webcal://`)
3. Test the URL in a web browser - it should download an .ics file
4. Check that the calendar feed is still active and not expired

## Example Conversation

```
User: "What do I have scheduled for tomorrow?"

AI: "Looking at your calendar, you have two things scheduled for tomorrow:
     - Tuxego at 6:30 PM at Tuxego, Troy-Schenectady Road, Latham, NY
     - This will go until 8:30 PM.

     That's all I see for tomorrow, darling!"
```

## Technical Details

### Calendar Client
- Location: `backend/app/calendar_client.py`
- Library: `icalendar` for parsing ICS files
- HTTP Client: `httpx` for fetching calendar feeds
- Caching: 15-minute cache to reduce API calls

### Integration Points
- System prompt injection in `backend/app/sip_client.py` (line 892-905)
- Configuration in `backend/app/config.py`
- API endpoints in `backend/app/main.py`
- Frontend settings in `frontend/src/components/Settings.tsx`
