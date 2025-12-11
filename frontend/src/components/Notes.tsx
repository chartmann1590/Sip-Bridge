import { useEffect, useState } from 'react';
import { FileText, Plus, Search, Clock, Trash2 } from 'lucide-react';
import { NoteModal } from './NoteModal';
import { formatDate } from '../utils/timezone';

interface Note {
  id: number;
  title: string;
  summary: string | null;
  transcript: string;
  call_id: string | null;
  created_at: string;
  updated_at: string;
}

export function Notes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);

  useEffect(() => {
    fetchNotes();

    // WebSocket listener for note updates
    const handleNoteCreated = (event: CustomEvent) => {
      const note = event.detail;
      setNotes((prev) => [note, ...prev]);
    };

    const handleNoteUpdated = (event: CustomEvent) => {
      const note = event.detail;
      setNotes((prev) =>
        prev.map((n) => (n.id === note.id ? note : n))
      );
    };

    const handleNoteDeleted = (event: CustomEvent) => {
      const { id } = event.detail;
      setNotes((prev) => prev.filter((n) => n.id !== id));
    };

    window.addEventListener('note_created', handleNoteCreated as EventListener);
    window.addEventListener('note_updated', handleNoteUpdated as EventListener);
    window.addEventListener('note_deleted', handleNoteDeleted as EventListener);

    return () => {
      window.removeEventListener('note_created', handleNoteCreated as EventListener);
      window.removeEventListener('note_updated', handleNoteUpdated as EventListener);
      window.removeEventListener('note_deleted', handleNoteDeleted as EventListener);
    };
  }, []);

  const fetchNotes = async () => {
    try {
      const response = await fetch('/api/notes');
      const data = await response.json();
      setNotes(data.notes || []);
    } catch (error) {
      console.error('Failed to fetch notes:', error);
    }
  };

  const createNote = async () => {
    const title = prompt('Enter note title:');
    if (!title) return;

    const transcript = prompt('Enter note content:');
    if (!transcript) return;

    try {
      const response = await fetch('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, transcript }),
      });

      if (response.ok) {
        fetchNotes();
      }
    } catch (error) {
      console.error('Failed to create note:', error);
    }
  };

  const updateNote = async (id: number, title: string, summary: string, transcript: string) => {
    try {
      const response = await fetch(`/api/notes/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, summary, transcript }),
      });

      if (response.ok) {
        fetchNotes();
      }
    } catch (error) {
      console.error('Failed to update note:', error);
    }
  };

  const deleteNote = async (id: number) => {
    try {
      const response = await fetch(`/api/notes/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchNotes();
      }
    } catch (error) {
      console.error('Failed to delete note:', error);
    }
  };

  const filteredNotes = notes.filter(
    (note) =>
      note.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      note.transcript.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (note.summary && note.summary.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6" />
            Notes
          </h2>
          <p className="text-gray-400 mt-1">
            Voice notes captured during calls
          </p>
        </div>

        <button
          onClick={createNote}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Note
        </button>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search notes..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500"
        />
      </div>

      {/* Notes Grid */}
      {filteredNotes.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">
            {searchQuery
              ? 'No notes found matching your search'
              : 'No notes yet. Say "start notes" during a call to create one.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredNotes.map((note) => (
            <div
              key={note.id}
              className="glass rounded-lg p-4 hover:bg-white/5 cursor-pointer transition-colors"
              onClick={() => setSelectedNote(note)}
            >
              {/* Note Header */}
              <div className="flex items-start justify-between mb-3">
                <h3 className="text-lg font-semibold text-white line-clamp-1 flex-1">
                  {note.title}
                </h3>
                <FileText className="w-5 h-5 text-red-400 flex-shrink-0 ml-2" />
              </div>

              {/* Summary */}
              {note.summary && (
                <p className="text-sm text-gray-300 mb-3 line-clamp-2">
                  {note.summary}
                </p>
              )}

              {/* Transcript Preview */}
              <div className="bg-gray-800/30 rounded p-2 mb-3">
                <pre className="text-xs text-gray-400 font-mono line-clamp-3 whitespace-pre-wrap">
                  {note.transcript}
                </pre>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between text-xs text-gray-500">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{formatDate(note.created_at)}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`Delete "${note.title}"?`)) {
                      deleteNote(note.id);
                    }
                  }}
                  className="p-1 hover:bg-red-500/20 text-red-400 rounded transition-colors"
                  aria-label="Delete note"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Note Modal */}
      {selectedNote && (
        <NoteModal
          note={selectedNote}
          onClose={() => setSelectedNote(null)}
          onUpdate={updateNote}
          onDelete={deleteNote}
        />
      )}
    </div>
  );
}
