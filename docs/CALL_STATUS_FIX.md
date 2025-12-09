# Call Status Update Fix

## Issue
The "Current Call Status" card on the dashboard was not updating during calls, showing "No Active Call" even when a call was in progress.

## Root Cause
The SIP client was not broadcasting call status updates via WebSocket at key moments:
1. **Ringing**: When INVITE was received, no 'ringing' status was sent
2. **Caller ID**: Caller ID was not being extracted from the SIP INVITE message
3. **Field Mapping**: Backend used snake_case (`call_id`, `caller_id`) but frontend expected camelCase (`callId`, `callerId`)
4. **Reset to Idle**: After call ended, status remained as 'ended' instead of resetting to 'idle'

## Changes Made

### Backend Changes (`backend/app/sip_client.py`)

1. **Added 'ringing' Status Broadcast** (Line 351-353)
   ```python
   # Broadcast 'ringing' status
   ws_manager.broadcast_call_status('ringing', call_id, caller_id)
   logger.info(f"Incoming call from {caller_id} (Call-ID: {call_id})")
   ```

2. **Enhanced Caller ID Extraction** (Line 318-335)
   - Extracts display name from From header
   - Handles multiple SIP URI formats:
     - `"Display Name" <sip:user@host>`
     - `<sip:user@host>`
     - `sip:user@host`
   - Falls back to extracting username from SIP URI

3. **Added Reset to 'idle' After Call Ends** (Line 1170-1175)
   ```python
   # After a brief delay, broadcast 'idle' status to reset UI
   def reset_to_idle():
       time.sleep(1)
       ws_manager.broadcast_call_status('idle')
   threading.Thread(target=reset_to_idle, daemon=True).start()
   ```

### Frontend Changes (`frontend/src/hooks/useWebSocket.ts`)

1. **Field Mapping in WebSocket Handler** (Line 84-94)
   ```typescript
   socket.on('call_status', (data: any) => {
     // Map backend fields to frontend interface
     const mappedData: CallStatus = {
       status: data.status,
       callId: data.call_id,
       callerId: data.caller_id,
       timestamp: data.timestamp
     };
     console.log('Received call_status:', mappedData);
     setCallStatus(mappedData);
   });
   ```

## Call Status Flow

### Before Fix
1. INVITE received → No WebSocket broadcast
2. Call answered → Broadcast 'connected' immediately
3. Call ongoing → Status remains 'connected' ✓
4. Call ends → Broadcast 'ended'
5. **Status stuck on 'ended'** ❌

### After Fix
1. INVITE received → **Broadcast 'ringing'** with caller ID ✓
2. Call answered → Broadcast 'connected' ✓
3. Call ongoing → Status remains 'connected' ✓
4. Call ends → Broadcast 'ended' ✓
5. **1 second later → Broadcast 'idle'** ✓

## Status States

| Status | When | UI Display |
|--------|------|------------|
| `idle` | No active call | "No Active Call" (gray) |
| `ringing` | INVITE received | "Ringing" (amber, pulsing) |
| `connected` | Call answered | "Connected" (green, glowing) |
| `ended` | Call terminated | "Ended" (brief, transitions to idle) |

## Visual Indicators

### Dashboard Call Status Card

**Idle State:**
- Gray phone-off icon
- "No Active Call" text
- No caller information

**Ringing State:**
- Amber phone icon (pulsing animation)
- "Ringing" text
- Shows caller ID
- Shows call ID (first 8 chars)

**Connected State:**
- Green phone icon (glowing effect)
- "Connected" text
- Shows caller ID
- Shows call ID
- Hang up button available

## Testing

The fix can be tested by:

1. **Make a call to the SIP bridge**
   - Dashboard should immediately show "Ringing" status
   - Caller ID should appear
   - Status should change to "Connected" when answered

2. **During call**
   - Status should remain "Connected"
   - Caller ID should stay visible

3. **End call**
   - Status should briefly show "Ended"
   - After 1 second, should reset to "No Active Call"

## Console Logging

Added console logging for debugging:
```javascript
console.log('Received call_status:', mappedData);
```

You can open browser DevTools (F12) → Console to see real-time call status updates.

## Backward Compatibility

✅ **Fully backward compatible**
- Existing calls continue to work
- Database schema unchanged
- API endpoints unchanged
- Only WebSocket events enhanced

## Performance Impact

✅ **Minimal**
- One additional WebSocket broadcast on INVITE (ringing)
- One additional broadcast 1 second after call ends (idle)
- Caller ID extraction happens once per call

## Related Files

- `backend/app/sip_client.py` - SIP call handling and status broadcasts
- `backend/app/websocket.py` - WebSocket manager (unchanged)
- `frontend/src/hooks/useWebSocket.ts` - WebSocket event handling
- `frontend/src/components/Dashboard.tsx` - Call status display (unchanged)

## Future Enhancements

Potential improvements:
- Add more granular states (dialing, answering, etc.)
- Show call duration timer during active calls
- Add call quality indicators
- Historical call status tracking
