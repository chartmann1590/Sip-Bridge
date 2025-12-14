# TomTom Maps Integration

The SIP AI Bridge supports TomTom Maps integration, allowing the AI assistant to provide directions, traffic updates, and find points of interest during phone calls.

## Features

- **Driving Directions**: Get turn-by-turn directions between two locations with distance and travel time
- **Traffic Incidents**: Check for traffic incidents and delays near a location
- **Points of Interest (POI)**: Search for nearby businesses, restaurants, gas stations, and more
- **Automatic Detection**: AI automatically detects when users ask for directions, traffic, or POI searches
- **Smart Geocoding**: Automatically converts addresses to coordinates when needed

## Setup

### 1. Get Your TomTom API Key

1. Go to https://developer.tomtom.com/
2. Sign up for a free account (or sign in if you already have one)
3. Navigate to your dashboard
4. Create a new app or use an existing one
5. Copy your API key

### 2. Configure in Settings

#### Via Web Interface (Recommended):

1. Open the SIP AI Bridge web interface (http://localhost:3002)
2. Go to the **Settings** tab
3. Scroll to **TomTom Maps Integration** section
4. Paste your TomTom API key
5. Click **Save Changes**

#### Via Environment Variables:

Add to your `.env` file:
```env
TOMTOM_API_KEY=your_tomtom_api_key_here
```

Then restart the container:
```bash
docker-compose restart
```

## How It Works

### Trigger Keywords

The AI automatically detects when you're asking for TomTom-related information:

**Directions:**
- "directions from X to Y"
- "how do I get from X to Y"
- "route from X to Y"
- "navigate from X to Y"
- "drive from X to Y"

**Traffic:**
- "traffic near X"
- "traffic in X"
- "traffic around X"
- "traffic conditions in X"

**Points of Interest:**
- "find restaurants near X"
- "gas stations in X"
- "hotels near X"
- "find X near Y"

### Example Conversations

```
You: "Give me directions from Boston to New York"
AI: "The route from Boston to New York is 213.4 miles and will take 
     approximately 220 minutes, including 15 minutes of traffic delay..."

You: "What's the traffic like near downtown?"
AI: "There are 3 traffic incidents near downtown. 
     Road closure on Main Street. Accident on Highway 101..."

You: "Find nearby gas stations"
AI: "I found 5 gas stations. 
     1. Shell at 123 Main Street
     2. BP at 456 Oak Avenue..."
```

## API Capabilities

### Directions

- Calculates optimal driving route
- Includes real-time traffic data
- Provides distance in miles
- Estimates travel time with traffic delays
- Supports origin and destination inference (if one location has state/country, applies to the other)

**Example:**
- "directions from Boston to New York" → Works
- "directions from Boston to New York, NY" → Works
- "directions from Boston, MA to New York" → Works (infers MA for New York)

### Traffic Incidents

- Searches within a configurable radius (default: 10km)
- Returns incident count and details
- Includes delay estimates
- Shows incident severity (Minor, Moderate, Major, Severe)
- Provides road names and descriptions

### Points of Interest

- Searches for businesses and locations
- Returns name, address, category, and distance
- Supports various POI types (restaurants, gas stations, hotels, etc.)
- Can be filtered by location context

## Privacy & Security

- API key is stored securely in the database
- TomTom data is fetched in real-time during calls
- Route and traffic data are stored in conversation history for reference
- No location tracking or persistent storage of user locations

## Troubleshooting

### "TomTom API key not configured"

1. Make sure you've entered your API key in Settings
2. Click "Save Changes" after entering the key
3. Verify the key is correct (no extra spaces)

### Directions not working

1. Check that both origin and destination are provided
2. Ensure location names are spelled correctly
3. Try using "city, state" or "city, country" format for better results
4. Check Docker logs: `docker-compose logs | grep tomtom`

### Traffic not showing

1. Verify the location name is correct
2. Check that there are actually incidents in that area
3. Traffic data is real-time and may not always have incidents
4. Try a larger city or well-known location

### POI search not finding results

1. Make sure your search query is clear (e.g., "restaurants", "gas stations")
2. Try adding a location context (e.g., "restaurants in Boston")
3. Some POI types may not be available in all areas
4. Check Docker logs for API errors

### API quota exceeded

1. TomTom free tier has usage limits
2. Check your TomTom dashboard for quota status
3. Consider upgrading to a paid plan if needed
4. The system will log errors when quota is exceeded

## Technical Details

### TomTom Client

- Location: `backend/app/tomtom_client.py`
- HTTP Client: `httpx` for API requests
- Geocoding: Automatic address-to-coordinates conversion
- Error Handling: Graceful fallback when API fails

### Integration Points

- Trigger detection in `backend/app/sip_client.py` (line 951-1083)
- API endpoints: Integrated into conversation flow (no separate test endpoint)
- Frontend display: `frontend/src/components/TomTomCard.tsx` and `TomTomModal.tsx`
- Database storage: `backend/app/database.py` (TomTomData model)

### Data Storage

TomTom results are stored in the database and linked to messages:
- Directions: Origin, destination, distance, travel time, instructions
- Traffic: Location, incident count, incident details
- POI: Query, results list with names and addresses

## API Reference

### TomTom Search API
- Base URL: `https://api.tomtom.com/search/2`
- POI Search: `/poiSearch/{query}.json`
- Geocoding: `/geocode/{location}.json`

### TomTom Routing API
- Base URL: `https://api.tomtom.com/routing/1`
- Route Calculation: `/calculateRoute/{origin}:{destination}/json`

### TomTom Traffic API
- Base URL: `https://api.tomtom.com/traffic/services/4`
- Incidents: `/incidentDetails/s3/{bbox}/10/-1/json`

## Support

For issues or questions:
- Check logs: `docker-compose logs -f | grep tomtom`
- Verify API key: Check Settings page
- Test in conversation: Ask "directions from X to Y" during a call
- TomTom API docs: https://developer.tomtom.com/documentation
