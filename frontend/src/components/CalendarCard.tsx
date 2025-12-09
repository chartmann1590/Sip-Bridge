import { Calendar, Clock, MapPin } from 'lucide-react';
import { formatDate, formatTime } from '../utils/timezone';

interface CalendarCardProps {
  event: {
    id: number;
    summary: string;
    start_time: string;
    end_time: string;
    location?: string;
    is_all_day: boolean;
  };
  timezone: string;
  onClick: () => void;
}

export function CalendarCard({ event, timezone, onClick }: CalendarCardProps) {
  const startTime = new Date(event.start_time);


  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 px-3 py-2 mx-1 my-0.5 rounded-lg bg-blue-500/20 border border-blue-500/30 hover:bg-blue-500/30 transition-all duration-200 text-sm group"
    >
      <Calendar className="w-4 h-4 text-blue-400 group-hover:text-blue-300" />

      <div className="flex flex-col items-start text-left">
        <span className="text-blue-100 font-medium leading-tight">{event.summary}</span>

        <div className="flex items-center gap-2 text-xs text-blue-300/80">
          <Clock className="w-3 h-3" />
          {event.is_all_day ? (
            <span>{formatDate(startTime.toISOString(), timezone)}</span>
          ) : (
            <span>
              {formatDate(startTime.toISOString(), timezone)} at {formatTime(startTime.toISOString(), timezone)}
            </span>
          )}
        </div>

        {event.location && (
          <div className="flex items-center gap-1 text-xs text-blue-300/70">
            <MapPin className="w-3 h-3" />
            <span className="truncate max-w-[200px]">{event.location}</span>
          </div>
        )}
      </div>
    </button>
  );
}
