# Email Integration Guide

The SIP AI Bridge now supports email integration via IMAP, allowing the AI to check your inbox **only when you specifically ask** during a call.

## Features

- **On-Demand Email Checking**: AI only checks emails when you ask (e.g., "Do I have any new emails?")
- **Unread Emails Only**: Fetches up to 3 most recent unread emails from your primary inbox
- **Gmail App Password Support**: Secure authentication using Google App Passwords
- **Configurable IMAP Settings**: Works with Gmail, Outlook, and other IMAP providers
- **Privacy-Focused**: Emails are fetched in real-time, never stored permanently

## Setup

### 1. Get Your Gmail App Password

**Important**: Do NOT use your regular Gmail password. You must create an App Password.

#### Steps to Create Gmail App Password:

1. Go to https://myaccount.google.com/apppasswords
2. Sign in to your Google Account
3. Create a new App Password:
   - Select app: "Mail"
   - Select device: "Other (Custom name)"
   - Enter a name like "SIP AI Bridge"
4. Click "Generate"
5. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)
6. **Save this password** - you'll need it for configuration

### 2. Configure Email Settings

#### Via Web Interface (Recommended):

1. Open the SIP AI Bridge web interface (http://localhost:3002)
2. Go to the **Settings** tab
3. Scroll to **Email Integration (IMAP)** section
4. Fill in:
   - **Email Address**: your.email@gmail.com
   - **App Password**: The 16-character password from Step 1
   - **IMAP Server**: imap.gmail.com (default for Gmail)
   - **IMAP Port**: 993 (default for SSL)
5. Click **Save Changes**

#### Via Environment Variables:

Add to your `.env` file:
```env
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_APP_PASSWORD=abcdefghijklmnop
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993
```

Then restart the container:
```bash
docker-compose restart
```

### 3. Test the Connection

Test that email is configured correctly:

```bash
curl http://localhost:5001/api/email/test
```

Expected response:
```json
{
  "status": "success",
  "count": 3,
  "emails": [
    {
      "subject": "Meeting Tomorrow",
      "sender": "john@example.com",
      "date": "2025-12-08T10:30:00Z",
      "body": "Just a reminder about our meeting...",
      "message_id": "<...>"
    }
  ]
}
```

## How It Works

### Trigger Keywords

The AI will check your email when you use these words/phrases:
- "email" / "e-mail"
- "mail"
- "inbox"
- "message"

### Example Conversations

```
You: "Do I have any new emails?"
AI: "Yes, you have 2 unread emails. The first one is from John Smith about
     'Meeting Tomorrow' received at 10:30 AM today..."

You: "Check my inbox"
AI: "Looking at your inbox now... You have 3 unread messages. The most recent
     is from Sarah about 'Project Update'..."

You: "What's in my email?"
AI: "You have no unread emails in your inbox right now."
```

### What the AI Sees

When you ask about emails, the AI receives:
- **Subject line**
- **Sender** (name and email address)
- **Date/time** received
- **Body preview** (first 1000 characters)

For long emails, the body is truncated with "[Email truncated for brevity]"

## Privacy & Security

### Security Measures

✅ **App Passwords Only**: Uses Google App Passwords, not your main password
✅ **Read-Only Access**: Cannot send emails, only read
✅ **No Permanent Storage**: Emails are not saved to database
✅ **On-Demand Only**: Only fetches when explicitly asked
✅ **Limited Scope**: Only unread emails from primary inbox
✅ **Encrypted Connection**: Uses SSL/TLS (port 993)

### What's NOT Stored

- Email content is never saved to the database
- Emails are only in memory during the call
- After the call ends, email data is discarded

### What IS Stored

- Your email address (in config)
- Your app password (in config, encrypted at rest)
- IMAP server settings

## IMAP Settings for Other Providers

### Outlook/Office 365
```
IMAP Server: outlook.office365.com
IMAP Port: 993
```

### Yahoo Mail
```
IMAP Server: imap.mail.yahoo.com
IMAP Port: 993
```

### iCloud Mail
```
IMAP Server: imap.mail.me.com
IMAP Port: 993
Note: Requires App-Specific Password
```

### Custom IMAP Server
Configure your provider's IMAP settings in the Settings page.

## API Endpoints

### `GET /api/email/test`
Test email connection and fetch unread emails.

**Response:**
```json
{
  "status": "success",
  "count": 3,
  "emails": [...]
}
```

### `GET /api/email/unread?limit=3`
Get unread emails.

**Query Parameters:**
- `limit` (default: 3) - Maximum number of emails to fetch

**Response:**
```json
{
  "emails": [...],
  "count": 3
}
```

## Troubleshooting

### "Email credentials not configured"
- Make sure you've set EMAIL_ADDRESS and EMAIL_APP_PASSWORD
- Save settings and refresh the page

### "IMAP error: authentication failed"
- Double-check your app password (not your regular password)
- Make sure you copied the 16-character password correctly
- For Gmail, ensure App Passwords are enabled (2FA must be enabled)

### "Connection timeout"
- Check your IMAP server address
- Verify port 993 is not blocked by firewall
- For corporate email, check if IMAP is enabled

### "No emails found" but you have unread emails
- The integration only checks INBOX (primary mailbox)
- Emails in other folders/labels are not fetched
- Only truly "unread" emails are returned

### AI doesn't check emails when asked
- Make sure you use trigger keywords (email, mail, inbox, message)
- Verify email configuration is saved
- Check Docker logs for errors: `docker-compose logs --tail=50`

## Calendar Caching Update

**Note**: The calendar integration has been updated to cache events for **15 minutes** instead of fetching on every request. This reduces API calls and improves performance.

- Calendar events are cached for 15 minutes
- Cache is automatically refreshed after expiration
- Manual refresh available via `/api/calendar/test` endpoint

## Technical Details

### Email Client
- Location: `backend/app/email_client.py`
- Library: Python's built-in `imaplib`
- Features:
  - IMAP4_SSL connection
  - Email parsing with `email` module
  - HTML to text conversion
  - Header decoding (UTF-8, quoted-printable, etc.)
  - Body truncation for large emails

### Integration Points
- Trigger detection in `backend/app/sip_client.py` (line 916-941)
- API endpoints in `backend/app/main.py`
- Settings UI in `frontend/src/components/Settings.tsx`
- Configuration in `backend/app/config.py`

### Performance
- Email fetching takes ~2-3 seconds
- Only happens when user asks
- Does not slow down normal conversation
- Cached emails are not re-fetched during same call

## Example Use Cases

1. **Morning Briefing**
   - "What emails do I have?"
   - AI lists your 3 most recent unread emails

2. **Waiting for Important Email**
   - "Did I get an email from John?"
   - AI checks and tells you if there's an email from John

3. **Quick Inbox Check**
   - "Any new messages?"
   - AI tells you how many unread emails you have

## Future Enhancements

Potential improvements:
- Search by sender
- Search by subject keywords
- Mark emails as read
- Different mailbox/folder support
- Increase email limit
- Email sending capability (with user approval)

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Test API: `curl http://localhost:5001/api/email/test`
- Verify config: `curl http://localhost:5001/api/config`
