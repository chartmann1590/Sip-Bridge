import { Mail, Calendar as CalendarIcon } from 'lucide-react';
import { formatDate, formatTime } from '../utils/timezone';

interface EmailCardProps {
  email: {
    id: number;
    subject: string;
    sender: string;
    date: string;
  };
  timezone: string;
  onClick: () => void;
}

export function EmailCard({ email, timezone, onClick }: EmailCardProps) {


  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 px-3 py-2 mx-1 my-0.5 rounded-lg bg-green-500/20 border border-green-500/30 hover:bg-green-500/30 transition-all duration-200 text-sm group"
    >
      <Mail className="w-4 h-4 text-green-400 group-hover:text-green-300" />

      <div className="flex flex-col items-start text-left">
        <span className="text-green-100 font-medium leading-tight">{email.subject}</span>

        <div className="flex items-center gap-2 text-xs text-green-300/80">
          <span>From: {email.sender}</span>
        </div>

        <div className="flex items-center gap-1 text-xs text-green-300/70">
          <CalendarIcon className="w-3 h-3" />
          <span>
            {formatDate(email.date, timezone)} at {formatTime(email.date, timezone)}
          </span>
        </div>
      </div>
    </button>
  );
}
