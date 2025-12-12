/**
 * Timezone utility functions for formatting dates and times
 */

let currentTimezone: string = 'UTC';

/**
 * Set the current timezone
 */
export function setTimezone(timezone: string): void {
  currentTimezone = timezone || 'UTC';
}

/**
 * Get the current timezone
 */
export function getTimezone(): string {
  return currentTimezone;
}

/**
 * Format a timestamp to a time string in the current timezone
 */
export function formatTime(timestamp: string, timezone?: string): string {
  try {
    const tz = timezone || currentTimezone;
    return new Date(timestamp).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      timeZone: tz
    });
  } catch {
    return timestamp;
  }
}

/**
 * Format a timestamp to a date string in the current timezone
 */
export function formatDate(timestamp: string, timezone?: string): string {
  try {
    const tz = timezone || currentTimezone;
    // Use toLocaleString instead of toLocaleDateString to support time options
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: tz
    });
  } catch {
    return timestamp;
  }
}

/**
 * Format a timestamp to a full date/time string in the current timezone
 */
export function formatDateTime(timestamp: string, timezone?: string): string {
  try {
    const tz = timezone || currentTimezone;
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: tz
    });
  } catch {
    return timestamp;
  }
}

/**
 * Get current time in the current timezone
 */
export function getCurrentTime(timezone?: string): string {
  const tz = timezone || currentTimezone;
  return new Date().toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    timeZone: tz
  });
}
