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
    // Ensure timestamp is treated as UTC if it doesn't have timezone info
    let dateStr = timestamp;
    if (!timestamp.includes('Z') && !timestamp.includes('+') && !timestamp.includes('-', 10)) {
      // No timezone indicator, append Z to force UTC interpretation
      dateStr = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
    }
    const date = new Date(dateStr);
    console.log(`formatDate: input="${timestamp}", normalized="${dateStr}", timezone="${tz}", parsed=${date.toISOString()}`);
    const result = date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: tz
    });
    console.log(`formatDate: result="${result}"`);
    return result;
  } catch (error) {
    console.error('formatDate error:', error, 'timestamp:', timestamp, 'timezone:', timezone);
    return timestamp;
  }
}

/**
 * Format a timestamp to a full date/time string in the current timezone
 */
export function formatDateTime(timestamp: string, timezone?: string): string {
  try {
    const tz = timezone || currentTimezone;
    // Ensure timestamp is treated as UTC if it doesn't have timezone info
    let dateStr = timestamp;
    if (!timestamp.includes('Z') && !timestamp.includes('+') && !timestamp.includes('-', 10)) {
      // No timezone indicator, append Z to force UTC interpretation
      dateStr = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
    }
    const date = new Date(dateStr);
    console.log(`formatDateTime: input="${timestamp}", normalized="${dateStr}", timezone="${tz}", parsed=${date.toISOString()}`);
    const result = date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: tz
    });
    console.log(`formatDateTime: result="${result}"`);
    return result;
  } catch (error) {
    console.error('formatDateTime error:', error, 'timestamp:', timestamp, 'timezone:', timezone);
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
