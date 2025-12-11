import { useEffect, useState } from 'react';
import {
  Phone,
  Mic,
  MessageSquare,
  Volume2,
  Database,
  Wifi,
  Clock,
  PhoneCall,
  PhoneOff,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Calendar,
  Mail,
  Cloud,
  Map,
  FileText
} from 'lucide-react';
import { ServiceCard } from './StatusIndicator';
import { formatTime, getCurrentTime, setTimezone } from '../utils/timezone';
import { ServiceInfoModal, serviceInfoMap } from './ServiceInfoModal';

interface DashboardProps {
  websocket: {
    isConnected: boolean;
    callStatus: {
      status: 'idle' | 'ringing' | 'connected' | 'ended';
      callId?: string;
      callerId?: string;
    };
    messages: Array<{
      role: string;
      content: string;
      timestamp: string;
    }>;
    logs: Array<{
      level: string;
      event: string;
      details?: string;
      timestamp: string;
    }>;
    sipStatus: {
      registered: boolean;
      details?: Record<string, unknown>;
    } | null;
    healthStatus: {
      services: {
        api: boolean;
        database: boolean;
        groq: boolean;
        ollama: boolean;
        tts: boolean;
        sip: boolean;
      };
    } | null;
  };
}

export function Dashboard({ websocket }: DashboardProps) {
  const [health, setHealth] = useState<Record<string, boolean>>({});
  const [, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalCalls: 0,
    activeTime: '0:00',
    messagesProcessed: 0,
  });
  const [timezone, setTimezoneState] = useState<string>('UTC');
  const [currentTime, setCurrentTime] = useState<string>('');
  const [recentCalls, setRecentCalls] = useState<Array<{
    id: number;
    call_id: string;
    caller_id: string;
    started_at: string;
    ended_at: string | null;
    duration_seconds: number;
    status: string;
  }>>([]);
  const [selectedServiceInfo, setSelectedServiceInfo] = useState<typeof serviceInfoMap[keyof typeof serviceInfoMap] | null>(null);
  const [serviceStatuses, setServiceStatuses] = useState<Record<string, boolean>>({
    calendar: false,
    email: false,
    weather: false,
    tomtom: false,
    notes: false,
  });
  
  // Fetch timezone and service statuses from config
  useEffect(() => {
    async function fetchConfig() {
      try {
        const res = await fetch('/api/config');
        const data = await res.json();
        const tz = data.timezone || 'UTC';
        setTimezoneState(tz);
        setTimezone(tz);

        // Update service statuses based on API keys
        setServiceStatuses({
          calendar: !!data.calendar_url,
          email: data.has_email_password ?? false,
          weather: data.has_weather_key ?? false,
          tomtom: data.has_tomtom_key ?? false,
          notes: true, // Notes system is always available (no API key needed)
        });
      } catch (err) {
        console.error('Failed to fetch config:', err);
      }
    }
    fetchConfig();
  }, []);
  
  // Update current time display
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(getCurrentTime(timezone));
    }, 1000);
    return () => clearInterval(interval);
  }, [timezone]);
  
  useEffect(() => {
    fetchHealth();
    fetchStats();
    fetchRecentCalls();
    const interval = setInterval(() => {
      fetchHealth();
      fetchRecentCalls();
    }, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, []);
  
  useEffect(() => {
    if (websocket.healthStatus) {
      setHealth(websocket.healthStatus.services);
    }
  }, [websocket.healthStatus]);
  
  async function fetchHealth() {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      setHealth(data.services);
    } catch (err) {
      console.error('Failed to fetch health:', err);
    } finally {
      setLoading(false);
    }
  }
  
  async function fetchStats() {
    try {
      const res = await fetch('/api/conversations?limit=1000');
      const data = await res.json();
      setStats({
        totalCalls: data.conversations?.length || 0,
        activeTime: formatDuration(data.conversations?.reduce((acc: number, c: { duration_seconds?: number }) =>
          acc + (c.duration_seconds || 0), 0) || 0),
        messagesProcessed: websocket.messages.length,
      });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }

  async function fetchRecentCalls() {
    try {
      const res = await fetch('/api/conversations?limit=10');
      const data = await res.json();
      setRecentCalls(data.conversations || []);
    } catch (err) {
      console.error('Failed to fetch recent calls:', err);
    }
  }
  
  function formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  }
  
  async function hangupCall() {
    try {
      await fetch('/api/sip/hangup', { method: 'POST' });
    } catch (err) {
      console.error('Failed to hangup:', err);
    }
  }
  
  const allServicesHealthy = Object.values(health).every(Boolean);
  
  return (
    <div className="space-y-6">
      {/* Status Banner */}
      <div className={`glass rounded-xl p-4 ${
        allServicesHealthy ? 'border-green-500/30' : 'border-amber-500/30'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {allServicesHealthy ? (
              <CheckCircle className="w-6 h-6 text-green-400" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-amber-400" />
            )}
            <div>
              <h2 className="text-lg font-semibold text-white">
                {allServicesHealthy ? 'All Systems Operational' : 'Some Services Degraded'}
              </h2>
              <p className="text-sm text-gray-400">
                Last checked: {currentTime || getCurrentTime(timezone)}
              </p>
            </div>
          </div>
          <button
            onClick={fetchHealth}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm text-gray-200 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>
      
      {/* Call Status Card */}
      <div className={`glass rounded-xl p-6 ${
        websocket.callStatus.status === 'connected' ? 'border-green-500/30 glow-green' :
        websocket.callStatus.status === 'ringing' ? 'border-amber-500/30 glow-amber' :
        'border-gray-700'
      }`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Phone className="w-5 h-5" />
            Current Call Status
          </h3>
          {websocket.callStatus.status === 'connected' && (
            <button
              onClick={hangupCall}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 text-sm transition-colors"
            >
              <PhoneOff className="w-4 h-4" />
              Hang Up
            </button>
          )}
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 rounded-lg bg-gray-800/50">
            <div className={`inline-flex p-3 rounded-full mb-2 ${
              websocket.callStatus.status === 'connected' ? 'bg-green-500/20' :
              websocket.callStatus.status === 'ringing' ? 'bg-amber-500/20' :
              'bg-gray-700'
            }`}>
              {websocket.callStatus.status === 'connected' ? (
                <PhoneCall className="w-6 h-6 text-green-400" />
              ) : websocket.callStatus.status === 'ringing' ? (
                <Phone className="w-6 h-6 text-amber-400 animate-pulse" />
              ) : (
                <PhoneOff className="w-6 h-6 text-gray-400" />
              )}
            </div>
            <p className="text-sm text-gray-400">Status</p>
            <p className={`font-semibold ${
              websocket.callStatus.status === 'connected' ? 'text-green-400' :
              websocket.callStatus.status === 'ringing' ? 'text-amber-400' :
              'text-gray-300'
            }`}>
              {websocket.callStatus.status === 'idle' ? 'No Active Call' :
               websocket.callStatus.status.charAt(0).toUpperCase() + websocket.callStatus.status.slice(1)}
            </p>
          </div>
          
          <div className="text-center p-4 rounded-lg bg-gray-800/50">
            <div className="inline-flex p-3 rounded-full mb-2 bg-gray-700">
              <Wifi className="w-6 h-6 text-blue-400" />
            </div>
            <p className="text-sm text-gray-400">Caller ID</p>
            <p className="font-semibold text-gray-300 truncate">
              {websocket.callStatus.callerId || '—'}
            </p>
          </div>
          
          <div className="text-center p-4 rounded-lg bg-gray-800/50">
            <div className="inline-flex p-3 rounded-full mb-2 bg-gray-700">
              <Clock className="w-6 h-6 text-purple-400" />
            </div>
            <p className="text-sm text-gray-400">Call ID</p>
            <p className="font-semibold text-gray-300 truncate text-xs">
              {websocket.callStatus.callId?.slice(0, 8) || '—'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Services Grid */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">Services</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <ServiceCard
            name="SIP Client"
            status={health.sip ?? false}
            description="VoIP connection to PBX"
            icon={<Phone className={`w-5 h-5 ${health.sip ? 'text-green-400' : 'text-red-400'}`} />}
          />
          <ServiceCard
            name="Groq STT"
            status={health.groq ?? false}
            description="Speech-to-text transcription"
            icon={<Mic className={`w-5 h-5 ${health.groq ? 'text-green-400' : 'text-red-400'}`} />}
          />
          <ServiceCard
            name="Ollama"
            status={health.ollama ?? false}
            description="Local LLM for AI responses"
            icon={<MessageSquare className={`w-5 h-5 ${health.ollama ? 'text-green-400' : 'text-red-400'}`} />}
          />
          <ServiceCard
            name="TTS Service"
            status={health.tts ?? false}
            description="Text-to-speech synthesis"
            icon={<Volume2 className={`w-5 h-5 ${health.tts ? 'text-green-400' : 'text-red-400'}`} />}
          />
          <ServiceCard
            name="Database"
            status={health.database ?? false}
            description="Local data storage"
            icon={<Database className={`w-5 h-5 ${health.database ? 'text-green-400' : 'text-red-400'}`} />}
          />
          <ServiceCard
            name="API Server"
            status={health.api ?? false}
            description="Web interface backend"
            icon={<Wifi className={`w-5 h-5 ${health.api ? 'text-green-400' : 'text-red-400'}`} />}
          />
        </div>
      </div>

      {/* AI Integrations */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">AI Integrations</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            onClick={() => setSelectedServiceInfo({ ...serviceInfoMap.calendar, status: serviceStatuses.calendar })}
            className="glass rounded-xl p-4 hover:bg-white/5 transition-all duration-200 text-left group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`p-2 rounded-lg ${serviceStatuses.calendar ? 'bg-indigo-500/20' : 'bg-gray-700'}`}>
                <Calendar className={`w-5 h-5 ${serviceStatuses.calendar ? 'text-indigo-400' : 'text-gray-500'}`} />
              </div>
              <div className={`px-2 py-1 rounded text-xs font-semibold ${
                serviceStatuses.calendar
                  ? 'bg-green-500/20 text-green-300'
                  : 'bg-gray-700 text-gray-400'
              }`}>
                {serviceStatuses.calendar ? 'Active' : 'Inactive'}
              </div>
            </div>
            <h4 className="font-semibold text-white mb-1 group-hover:text-indigo-300 transition-colors">Calendar</h4>
            <p className="text-xs text-gray-400">Access your schedule and events</p>
          </button>

          <button
            onClick={() => setSelectedServiceInfo({ ...serviceInfoMap.email, status: serviceStatuses.email })}
            className="glass rounded-xl p-4 hover:bg-white/5 transition-all duration-200 text-left group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`p-2 rounded-lg ${serviceStatuses.email ? 'bg-blue-500/20' : 'bg-gray-700'}`}>
                <Mail className={`w-5 h-5 ${serviceStatuses.email ? 'text-blue-400' : 'text-gray-500'}`} />
              </div>
              <div className={`px-2 py-1 rounded text-xs font-semibold ${
                serviceStatuses.email
                  ? 'bg-green-500/20 text-green-300'
                  : 'bg-gray-700 text-gray-400'
              }`}>
                {serviceStatuses.email ? 'Active' : 'Inactive'}
              </div>
            </div>
            <h4 className="font-semibold text-white mb-1 group-hover:text-blue-300 transition-colors">Email</h4>
            <p className="text-xs text-gray-400">Check inbox and messages</p>
          </button>

          <button
            onClick={() => setSelectedServiceInfo({ ...serviceInfoMap.weather, status: serviceStatuses.weather })}
            className="glass rounded-xl p-4 hover:bg-white/5 transition-all duration-200 text-left group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`p-2 rounded-lg ${serviceStatuses.weather ? 'bg-cyan-500/20' : 'bg-gray-700'}`}>
                <Cloud className={`w-5 h-5 ${serviceStatuses.weather ? 'text-cyan-400' : 'text-gray-500'}`} />
              </div>
              <div className={`px-2 py-1 rounded text-xs font-semibold ${
                serviceStatuses.weather
                  ? 'bg-green-500/20 text-green-300'
                  : 'bg-gray-700 text-gray-400'
              }`}>
                {serviceStatuses.weather ? 'Active' : 'Inactive'}
              </div>
            </div>
            <h4 className="font-semibold text-white mb-1 group-hover:text-cyan-300 transition-colors">Weather</h4>
            <p className="text-xs text-gray-400">Get weather information</p>
          </button>

          <button
            onClick={() => setSelectedServiceInfo({ ...serviceInfoMap.tomtom, status: serviceStatuses.tomtom })}
            className="glass rounded-xl p-4 hover:bg-white/5 transition-all duration-200 text-left group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`p-2 rounded-lg ${serviceStatuses.tomtom ? 'bg-red-500/20' : 'bg-gray-700'}`}>
                <Map className={`w-5 h-5 ${serviceStatuses.tomtom ? 'text-red-400' : 'text-gray-500'}`} />
              </div>
              <div className={`px-2 py-1 rounded text-xs font-semibold ${
                serviceStatuses.tomtom
                  ? 'bg-green-500/20 text-green-300'
                  : 'bg-gray-700 text-gray-400'
              }`}>
                {serviceStatuses.tomtom ? 'Active' : 'Inactive'}
              </div>
            </div>
            <h4 className="font-semibold text-white mb-1 group-hover:text-red-300 transition-colors">TomTom Maps</h4>
            <p className="text-xs text-gray-400">Directions, traffic & POI</p>
          </button>

          <button
            onClick={() => setSelectedServiceInfo({ ...serviceInfoMap.notes, status: serviceStatuses.notes })}
            className="glass rounded-xl p-4 hover:bg-white/5 transition-all duration-200 text-left group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`p-2 rounded-lg ${serviceStatuses.notes ? 'bg-purple-500/20' : 'bg-gray-700'}`}>
                <FileText className={`w-5 h-5 ${serviceStatuses.notes ? 'text-purple-400' : 'text-gray-500'}`} />
              </div>
              <div className={`px-2 py-1 rounded text-xs font-semibold ${
                serviceStatuses.notes
                  ? 'bg-green-500/20 text-green-300'
                  : 'bg-gray-700 text-gray-400'
              }`}>
                {serviceStatuses.notes ? 'Active' : 'Inactive'}
              </div>
            </div>
            <h4 className="font-semibold text-white mb-1 group-hover:text-purple-300 transition-colors">Notes</h4>
            <p className="text-xs text-gray-400">Voice notes with AI summaries</p>
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-green-400">{stats.totalCalls}</p>
          <p className="text-sm text-gray-400">Total Calls</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-blue-400">{stats.activeTime}</p>
          <p className="text-sm text-gray-400">Total Duration</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-purple-400">{websocket.messages.length}</p>
          <p className="text-sm text-gray-400">Messages</p>
        </div>
      </div>
      
      {/* Recent Call Activity */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Phone className="w-5 h-5" />
          Recent Call Activity
        </h3>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {recentCalls.map((call) => (
            <div
              key={call.id}
              className={`flex items-center gap-4 p-3 rounded-lg transition-colors ${
                call.status === 'active'
                  ? 'bg-green-500/10 border border-green-500/30'
                  : 'bg-gray-800/50 hover:bg-gray-800'
              }`}
            >
              <div className={`p-2 rounded-full ${
                call.status === 'active' ? 'bg-green-500/20' : 'bg-gray-700'
              }`}>
                {call.status === 'active' ? (
                  <PhoneCall className="w-5 h-5 text-green-400" />
                ) : (
                  <PhoneOff className="w-5 h-5 text-gray-400" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-gray-200">
                    {call.caller_id || 'Unknown'}
                  </p>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                    call.status === 'active'
                      ? 'bg-green-500/20 text-green-400'
                      : call.status === 'completed'
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'bg-gray-700 text-gray-400'
                  }`}>
                    {call.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <p className="text-xs text-gray-400">
                    {formatTime(call.started_at, timezone)}
                  </p>
                  {call.duration_seconds > 0 && (
                    <>
                      <span className="text-gray-600">•</span>
                      <p className="text-xs text-gray-400">
                        Duration: {formatDuration(call.duration_seconds)}
                      </p>
                    </>
                  )}
                </div>
              </div>

              <div className="text-right flex-shrink-0">
                <p className="text-xs text-gray-500 font-mono">
                  {call.call_id.slice(0, 8)}
                </p>
              </div>
            </div>
          ))}
          {recentCalls.length === 0 && (
            <div className="text-center py-8">
              <PhoneOff className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No recent calls</p>
              <p className="text-xs text-gray-600 mt-1">Calls will appear here once they start coming in</p>
            </div>
          )}
        </div>
      </div>

      {/* Service Info Modal */}
      {selectedServiceInfo && (
        <ServiceInfoModal
          service={selectedServiceInfo}
          onClose={() => setSelectedServiceInfo(null)}
        />
      )}
    </div>
  );
}

