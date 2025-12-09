"""iCalendar client for fetching and parsing calendar data."""
import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from icalendar import Calendar
from dateutil.rrule import rrulestr
from dateutil import parser as date_parser
import pytz

logger = logging.getLogger(__name__)


class CalendarEvent:
    """Represents a single calendar event."""

    def __init__(self, summary: str, start: datetime, end: datetime,
                 description: Optional[str] = None, location: Optional[str] = None,
                 is_all_day: bool = False):
        self.summary = summary
        self.start = start
        self.end = end
        self.description = description
        self.location = location
        self.is_all_day = is_all_day

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'summary': self.summary,
            'start': self.start.isoformat() if self.start else None,
            'end': self.end.isoformat() if self.end else None,
            'description': self.description,
            'location': self.location,
            'is_all_day': self.is_all_day,
        }

    def __repr__(self) -> str:
        """String representation of event."""
        if self.is_all_day:
            return f"{self.summary} (All day on {self.start.strftime('%Y-%m-%d')})"
        return f"{self.summary} ({self.start.strftime('%Y-%m-%d %H:%M')} - {self.end.strftime('%H:%M')})"


class CalendarClient:
    """Client for fetching and parsing iCalendar (.ics) files."""

    def __init__(self, calendar_url: Optional[str] = None):
        self.calendar_url = calendar_url
        self._cached_events: List[CalendarEvent] = []
        self._last_fetch: Optional[datetime] = None
        self._cache_duration = timedelta(minutes=30)  # Cache for 30 minutes

    def set_calendar_url(self, url: str) -> None:
        """Set or update the calendar URL."""
        if self.calendar_url == url:
            return

        self.calendar_url = url
        # Clear cache when URL changes
        self._cached_events = []
        self._last_fetch = None

    def fetch_calendar(self, url: Optional[str] = None) -> tuple[Optional[List[CalendarEvent]], Optional[str]]:
        """
        Fetch and parse calendar from URL.

        Args:
            url: Calendar URL (uses instance URL if not provided)

        Returns:
            Tuple of (events list, error message)
        """
        calendar_url = url or self.calendar_url

        if not calendar_url:
            return None, "No calendar URL configured"

        # Use cached result (events or failure backoff) if still valid
        if self._last_fetch:
            age = datetime.now(timezone.utc) - self._last_fetch
            if age < self._cache_duration:
                if self._cached_events:
                    logger.info(f"Using cached calendar events ({len(self._cached_events)} events)")
                    return self._cached_events, None
                else:
                    logger.debug("Skipping calendar fetch (backoff active)")
                    return None, "Skipping fetch due to recent failure (backoff)"

        try:
            logger.info(f"Fetching calendar from: {calendar_url}")

            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(calendar_url)

                if response.status_code != 200:
                    error = f"Failed to fetch calendar: HTTP {response.status_code}"
                    logger.error(error)
                    self._last_fetch = datetime.now(timezone.utc)
                    return None, error

                # Parse iCalendar data
                cal = Calendar.from_ical(response.content)
                events = self._parse_calendar(cal)

                # Cache the events
                self._cached_events = events
                self._last_fetch = datetime.now(timezone.utc)

                logger.info(f"Successfully fetched {len(events)} events from calendar")
                return events, None

        except Exception as e:
            error = f"Error fetching calendar: {str(e)}"
            logger.warning(error) # Reduced to warning and removed stack trace for cleaner logs
            self._last_fetch = datetime.now(timezone.utc)
            return None, error

    def _parse_calendar(self, cal: Calendar) -> List[CalendarEvent]:
        """Parse calendar and extract events."""
        events = []
        now = datetime.now(timezone.utc)

        for component in cal.walk():
            if component.name == "VEVENT":
                try:
                    event = self._parse_event(component, now)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Error parsing event: {e}")
                    continue

        # Sort events by start time
        events.sort(key=lambda e: e.start)

        return events

    def _parse_event(self, component, now: datetime) -> Optional[CalendarEvent]:
        """Parse a single event component."""
        summary = str(component.get('summary', 'Untitled Event'))

        # Get start and end times
        dtstart = component.get('dtstart')
        dtend = component.get('dtend')

        if not dtstart:
            return None

        # Convert to datetime
        start = dtstart.dt if hasattr(dtstart, 'dt') else dtstart
        end = dtend.dt if dtend and hasattr(dtend, 'dt') else None

        # Check if all-day event
        is_all_day = isinstance(start, datetime) is False

        # Convert date to datetime if needed
        if not isinstance(start, datetime):
            from datetime import date
            start = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
            is_all_day = True

        if end and not isinstance(end, datetime):
            from datetime import date
            end = datetime.combine(end, datetime.min.time()).replace(tzinfo=timezone.utc)

        # Ensure timezone-aware
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # If no end time, use start time + 1 hour
        if not end:
            if is_all_day:
                end = start + timedelta(days=1)
            else:
                end = start + timedelta(hours=1)

        # Get optional fields
        description = component.get('description')
        if description:
            description = str(description)

        location = component.get('location')
        if location:
            location = str(location)

        # Handle recurring events
        rrule = component.get('rrule')
        if rrule:
            # For recurring events, we'll generate instances for the next 90 days
            return self._handle_recurring_event(
                summary, start, end, description, location, is_all_day, rrule, now
            )

        return CalendarEvent(summary, start, end, description, location, is_all_day)

    def _handle_recurring_event(self, summary: str, start: datetime, end: datetime,
                                description: Optional[str], location: Optional[str],
                                is_all_day: bool, rrule, now: datetime) -> Optional[CalendarEvent]:
        """Handle recurring events - for now, just return the base event."""
        # TODO: Generate recurring instances
        # For now, just return the first occurrence
        return CalendarEvent(summary, start, end, description, location, is_all_day)

    def get_upcoming_events(self, days: int = 30, limit: int = 50) -> List[CalendarEvent]:
        """
        Get upcoming events within the next N days.

        Args:
            days: Number of days to look ahead
            limit: Maximum number of events to return

        Returns:
            List of upcoming events
        """
        events, error = self.fetch_calendar()

        if error or not events:
            return []

        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=days)

        # Filter events that start within the time window
        upcoming = [
            event for event in events
            if now <= event.start <= end_date
        ]

        return upcoming[:limit]

    def get_events_for_date(self, target_date: datetime) -> List[CalendarEvent]:
        """
        Get events for a specific date.

        Args:
            target_date: The date to get events for

        Returns:
            List of events on that date
        """
        events, error = self.fetch_calendar()

        if error or not events:
            return []

        # Normalize target date to start/end of day
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        # Filter events that overlap with the target date
        date_events = [
            event for event in events
            if event.start < end_of_day and event.end > start_of_day
        ]

        return date_events

    def format_events_for_llm(self, events: List[CalendarEvent], user_timezone: str = 'UTC') -> str:
        """
        Format events into a human-readable string for the LLM.

        Args:
            events: List of calendar events
            user_timezone: User's timezone (e.g., 'America/New_York')

        Returns:
            Formatted string describing the events
        """
        if not events:
            return "No upcoming events found."

        lines = ["Here are your upcoming events:"]

        # Get user's timezone
        try:
            tz = pytz.timezone(user_timezone)
        except:
            tz = pytz.UTC
            logger.warning(f"Invalid timezone {user_timezone}, using UTC")

        for event in events:
            # Convert event times to user's timezone
            local_start = event.start.astimezone(tz) if event.start.tzinfo else event.start.replace(tzinfo=pytz.UTC).astimezone(tz)
            local_end = event.end.astimezone(tz) if event.end.tzinfo else event.end.replace(tzinfo=pytz.UTC).astimezone(tz)

            if event.is_all_day:
                lines.append(f"- {event.summary} (All day on {local_start.strftime('%A, %B %d, %Y')})")
            else:
                lines.append(
                    f"- {event.summary} on {local_start.strftime('%A, %B %d at %I:%M %p')} "
                    f"to {local_end.strftime('%I:%M %p')}"
                )
                if event.location:
                    lines.append(f"  Location: {event.location}")
                if event.description:
                    # Truncate long descriptions
                    desc = event.description[:100] + "..." if len(event.description) > 100 else event.description
                    lines.append(f"  Details: {desc}")

        return "\n".join(lines)

    def check_health(self) -> bool:
        """Check if calendar can be fetched."""
        if not self.calendar_url:
            return False

        events, error = self.fetch_calendar()
        return error is None


# Global client instance
calendar_client = CalendarClient()
