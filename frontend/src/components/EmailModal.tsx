import { X, Mail, Calendar, User } from 'lucide-react';
import { formatDate, formatTime } from '../utils/timezone';

interface EmailModalProps {
  email: {
    id: number;
    message_id: string;
    subject: string;
    sender: string;
    date: string;
    body: string;
  };
  timezone: string;
  onClose: () => void;
}

export function EmailModal({ email, timezone, onClose }: EmailModalProps) {


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
            <Mail className="w-6 h-6 text-green-400 mt-1" />
            <div className="flex-1">
              <h2 className="text-xl font-bold text-white">{email.subject}</h2>

              <div className="mt-3 space-y-1">
                <div className="flex items-center gap-2 text-sm text-gray-300">
                  <User className="w-4 h-4" />
                  <span className="font-medium">From:</span>
                  <span>{email.sender}</span>
                </div>

                <div className="flex items-center gap-2 text-sm text-gray-300">
                  <Calendar className="w-4 h-4" />
                  <span className="font-medium">Date:</span>
                  <span>
                    {formatDate(email.date, timezone)} at {formatTime(email.date, timezone)}
                  </span>
                </div>
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
        <div className="px-6 py-4">
          <div className="text-sm font-semibold text-green-400 mb-2">Message</div>
          <div className="pl-6 text-gray-200 bg-gray-900/50 rounded-lg p-4 whitespace-pre-wrap break-words font-mono text-sm">
            {email.body}
          </div>
        </div>
      </div>
    </div>
  );
}
