"""TomTom API client for traffic, directions, and POI lookups."""
import httpx
from typing import Optional, Dict, List, Tuple
from .config import Config
import logging

logger = logging.getLogger(__name__)


class TomTomClient:
    """Client for interacting with TomTom APIs."""

    SEARCH_BASE_URL = "https://api.tomtom.com/search/2"
    ROUTING_BASE_URL = "https://api.tomtom.com/routing/1"
    TRAFFIC_BASE_URL = "https://api.tomtom.com/traffic/services/4"

    def __init__(self):
        self.api_key = Config.TOMTOM_API_KEY

    def search_poi(self, query: str, location: Optional[str] = None, limit: int = 5) -> Optional[Dict]:
        """
        Search for Points of Interest.

        Args:
            query: Search query (e.g., "restaurants", "gas stations")
            location: Optional location context (city, coordinates)
            limit: Maximum number of results

        Returns:
            Dictionary with POI search results or None if request fails
        """
        if not self.api_key:
            logger.error("TomTom API key not configured")
            return None

        try:
            url = f"{self.SEARCH_BASE_URL}/poiSearch/{query}.json"

            params = {
                "key": self.api_key,
                "limit": limit
            }

            # If location provided, try to geocode it first or use it as a lat/lon
            if location:
                params["lat"] = None  # Will be set after geocoding
                params["lon"] = None

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    results = []

                    for result in data.get('results', []):
                        poi_data = {
                            'name': result.get('poi', {}).get('name', ''),
                            'category': ', '.join([cat['name'] for cat in result.get('poi', {}).get('categories', [])]),
                            'address': result.get('address', {}).get('freeformAddress', ''),
                            'position': result.get('position', {}),
                            'distance': result.get('dist'),  # Distance in meters if search had a center point
                            'phone': result.get('poi', {}).get('phone', ''),
                            'url': result.get('poi', {}).get('url', ''),
                        }
                        results.append(poi_data)

                    logger.info(f"Found {len(results)} POI results for '{query}'")
                    return {
                        'query': query,
                        'results': results,
                        'type': 'poi'
                    }
                else:
                    logger.error(f"TomTom POI search error: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error searching POI: {e}")
            return None

    def get_directions(self, origin: str, destination: str,
                       avoid: Optional[List[str]] = None) -> Optional[Dict]:
        """
        Get driving directions between two locations.

        Args:
            origin: Starting point (address or "lat,lon")
            destination: End point (address or "lat,lon")
            avoid: Optional list of things to avoid ["tolls", "motorways", "ferries"]

        Returns:
            Dictionary with route information or None if request fails
        """
        if not self.api_key:
            logger.error("TomTom API key not configured")
            return None

        try:
            # First, geocode origin and destination if they're not coordinates
            origin_coords = self._geocode_location(origin)
            dest_coords = self._geocode_location(destination)

            if not origin_coords or not dest_coords:
                logger.error(f"Could not geocode origin or destination")
                return None

            url = f"{self.ROUTING_BASE_URL}/calculateRoute/{origin_coords}:{dest_coords}/json"

            params = {
                "key": self.api_key,
                "traffic": "true",
                "travelMode": "car"
            }

            if avoid:
                params["avoid"] = ",".join(avoid)

            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()

                    if 'routes' not in data or len(data['routes']) == 0:
                        return None

                    route = data['routes'][0]
                    summary = route.get('summary', {})

                    route_data = {
                        'origin': origin,
                        'destination': destination,
                        'distance_meters': summary.get('lengthInMeters', 0),
                        'distance_miles': round(summary.get('lengthInMeters', 0) / 1609.34, 1),
                        'travel_time_seconds': summary.get('travelTimeInSeconds', 0),
                        'travel_time_minutes': round(summary.get('travelTimeInSeconds', 0) / 60),
                        'traffic_delay_seconds': summary.get('trafficDelayInSeconds', 0),
                        'departure_time': summary.get('departureTime', ''),
                        'arrival_time': summary.get('arrivalTime', ''),
                        'instructions': self._extract_instructions(route.get('guidance', {}).get('instructions', [])),
                        'type': 'directions'
                    }

                    logger.info(f"Route from {origin} to {destination}: {route_data['distance_miles']} mi, {route_data['travel_time_minutes']} min")
                    return route_data
                else:
                    logger.error(f"TomTom routing error: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error getting directions: {e}")
            return None

    def get_traffic_incidents(self, location: str, radius_km: int = 10) -> Optional[Dict]:
        """
        Get traffic incidents near a location.

        Args:
            location: Location to check (address or "lat,lon")
            radius_km: Search radius in kilometers

        Returns:
            Dictionary with traffic incident information or None if request fails
        """
        if not self.api_key:
            logger.error("TomTom API key not configured")
            return None

        try:
            # Geocode location if needed
            coords = self._geocode_location(location)
            if not coords:
                logger.error(f"Could not geocode location: {location}")
                return None

            # Parse coordinates
            lat, lon = coords.split(',')

            url = f"{self.TRAFFIC_BASE_URL}/incidentDetails/s3/{lat},{lon},{radius_km},10/json"

            params = {
                "key": self.api_key
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    incidents = []

                    for incident in data.get('incidents', []):
                        properties = incident.get('properties', {})
                        incident_data = {
                            'type': properties.get('iconCategory', ''),
                            'description': properties.get('description', ''),
                            'road': properties.get('from', ''),
                            'delay_minutes': properties.get('delay', 0) // 60 if properties.get('delay') else 0,
                            'length_meters': properties.get('length', 0),
                            'severity': self._map_magnitude_to_severity(properties.get('magnitudeOfDelay', 0)),
                        }
                        incidents.append(incident_data)

                    logger.info(f"Found {len(incidents)} traffic incidents near {location}")
                    return {
                        'location': location,
                        'radius_km': radius_km,
                        'incidents': incidents,
                        'incident_count': len(incidents),
                        'type': 'traffic'
                    }
                else:
                    logger.error(f"TomTom traffic error: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error getting traffic incidents: {e}")
            return None

    def _geocode_location(self, location: str) -> Optional[str]:
        """Convert address to lat,lon coordinates."""
        # Check if already in lat,lon format
        if ',' in location:
            try:
                parts = location.split(',')
                float(parts[0].strip())
                float(parts[1].strip())
                return location  # Already coordinates
            except:
                pass

        # Geocode the address
        try:
            url = f"{self.SEARCH_BASE_URL}/geocode/{location}.json"
            params = {"key": self.api_key, "limit": 1}

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('results'):
                        pos = data['results'][0].get('position', {})
                        return f"{pos.get('lat')},{pos.get('lon')}"

            logger.warning(f"Could not geocode location: {location}")
            return None

        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None

    def _extract_instructions(self, instructions_list: List[Dict]) -> List[str]:
        """Extract simplified turn-by-turn instructions."""
        simplified = []
        for instruction in instructions_list[:10]:  # Limit to first 10 steps
            text = instruction.get('message', '')
            if text:
                simplified.append(text)
        return simplified

    def _map_magnitude_to_severity(self, magnitude: int) -> str:
        """Map TomTom magnitude to severity level."""
        if magnitude == 0:
            return "Unknown"
        elif magnitude == 1:
            return "Minor"
        elif magnitude == 2:
            return "Moderate"
        elif magnitude == 3:
            return "Major"
        elif magnitude == 4:
            return "Severe"
        else:
            return "Unknown"

    def format_for_voice(self, data: Dict) -> str:
        """Format TomTom data for voice response."""
        if not data:
            return "I couldn't fetch that information."

        data_type = data.get('type', '')

        if data_type == 'poi':
            results = data.get('results', [])
            if not results:
                return f"I couldn't find any {data.get('query', 'results')} nearby."

            response = f"I found {len(results)} {data.get('query', 'places')}. "
            for i, poi in enumerate(results[:3], 1):  # Top 3 results
                response += f"{i}. {poi['name']} at {poi['address']}. "

            return response

        elif data_type == 'directions':
            dist_miles = data.get('distance_miles', 0)
            time_min = data.get('travel_time_minutes', 0)
            traffic_delay = data.get('traffic_delay_seconds', 0) // 60

            response = f"The route from {data.get('origin')} to {data.get('destination')} is {dist_miles} miles and will take approximately {time_min} minutes"

            if traffic_delay > 5:
                response += f", including {traffic_delay} minutes of traffic delay"

            response += ". "
            return response

        elif data_type == 'traffic':
            incident_count = data.get('incident_count', 0)
            if incident_count == 0:
                return f"There are no reported traffic incidents near {data.get('location')}."

            response = f"There are {incident_count} traffic incidents near {data.get('location')}. "
            for incident in data.get('incidents', [])[:3]:  # Top 3 incidents
                response += f"{incident['description']} on {incident['road']}. "

            return response

        return "Here's the information you requested."


# Global TomTom client instance
tomtom_client = TomTomClient()
