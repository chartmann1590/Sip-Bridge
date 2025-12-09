import { X, Calendar, Clock, MapPin, Users } from 'lucide-react';
import { formatDate, formatTime } from '../utils/timezone';

interface EventModalProps {
  event: {
    id: number;
    summary: string;
    start_time: string;
    end_time: string;
    description?: string;
    location?: string;
    attendees?: Array<{
      email: string;
      name: string;
      status: string;
    }>;
    is_all_day: boolean;
  };
  timezone: string;
  onClose: () => void;
}

export function EventModal({ event, timezone, onClose }: EventModalProps) {


  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="glass rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 glass border-b border-white/10 px-6 py-4 flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <Calendar className="w-6 h-6 text-blue-400 mt-1" />
            <div className="flex-1">
              <h2 className="text-xl font-bold text-white">{event.summary}</h2>
              <div className="flex items-center gap-2 mt-2 text-sm text-gray-300">
                <Clock className="w-4 h-4" />
                {event.is_all_day ? (
                  <span>All day on {formatDate(event.start_time, timezone)}</span>
                ) : (
                  <span>
                    {formatDate(event.start_time, timezone)} at {formatTime(event.start_time, timezone)} -{' '}
                    {formatTime(event.end_time, timezone)}
                  </span>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-6">
          {/* Location */}
          {event.location && (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-blue-400 mb-2">
                <MapPin className="w-4 h-4" />
                <span>Location</span>
              </div>
              <div className="pl-6 text-gray-200">{event.location}</div>
            </div>
          )}

          {/* Attendees */}
          {event.attendees && event.attendees.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-blue-400 mb-2">
                <Users className="w-4 h-4" />
                <span>Attendees ({event.attendees.length})</span>
              </div>
              <div className="pl-6 space-y-2">
                {event.attendees.map((attendee, idx) => (
                  <div key={idx} className="flex items-center justify-between text-sm">
                    <div>
                      <div className="text-gray-200">
                        {attendee.name || attendee.email}
                      </div>
                      {attendee.name && (
                        <div className="text-xs text-gray-400">{attendee.email}</div>
                      )}
                    </div>
                    <span className="text-xs px-2 py-1 rounded bg-gray-700/50 text-gray-300">
                      {attendee.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          {event.description && (
            <div>
              <div className="text-sm font-semibold text-blue-400 mb-2">Description</div>
              <div className="pl-6 text-gray-200 bg-gray-900/50 rounded-lg p-4 whitespace-pre-wrap break-words font-mono text-sm">
                {event.description}
              </div>
            </div>
          )}

          {!event.location && !event.attendees?.length && !event.description && (
            <div className="text-center text-gray-400 py-8">
              No additional details available for this event.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
