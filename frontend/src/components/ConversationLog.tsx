import { useEffect, useState, useRef, useCallback } from 'react';
import {
  User,
  Bot,
  Clock,
  Phone,
  Trash2,
  Download,
  Search,
  RefreshCw,
  PhoneOff,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { formatTime, formatDate, setTimezone } from '../utils/timezone';
import { CalendarCard } from './CalendarCard';
import { EmailCard } from './EmailCard';
import { WeatherCard } from './WeatherCard';
import { TomTomCard } from './TomTomCard';
import { NoteCard } from './NoteCard';
import { EventModal } from './EventModal';
import { EmailModal } from './EmailModal';
import { WeatherModal } from './WeatherModal';
import { TomTomModal } from './TomTomModal';
import { NoteModal } from './NoteModal';
import { Message as WSMessage } from '../hooks/useWebSocket';

interface CalendarRef {
  ref_index: number;
  event: {
    id: number;
    event_uid: string;
    summary: string;
    start_time: string;
    end_time: string;
    description?: string;
    location?: string;
    attendees?: Array<{ email: string; name: string; status: string }>;
    is_all_day: boolean;
  };
}

interface EmailRef {
  ref_index: number;
  email: {
    id: number;
    message_id: string;
    subject: string;
    sender: string;
    date: string;
    body: string;
  };
}

interface WeatherRef {
  ref_index: number;
  weather: {
    id: number;
    location: string;
    country?: string;
    temperature: number;
    feels_like?: number;
    temp_min?: number;
    temp_max?: number;
    humidity?: number;
    pressure?: number;
    description: string;
    main: string;
    wind_speed?: number;
    wind_deg?: number;
    clouds?: number;
    visibility?: number;
    units: string;
    fetched_at?: string;
  };
}

interface TomTomRef {
  ref_index: number;
  tomtom: {
    id: number;
    data_type: 'directions' | 'traffic' | 'poi';
    query?: string;
    location?: string;
    origin?: string;
    destination?: string;
    distance_miles?: number;
    travel_time_minutes?: number;
    incident_count?: number;
    result_data?: any;
    fetched_at?: string;
  };
}

interface NoteRef {
  ref_index: number;
  note: {
    id: number;
    title: string;
    summary?: string | null;
    transcript: string;
    call_id?: string | null;
    created_at: string;
    updated_at: string;
  };
}

interface Message {
  id?: number;
  conversation_id?: number;
  role: string;
  content: string;
  timestamp: string;
  call_id?: string;
  calendar_refs?: CalendarRef[];
  email_refs?: EmailRef[];
  weather_refs?: WeatherRef[];
  tomtom_refs?: TomTomRef[];
  note_refs?: NoteRef[];
  model?: string;
}

interface Conversation {
  id: number;
  call_id: string;
  caller_id: string;
  started_at: string;
  answered_at?: string;
  ended_at?: string;
  duration_seconds: number;
  status: string;
  recording_url?: string;
}

interface ConversationLogProps {
  websocket: {
    messages: WSMessage[];
    clearMessages: () => void;
    isConnected: boolean;
  };
}

export function ConversationLog({ websocket }: ConversationLogProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [timezone, setTimezoneState] = useState<string>('UTC');

  // Modal state for calendar/email/weather/tomtom/note cards
  const [selectedEvent, setSelectedEvent] = useState<CalendarRef['event'] | null>(null);
  const [selectedEmail, setSelectedEmail] = useState<EmailRef['email'] | null>(null);
  const [selectedWeather, setSelectedWeather] = useState<WeatherRef['weather'] | null>(null);
  const [selectedTomTom, setSelectedTomTom] = useState<TomTomRef['tomtom'] | null>(null);
  const [selectedNote, setSelectedNote] = useState<NoteRef['note'] | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;


  // Fetch timezone from config
  useEffect(() => {
    async function fetchTimezone() {
      try {
        const res = await fetch('/api/config');
        const data = await res.json();
        const tz = data.timezone || 'UTC';
        setTimezoneState(tz);
        setTimezone(tz);
      } catch (err) {
        console.error('Failed to fetch timezone:', err);
      }
    }
    fetchTimezone();
  }, []);

  // Fetch conversations
  const fetchConversations = useCallback(async () => {
    try {
      setRefreshing(true);
      const res = await fetch('/api/conversations?limit=50');
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
    // Refresh conversations every 5 seconds
    const interval = setInterval(fetchConversations, 5000);
    return () => clearInterval(interval);
  }, [fetchConversations]);

  // Update durations for active conversations
  useEffect(() => {
    const interval = setInterval(() => {
      setConversations(prev => prev.map(conv => {
        if (conv.status === 'active' && !conv.ended_at) {
          // Use answered_at if available, otherwise started_at
          const startTime = conv.answered_at || conv.started_at;
          if (startTime) {
            const started = new Date(startTime).getTime();
            const now = Date.now();
            const duration = Math.max(0, Math.floor((now - started) / 1000));
            return { ...conv, duration_seconds: duration };
          }
        }
        return conv;
      }));
    }, 1000); // Update every second

    return () => clearInterval(interval);
  }, []);

  // Removed auto-scroll behavior - users can manually scroll

  // Listen for conversation updates via WebSocket
  useEffect(() => {
    if (!websocket.isConnected) {
      console.log('WebSocket not connected, waiting...');
      return;
    }

    // Wait for socket to be available
    const checkSocket = setInterval(() => {
      const socket = (window as any).socket;
      if (socket) {
        clearInterval(checkSocket);

        const handleConversationUpdate = (data: { conversation: Conversation }) => {
          console.log('Received conversation_update:', data);
          const updatedConv = data.conversation;
          setConversations(prev => {
            const existing = prev.find(c => c.id === updatedConv.id || c.call_id === updatedConv.call_id);
            if (existing) {
              // Update existing conversation
              return prev.map(c =>
                (c.id === updatedConv.id || c.call_id === updatedConv.call_id) ? updatedConv : c
              );
            } else {
              // Add new conversation at the top
              return [updatedConv, ...prev];
            }
          });

          // If this is the selected conversation, refresh messages
          if (selectedConv && (selectedConv.id === updatedConv.id || selectedConv.call_id === updatedConv.call_id)) {
            console.log('Selected conversation updated, refreshing messages');
            fetchMessages(selectedConv.call_id);
            // Also update the selected conversation object
            setSelectedConv(updatedConv);
          }
        };

        socket.on('conversation_update', handleConversationUpdate);
        console.log('Registered conversation_update listener');

        return () => {
          socket.off('conversation_update', handleConversationUpdate);
        };
      }
    }, 500);

    return () => clearInterval(checkSocket);
  }, [websocket.isConnected, selectedConv]);

  // Auto-refresh messages for active conversations every 3 seconds
  useEffect(() => {
    if (!selectedConv || selectedConv.status !== 'active') {
      return;
    }

    console.log('Setting up auto-refresh for active conversation:', selectedConv.call_id);
    const interval = setInterval(() => {
      console.log('Auto-refreshing messages for active conversation');
      fetchMessages(selectedConv.call_id);
    }, 3000); // Refresh every 3 seconds

    return () => clearInterval(interval);
  }, [selectedConv?.call_id, selectedConv?.status]);

  // Listen for new messages and update selected conversation
  useEffect(() => {
    if (!selectedConv) return;

    const relevantMessages = websocket.messages.filter(m =>
      m.callId === selectedConv.call_id
    );

    if (relevantMessages.length > 0) {
      console.log('Merging new messages for selected conversation:', relevantMessages);
      // Merge with existing messages, avoiding duplicates
      setMessages(prev => {
        const existingKeys = new Set(prev.map(m => `${m.timestamp}-${m.content.slice(0, 50)}`));
        const newMessages = relevantMessages
          .filter(m => !existingKeys.has(`${m.timestamp}-${m.content.slice(0, 50)}`))
          .map(m => ({
            role: m.role,
            content: m.content,
            timestamp: m.timestamp,
            call_id: m.callId,
            conversation_id: m.conversationId,
            model: m.model,
            calendar_refs: m.calendar_refs,
            email_refs: m.email_refs,
            weather_refs: m.weather_refs,
            tomtom_refs: m.tomtom_refs,
            note_refs: m.note_refs,
          }));

        if (newMessages.length > 0) {
          console.log('Adding new messages:', newMessages);
          const combined = [...prev, ...newMessages];
          // Sort by timestamp
          combined.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
          return combined;
        }
        return prev;
      });
    }
  }, [websocket.messages, selectedConv]);

  async function fetchMessages(callId: string) {
    try {
      const res = await fetch(`/api/conversations/${callId}`);
      const data = await res.json();
      setMessages(data.messages || []);
    } catch (err) {
      console.error('Failed to fetch messages:', err);
    }
  }

  async function selectConversation(conv: Conversation) {
    setSelectedConv(conv);
    await fetchMessages(conv.call_id);
    // Scroll to bottom after loading (only on initial load)
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  }

  function formatDuration(seconds: number): string {
    if (!seconds || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  // Clean message content by removing markers - no regex, just simple string replacement
  function cleanMessageContent(content: string): string {
    let cleaned = content;
    const markerPrefixes = ['[CALENDAR:', '[EMAIL:', '[WEATHER:', '[TOMTOM:'];
    
    // Remove all markers by finding each one and removing it
    let changed = true;
    while (changed) {
      const before = cleaned;
      
      for (const prefix of markerPrefixes) {
        const index = cleaned.indexOf(prefix);
        if (index !== -1) {
          const endIndex = cleaned.indexOf(']', index);
          if (endIndex !== -1) {
            cleaned = cleaned.slice(0, index) + cleaned.slice(endIndex + 1);
          }
        }
      }
      
      changed = cleaned !== before;
    }
    
    return cleaned.trim();
  }

  // Render attachments directly from refs arrays - no regex needed!
  function renderAttachments(
    calendarRefs: CalendarRef[] = [],
    emailRefs: EmailRef[] = [],
    weatherRefs: WeatherRef[] = [],
    tomtomRefs: TomTomRef[] = [],
    noteRefs: NoteRef[] = []
  ): React.ReactNode[] {
    const attachments: React.ReactNode[] = [];
    
    // Render calendar cards
    calendarRefs.forEach((ref, idx) => {
      attachments.push(
        <CalendarCard
          key={`calendar-${ref.ref_index}-${idx}`}
          event={ref.event}
          timezone={timezone}
          onClick={() => setSelectedEvent(ref.event)}
        />
      );
    });
    
    // Render email cards
    emailRefs.forEach((ref, idx) => {
      attachments.push(
        <EmailCard
          key={`email-${ref.ref_index}-${idx}`}
          email={ref.email}
          timezone={timezone}
          onClick={() => setSelectedEmail(ref.email)}
        />
      );
    });
    
    // Render weather cards
    weatherRefs.forEach((ref, idx) => {
      attachments.push(
        <WeatherCard
          key={`weather-${ref.ref_index}-${idx}`}
          weather={ref.weather}
          onClick={() => setSelectedWeather(ref.weather)}
        />
      );
    });
    
    // Render TomTom cards
    tomtomRefs.forEach((ref, idx) => {
      attachments.push(
        <TomTomCard
          key={`tomtom-${ref.ref_index}-${idx}`}
          tomtom={ref.tomtom}
          onClick={() => setSelectedTomTom(ref.tomtom)}
        />
      );
    });
    
    // Render note cards
    noteRefs.forEach((ref, idx) => {
      attachments.push(
        <NoteCard
          key={`note-${ref.ref_index}-${idx}`}
          note={ref.note}
          timezone={timezone}
          onClick={() => setSelectedNote(ref.note)}
        />
      );
    });

    return attachments;
  }

  function exportConversation() {
    if (!selectedConv || messages.length === 0) return;

    const text = messages.map(m =>
      `[${formatTime(m.timestamp)}] ${m.role.toUpperCase()}: ${m.content}`
    ).join('\n\n');

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${selectedConv.call_id.slice(0, 8)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const filteredConversations = conversations.filter(conv =>
    conv.caller_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    conv.call_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Pagination calculations
  const totalPages = Math.ceil(filteredConversations.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedConversations = filteredConversations.slice(startIndex, endIndex);

  // Reset to page 1 when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  // Combine stored messages with real-time messages
  const allMessages = selectedConv
    ? messages
    : websocket.messages.length > 0
      ? websocket.messages
        .map(m => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
          call_id: m.callId,
          conversation_id: m.conversationId,
          model: m.model,
          calendar_refs: m.calendar_refs,
          email_refs: m.email_refs,
          weather_refs: m.weather_refs,
          tomtom_refs: m.tomtom_refs,
          note_refs: m.note_refs,
        }))
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      : [];

  return (
    <div className="grid grid-cols-12 gap-4 min-h-full">
      {/* Conversation List */}
      <div className="col-span-4 glass rounded-xl flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-white">Conversations</h3>
            <button
              onClick={fetchConversations}
              disabled={refreshing}
              className="p-1.5 rounded-lg hover:bg-gray-700 transition-colors"
              title="Refresh conversations"
            >
              <RefreshCw className={`w-4 h-4 text-gray-400 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-green-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-2" style={{ scrollbarWidth: 'thin' }}>
          {/* Live conversation option */}
          <button
            onClick={() => {
              setSelectedConv(null);
            }}
            className={`w-full text-left p-3 rounded-lg transition-colors ${selectedConv === null
              ? 'bg-green-500/20 border border-green-500/30'
              : 'bg-gray-800/50 hover:bg-gray-800 border border-transparent'
              }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-green-400 status-dot" />
              <span className="font-medium text-green-400">Live Feed</span>
            </div>
            <p className="text-xs text-gray-400">
              Real-time messages from active calls
            </p>
          </button>

          {loading ? (
            <p className="text-center text-gray-500 py-8">Loading...</p>
          ) : filteredConversations.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No conversations found</p>
          ) : (
            paginatedConversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => selectConversation(conv)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${selectedConv?.id === conv.id
                  ? 'bg-blue-500/20 border border-blue-500/30'
                  : 'bg-gray-800/50 hover:bg-gray-800 border border-transparent'
                  }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-gray-200 truncate">
                    {conv.caller_id || 'Unknown Caller'}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${conv.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                    conv.status === 'active' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                    {conv.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDuration(conv.duration_seconds)}
                  </span>
                  <span className="truncate">{formatDate(conv.started_at, timezone)}</span>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Pagination Controls */}
        {filteredConversations.length > itemsPerPage && (
          <div className="p-3 border-t border-gray-700 flex items-center justify-between">
            <p className="text-xs text-gray-400">
              Showing {startIndex + 1}-{Math.min(endIndex, filteredConversations.length)} of {filteredConversations.length}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="p-1.5 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Previous page"
              >
                <ChevronLeft className="w-4 h-4 text-gray-400" />
              </button>
              <span className="text-xs text-gray-400 min-w-[60px] text-center">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="p-1.5 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Next page"
              >
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Message View */}
      <div className="col-span-8 glass rounded-xl flex flex-col">
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">
              {selectedConv ? `Call: ${selectedConv.call_id.slice(0, 8)}...` : 'Live Messages'}
            </h3>
            {selectedConv && (
              <p className="text-sm text-gray-400">
                From: {selectedConv.caller_id} • Duration: {formatDuration(selectedConv.duration_seconds)}
                {selectedConv.status === 'active' && ' (active)'}
                {selectedConv.answered_at && (
                  <span className="ml-2 text-xs text-gray-500">
                    • Answered: {formatTime(selectedConv.answered_at, timezone)}
                  </span>
                )}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {selectedConv && (
              <>
                <button
                  onClick={() => fetchMessages(selectedConv.call_id)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm text-gray-200 transition-colors"
                  title="Refresh messages"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
                <button
                  onClick={exportConversation}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm text-gray-200 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Export
                </button>
              </>
            )}
            {!selectedConv && (
              <button
                onClick={websocket.clearMessages}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm text-gray-200 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Active Call Controls */}
        {selectedConv && selectedConv.status === 'active' && (
          <div className="px-4 py-2 border-b border-gray-700 bg-gray-800/30 flex justify-end">
            <button
              onClick={async () => {
                try {
                  await fetch('/api/sip/hangup', { method: 'POST' });
                  // Status update will come via websocket
                } catch (err) {
                  console.error('Failed to hangup:', err);
                }
              }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 text-sm transition-colors"
            >
              <PhoneOff className="w-4 h-4" />
              End Call
            </button>
          </div>
        )}

        {/* Recording Player */}
        {selectedConv && selectedConv.recording_url && (
          <div className="px-4 py-2 border-b border-gray-700 bg-gray-800/30">
            <p className="text-xs text-gray-400 mb-1">Call Recording</p>
            <audio
              controls
              src={`/api${selectedConv.recording_url}`}
              className="w-full h-8"
              style={{ borderRadius: '0.5rem' }}
            />
          </div>
        )}

        <div
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto p-4 space-y-4"
          style={{
            scrollbarWidth: 'thin',
            overscrollBehavior: 'contain'
          }}
        >
          {allMessages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Phone className="w-12 h-12 mb-4 opacity-50" />
              <p>No messages yet</p>
              <p className="text-sm">Messages will appear here during calls</p>
            </div>
          ) : (
            <>
              {allMessages.map((msg, index) => {
                const msgKey = ('id' in msg && msg.id) ? msg.id : `${msg.timestamp}-${index}-${msg.content.slice(0, 20)}`;

                // Handle system messages (call answered, user hung up)
                if (msg.role === 'system') {
                  return (
                    <div key={msgKey} className="flex justify-center my-2">
                      <div className="bg-gray-700/50 border border-gray-600 rounded-lg px-4 py-2">
                        <p className="text-xs text-gray-400 text-center">
                          <Clock className="w-3 h-3 inline mr-1" />
                          {msg.content} • {formatTime(msg.timestamp, timezone)}
                        </p>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={msgKey}
                    className={`flex gap-3 log-entry ${msg.role === 'assistant' ? '' : 'flex-row-reverse'
                      }`}
                  >
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'assistant' ? 'bg-green-500/20' : 'bg-blue-500/20'
                      }`}>
                      {msg.role === 'assistant' ? (
                        <Bot className="w-4 h-4 text-green-400" />
                      ) : (
                        <User className="w-4 h-4 text-blue-400" />
                      )}
                    </div>
                    <div className={`max-w-[70%] ${msg.role === 'assistant' ? '' : 'text-right'}`}>
                      <div className={`rounded-2xl px-4 py-2 ${msg.role === 'assistant' ? 'message-assistant' : 'message-user'
                        }`}>
                        {/* Message Content */}
                        <div className="text-sm prose prose-sm max-w-none text-gray-100">
                          <p className="whitespace-pre-wrap">{cleanMessageContent(msg.content)}</p>
                        </div>

                        {/* Model Name */}
                        {msg.role === 'assistant' && msg.model && (
                          <div className="mt-1 text-xs text-gray-400 flex items-center gap-1">
                            <div className="w-1.5 h-1.5 rounded-full bg-blue-400/50"></div>
                            {msg.model}
                          </div>
                        )}
                      </div>

                      {/* Render attachments below the bubble */}
                      {(msg.calendar_refs?.length || msg.email_refs?.length || msg.weather_refs?.length || msg.tomtom_refs?.length || msg.note_refs?.length) ? (
                        <div className={`mt-2 flex flex-wrap gap-2 ${msg.role === 'assistant' ? 'justify-start' : 'justify-end'}`}>
                          {renderAttachments(msg.calendar_refs, msg.email_refs, msg.weather_refs, msg.tomtom_refs, msg.note_refs)}
                        </div>
                      ) : null}

                      <p className="text-xs text-gray-500 mt-1 px-2">
                        {formatTime(msg.timestamp, timezone)}
                      </p>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </div>

      {/* Modals for calendar events, emails, weather, tomtom, and notes */}
      {selectedEvent && (
        <EventModal
          event={selectedEvent}
          timezone={timezone}
          onClose={() => setSelectedEvent(null)}
        />
      )}

      {selectedEmail && (
        <EmailModal
          email={selectedEmail}
          timezone={timezone}
          onClose={() => setSelectedEmail(null)}
        />
      )}

      {selectedWeather && (
        <WeatherModal
          weather={selectedWeather}
          onClose={() => setSelectedWeather(null)}
        />
      )}

      {selectedTomTom && (
        <TomTomModal
          tomtom={selectedTomTom}
          onClose={() => setSelectedTomTom(null)}
        />
      )}

      {selectedNote && (
        <NoteModal
          note={{
            ...selectedNote,
            summary: selectedNote.summary ?? null,
            call_id: selectedNote.call_id ?? null,
          }}
          timezone={timezone}
          onClose={() => setSelectedNote(null)}
          onUpdate={async (id, title, summary, transcript) => {
            try {
              const response = await fetch(`/api/notes/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, summary, transcript }),
              });
              if (response.ok) {
                // Refresh messages to get updated note
                if (selectedConv) {
                  fetchMessages(selectedConv.call_id);
                }
              }
            } catch (error) {
              console.error('Failed to update note:', error);
            }
          }}
          onDelete={async (id) => {
            try {
              const response = await fetch(`/api/notes/${id}`, {
                method: 'DELETE',
              });
              if (response.ok) {
                setSelectedNote(null);
                // Refresh messages to remove deleted note
                if (selectedConv) {
                  fetchMessages(selectedConv.call_id);
                }
              }
            } catch (error) {
              console.error('Failed to delete note:', error);
            }
          }}
        />
      )}
    </div>
  );
}
