import { Calendar } from 'lucide-react';
import { formatDate, formatTime } from '../utils/timezone';

interface NoteCardProps {
  note: {
    id: number;
    title: string;
    summary?: string | null;
    created_at: string;
  };
  timezone: string;
  onClick: () => void;
}

export function NoteCard({ note, timezone, onClick }: NoteCardProps) {

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 px-3 py-2 mx-1 my-0.5 rounded-lg bg-purple-500/20 border border-purple-500/30 hover:bg-purple-500/30 transition-all duration-200 text-sm group"
    >
      <div className="text-2xl">📝</div>

      <div className="flex flex-col items-start text-left">
        <span className="text-purple-100 font-medium leading-tight">
          {note.title}
        </span>

        {note.summary && (
          <div className="text-xs text-purple-300/80 mt-0.5 line-clamp-2 max-w-[200px]">
            {note.summary}
          </div>
        )}

        <div className="flex items-center gap-1 text-xs text-purple-300/70 mt-0.5">
          <Calendar className="w-3 h-3" />
          <span>
            {formatDate(note.created_at, timezone)} at {formatTime(note.created_at, timezone)}
          </span>
        </div>
      </div>
    </button>
  );
}


