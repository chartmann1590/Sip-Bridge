# Notes Feature

The SIP AI Bridge includes a voice note-taking feature that allows you to capture timestamped transcripts during phone calls. Notes are automatically transcribed, stored, and can be reviewed later in the web interface.

## Features

- **Voice-Activated**: Start and stop note-taking with simple voice commands
- **Timestamped Transcripts**: Every utterance is recorded with a timestamp
- **AI-Generated Summaries**: Optional AI summaries for quick reference
- **Call-Linked**: Notes are automatically linked to the call where they were created
- **Web Interface**: View, edit, and manage all notes in the Notes tab
- **Real-Time Updates**: Notes appear in the web interface immediately after saving

## How to Use

### Starting a Note

During a phone call, say one of these phrases to start taking notes:
- "start note"
- "begin note"
- "take note"

The AI will silently start recording everything you say. You won't hear a confirmation (to avoid interrupting your flow).

### Recording Your Note

Once note-taking is active:
- Everything you say will be transcribed and timestamped
- The AI will NOT respond to your speech (it's recording silently)
- You can speak naturally - pauses and full sentences are captured
- Each utterance gets a timestamp in your configured timezone

### Stopping a Note

Say one of these phrases to stop and save the note:
- "stop note"
- "end note"
- "finish note"
- "save note"

The note will be saved with:
- A title (auto-generated from the first few words or you can edit it)
- Full timestamped transcript
- Optional AI-generated summary
- Link to the call where it was created

## Example Usage

```
[During a phone call]

You: "Start note"
[AI silently starts recording]

You: "Meeting with John tomorrow at 3pm. Need to discuss the project proposal. 
      Remember to bring the budget spreadsheet."

You: "Stop note"
[Note is saved with transcript and summary]
```

The saved note will contain:
- **Title**: "Meeting with John tomorrow at 3pm"
- **Transcript**: 
  ```
  [03:45:23 PM EST] Meeting with John tomorrow at 3pm. Need to discuss the project proposal.
  [03:45:28 PM EST] Remember to bring the budget spreadsheet.
  ```
- **Summary**: "Meeting scheduled with John tomorrow at 3pm to discuss project proposal. Need to bring budget spreadsheet."

## Web Interface

### Viewing Notes

1. Open the SIP AI Bridge web interface (http://localhost:3002)
2. Click on the **Notes** tab
3. See all your notes listed by creation date (newest first)

### Note Details

Each note shows:
- **Title**: Quick reference name
- **Summary**: AI-generated summary (if available)
- **Transcript**: Full timestamped transcript
- **Created At**: When the note was created
- **Call ID**: Link to the original call (if available)

### Editing Notes

1. Click on a note to view details
2. Click the **Edit** button
3. Modify title, summary, or transcript
4. Click **Save** to update

### Deleting Notes

1. Click on a note to view details
2. Click the **Delete** button
3. Confirm deletion

## API Endpoints

### Get All Notes
```http
GET /api/notes
```

Response:
```json
{
  "notes": [
    {
      "id": 1,
      "title": "Meeting with John",
      "summary": "Meeting scheduled...",
      "transcript": "[03:45:23 PM EST] Meeting with John...",
      "call_id": "abc123",
      "created_at": "2025-01-15T20:45:23Z",
      "updated_at": "2025-01-15T20:45:23Z"
    }
  ]
}
```

### Get Specific Note
```http
GET /api/notes/:note_id
```

### Create Note
```http
POST /api/notes
Content-Type: application/json

{
  "title": "Note Title",
  "transcript": "Full transcript text",
  "summary": "Optional AI summary",
  "call_id": "optional-call-id"
}
```

### Update Note
```http
PUT /api/notes/:note_id
Content-Type: application/json

{
  "title": "Updated Title",
  "summary": "Updated summary",
  "transcript": "Updated transcript"
}
```

### Delete Note
```http
DELETE /api/notes/:note_id
```

## Technical Details

### Note-Taking Flow

1. **Activation**: User says "start note" → `_start_note_taking()` is called
2. **Recording**: All transcribed text is appended to `note_transcripts` list with timestamps
3. **Silent Mode**: AI responses are suppressed during note-taking
4. **Deactivation**: User says "stop note" → `_stop_note_taking()` is called
5. **Saving**: Note is saved to database with transcript and optional AI summary

### Timestamp Format

Timestamps use your configured timezone and format:
- Format: `%I:%M:%S %p %Z` (e.g., "03:45:23 PM EST")
- Timezone: Set via `TIMEZONE` environment variable or Settings UI
- Default: UTC if not configured

### AI Summary Generation

When a note is saved:
- The full transcript is sent to the AI (Ollama or Groq)
- AI generates a concise summary
- Summary is stored with the note for quick reference
- If AI is unavailable, note is saved without summary

### Database Schema

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    transcript TEXT NOT NULL,
    call_id VARCHAR(100),
    created_at DATETIME,
    updated_at DATETIME
);
```

## Privacy & Storage

- Notes are stored locally in the SQLite database
- Transcripts contain only what you said during note-taking
- Notes are linked to calls but can exist independently
- You can delete notes at any time
- No external services receive your note content (except for optional AI summary)

## Troubleshooting

### Note not starting

1. Make sure you say the exact phrase: "start note", "begin note", or "take note"
2. Wait for the current AI response to finish before starting a note
3. Check Docker logs: `docker-compose logs | grep note`

### Note not stopping

1. Make sure you say: "stop note", "end note", "finish note", or "save note"
2. Wait a moment for processing
3. Check the Notes tab in the web interface to see if it was saved

### Timestamps incorrect

1. Verify your timezone is set correctly in Settings
2. Check `TIMEZONE` environment variable
3. Restart the container after changing timezone

### AI summary not generated

1. Check that Ollama or Groq LLM is available
2. Summary generation is optional - notes work without it
3. Check Docker logs for AI errors

### Notes not appearing in web interface

1. Refresh the Notes tab
2. Check that the note was actually saved (check logs)
3. Verify WebSocket connection is working
4. Try manually fetching: `curl http://localhost:5001/api/notes`

## Best Practices

1. **Be Clear**: Speak clearly when taking notes for better transcription
2. **Natural Pauses**: Don't worry about pausing - timestamps capture everything
3. **Review Later**: Check the web interface to review and edit notes
4. **Use Summaries**: AI summaries help you quickly find important notes
5. **Link to Calls**: Notes are automatically linked to calls for context

## Future Enhancements

Potential improvements:
- Voice commands to search notes during calls
- Automatic categorization of notes
- Export notes to text files
- Note sharing/collaboration
- Voice playback of notes
- Note templates
