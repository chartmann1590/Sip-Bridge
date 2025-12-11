import { X, Calendar, Edit2, Trash2, Save } from 'lucide-react';
import { useState } from 'react';

interface Note {
  id: number;
  title: string;
  summary: string | null;
  transcript: string;
  call_id: string | null;
  created_at: string;
  updated_at: string;
}

interface NoteModalProps {
  note: Note;
  onClose: () => void;
  onUpdate: (id: number, title: string, summary: string, transcript: string) => void;
  onDelete: (id: number) => void;
}

export function NoteModal({ note, onClose, onUpdate, onDelete }: NoteModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(note.title);
  const [editedSummary, setEditedSummary] = useState(note.summary || '');
  const [editedTranscript, setEditedTranscript] = useState(note.transcript);

  const handleSave = () => {
    onUpdate(note.id, editedTitle, editedSummary, editedTranscript);
    setIsEditing(false);
  };

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete "${note.title}"?`)) {
      onDelete(note.id);
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="glass rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 glass border-b border-white/10 px-6 py-4 flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <div className="text-4xl mt-1">📝</div>
            <div className="flex-1">
              {isEditing ? (
                <input
                  type="text"
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                  className="w-full bg-gray-800/50 border border-white/20 rounded-lg px-3 py-2 text-xl font-bold text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              ) : (
                <h2 className="text-xl font-bold text-white">{note.title}</h2>
              )}
              <div className="flex items-center gap-2 mt-2 text-sm text-gray-400">
                <Calendar className="w-4 h-4" />
                <span>{new Date(note.created_at).toLocaleString()}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isEditing ? (
              <button
                onClick={handleSave}
                className="p-2 hover:bg-green-500/20 text-green-400 rounded-lg transition-colors"
                aria-label="Save changes"
              >
                <Save className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="p-2 hover:bg-blue-500/20 text-blue-400 rounded-lg transition-colors"
                aria-label="Edit note"
              >
                <Edit2 className="w-5 h-5" />
              </button>
            )}

            <button
              onClick={handleDelete}
              className="p-2 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
              aria-label="Delete note"
            >
              <Trash2 className="w-5 h-5" />
            </button>

            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              aria-label="Close modal"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-6">
          {/* Summary */}
          {(note.summary || isEditing) && (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-red-400 mb-3">
                <span>Summary</span>
              </div>
              <div className="pl-6">
                {isEditing ? (
                  <textarea
                    value={editedSummary}
                    onChange={(e) => setEditedSummary(e.target.value)}
                    rows={3}
                    className="w-full bg-gray-800/50 border border-white/20 rounded-lg p-3 text-gray-300 focus:outline-none focus:ring-2 focus:ring-red-500"
                    placeholder="Enter summary..."
                  />
                ) : (
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="text-gray-300">{note.summary}</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Transcript */}
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-red-400 mb-3">
              <span>Transcript</span>
            </div>
            <div className="pl-6">
              {isEditing ? (
                <textarea
                  value={editedTranscript}
                  onChange={(e) => setEditedTranscript(e.target.value)}
                  rows={15}
                  className="w-full bg-gray-800/50 border border-white/20 rounded-lg p-3 text-gray-300 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-red-500 whitespace-pre-wrap"
                />
              ) : (
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                    {note.transcript}
                  </pre>
                </div>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="text-xs text-gray-500 text-center pt-2 border-t border-white/10">
            Last updated: {new Date(note.updated_at).toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
}
