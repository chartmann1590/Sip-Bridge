"""iCalendar client for fetching and parsing calendar data."""
import requests
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
                 is_all_day: bool = False, uid: Optional[str] = None,
                 attendees: Optional[List[Dict[str, str]]] = None):
        self.summary = summary
        self.start = start
        self.end = end
        self.description = description
        self.location = location
        self.is_all_day = is_all_day
        self.uid = uid or f"generated-{hash(f'{summary}{start}')}"  # Generate UID if not provided
        self.attendees = attendees or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'summary': self.summary,
            'start': self.start.isoformat() if self.start else None,
            'end': self.end.isoformat() if self.end else None,
            'description': self.description,
            'location': self.location,
            'is_all_day': self.is_all_day,
            'uid': self.uid,
            'attendees': self.attendees,
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
        self._cache_duration = timedelta(hours=2)  # Cache for 2 hours
        self._failure_backoff = timedelta(minutes=30)  # Wait 30 min after failure before retrying

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
            if self._cached_events and age < self._cache_duration:
                # Have cached events, use them
                logger.info(f"Using cached calendar events ({len(self._cached_events)} events, age: {age})")
                return self._cached_events, None
            elif not self._cached_events and age < self._failure_backoff:
                # Previous fetch failed, waiting for backoff period
                logger.debug(f"Skipping calendar fetch (failure backoff active, {self._failure_backoff - age} remaining)")
                return None, "Skipping fetch due to recent failure (backoff active)"

        try:
            logger.info(f"Fetching calendar from: {calendar_url}")

            # Use generous timeout - gevent handles DNS properly
            # (connect timeout, read timeout)
            timeout = (30.0, 60.0)

            # Retry logic for transient failures
            max_retries = 2
            last_error = None

            for attempt in range(max_retries):
                try:
                    # Fetch with requests - gevent's monkey patching handles DNS correctly
                    response = requests.get(calendar_url, timeout=timeout, allow_redirects=True)

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

                except (requests.Timeout, requests.ConnectionError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Calendar fetch attempt {attempt + 1} failed, retrying: {str(e)}")
                        continue
                    else:
                        raise

        except Exception as e:
            error = f"Error fetching calendar: {str(e)}"
            logger.warning(error)
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

        # Extract UID (unique identifier for deduplication)
        uid = str(component.get('uid', ''))
        if not uid:
            # Generate UID if not provided
            uid = f"generated-{hash(f'{summary}{start.isoformat()}')}"

        # Extract attendees
        attendees = []
        attendee_list = component.get('attendee', [])
        # Handle single attendee or list
        if not isinstance(attendee_list, list):
            attendee_list = [attendee_list] if attendee_list else []

        for attendee in attendee_list:
            try:
                attendee_info = {
                    'email': str(attendee).replace('MAILTO:', '').replace('mailto:', ''),
                    'name': '',
                    'status': 'NEEDS-ACTION'
                }

                # Extract parameters if available
                if hasattr(attendee, 'params'):
                    attendee_info['name'] = attendee.params.get('CN', '')
                    attendee_info['status'] = attendee.params.get('PARTSTAT', 'NEEDS-ACTION')

                attendees.append(attendee_info)
            except Exception as e:
                logger.warning(f"Could not parse attendee: {e}")
                continue

        # Handle recurring events
        rrule = component.get('rrule')
        if rrule:
            # For recurring events, we'll generate instances for the next 90 days
            return self._handle_recurring_event(
                summary, start, end, description, location, is_all_day, rrule, now, uid, attendees
            )

        return CalendarEvent(summary, start, end, description, location, is_all_day, uid, attendees)

    def _handle_recurring_event(self, summary: str, start: datetime, end: datetime,
                                description: Optional[str], location: Optional[str],
                                is_all_day: bool, rrule, now: datetime, uid: str,
                                attendees: List[Dict[str, str]]) -> Optional[CalendarEvent]:
        """Handle recurring events - for now, just return the base event."""
        # TODO: Generate recurring instances
        # For now, just return the first occurrence
        return CalendarEvent(summary, start, end, description, location, is_all_day, uid, attendees)

    def get_upcoming_events(self, days: int = 30, limit: int = 50, user_timezone: str = 'UTC') -> List[CalendarEvent]:
        """
        Get upcoming events within the next N days.

        Args:
            days: Number of days to look ahead
            limit: Maximum number of events to return
            user_timezone: User's timezone (e.g., 'America/New_York') for filtering

        Returns:
            List of upcoming events
        """
        events, error = self.fetch_calendar()

        if error or not events:
            return []

        # Get user's timezone
        try:
            tz = pytz.timezone(user_timezone)
        except:
            tz = pytz.UTC
            logger.warning(f"Invalid timezone {user_timezone}, using UTC")

        # Use user's timezone for filtering (not UTC)
        now = datetime.now(tz)
        end_date = now + timedelta(days=days)

        # Filter events that start within the time window
        # Convert event times to user's timezone for comparison
        upcoming = []
        for event in events:
            # Convert event start to user's timezone for comparison
            event_start_tz = event.start.astimezone(tz) if event.start.tzinfo else event.start.replace(tzinfo=pytz.UTC).astimezone(tz)
            if now <= event_start_tz <= end_date:
                upcoming.append(event)

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

    def persist_events_to_db(self, events: List[CalendarEvent]) -> List[int]:
        """
        Store events in database and return list of database IDs.

        Args:
            events: List of calendar events to persist

        Returns:
            List of database event IDs
        """
        from .database import db

        event_ids = []
        for event in events:
            try:
                event_id = db.store_calendar_event(
                    event_uid=event.uid,
                    summary=event.summary,
                    start_time=event.start,
                    end_time=event.end,
                    description=event.description,
                    location=event.location,
                    attendees=event.attendees,
                    is_all_day=event.is_all_day
                )
                event_ids.append(event_id)
            except Exception as e:
                logger.error(f"Could not persist event {event.summary}: {e}")
                continue

        return event_ids

    def format_events_for_llm_with_refs(self, events: List[CalendarEvent],
                                        user_timezone: str = 'UTC') -> tuple[str, List[int]]:
        """
        Format events for LLM with reference indices and persist to database.

        Args:
            events: List of calendar events
            user_timezone: User's timezone (e.g., 'America/New_York')

        Returns:
            Tuple of (formatted string with indices, list of database IDs)
        """
        if not events:
            return "No upcoming events found.", []

        # Persist events to database first
        event_ids = self.persist_events_to_db(events)

        # Get user's timezone
        try:
            tz = pytz.timezone(user_timezone)
        except:
            tz = pytz.UTC
            logger.warning(f"Invalid timezone {user_timezone}, using UTC")

        # Get current date in user's timezone for relative date calculation
        now = datetime.now(tz)
        today = now.date()

        lines = ["Here are your upcoming events (use [CALENDAR:N] to reference):"]

        current_date_label = None
        for i, event in enumerate(events):
            # Convert event times to user's timezone
            local_start = event.start.astimezone(tz) if event.start.tzinfo else event.start.replace(tzinfo=pytz.UTC).astimezone(tz)
            local_end = event.end.astimezone(tz) if event.end.tzinfo else event.end.replace(tzinfo=pytz.UTC).astimezone(tz)
            
            # Calculate relative date label
            event_date = local_start.date()
            days_diff = (event_date - today).days
            
            if days_diff == 0:
                date_label = "Today:"
            elif days_diff == 1:
                date_label = "Tomorrow:"
            elif days_diff == 2:
                date_label = "In 2 days:"
            elif days_diff < 7:
                date_label = f"In {days_diff} days:"
            else:
                date_label = None  # Don't add label for events more than a week away
            
            # Add date label if it's different from the previous event
            if date_label and date_label != current_date_label:
                lines.append(f"\n{date_label}")
                current_date_label = date_label
            elif not date_label:
                current_date_label = None

            if event.is_all_day:
                lines.append(f"[{i}] {event.summary} (All day on {local_start.strftime('%A, %B %d, %Y')})")
            else:
                lines.append(
                    f"[{i}] {event.summary} on {local_start.strftime('%A, %B %d at %I:%M %p')} "
                    f"to {local_end.strftime('%I:%M %p')}"
                )
                if event.location:
                    lines.append(f"    Location: {event.location}")
                if event.description:
                    # Truncate long descriptions
                    desc = event.description[:100] + "..." if len(event.description) > 100 else event.description
                    lines.append(f"    Details: {desc}")

        return "\n".join(lines), event_ids

    def check_health(self) -> bool:
        """Check if calendar can be fetched."""
        if not self.calendar_url:
            return False

        events, error = self.fetch_calendar()
        return error is None


# Global client instance
calendar_client = CalendarClient()
