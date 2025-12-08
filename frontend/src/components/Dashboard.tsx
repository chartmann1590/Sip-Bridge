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
  XCircle,
  RefreshCw
} from 'lucide-react';
import { ServiceCard } from './StatusIndicator';
import { formatTime, getCurrentTime, setTimezone } from '../utils/timezone';

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
    const interval = setInterval(fetchHealth, 30000);
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
  
  function formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  }
  
  async function restartSip() {
    try {
      await fetch('/api/sip/restart', { method: 'POST' });
    } catch (err) {
      console.error('Failed to restart SIP:', err);
    }
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
      
      {/* Recent Logs */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Recent Activity</h3>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {websocket.logs.slice(0, 10).map((log, index) => (
            <div 
              key={index} 
              className={`log-entry flex items-start gap-3 p-2 rounded-lg ${
                log.level === 'error' ? 'bg-red-500/10' :
                log.level === 'warning' ? 'bg-amber-500/10' :
                'bg-gray-800/50'
              }`}
            >
              {log.level === 'error' ? (
                <XCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              ) : log.level === 'warning' ? (
                <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
              ) : (
                <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200">{log.event}</p>
                {log.details && (
                  <p className="text-xs text-gray-400 truncate">{log.details}</p>
                )}
              </div>
              <span className="text-xs text-gray-500 flex-shrink-0">
                {formatTime(log.timestamp, timezone)}
              </span>
            </div>
          ))}
          {websocket.logs.length === 0 && (
            <p className="text-center text-gray-500 py-4">No recent activity</p>
          )}
        </div>
      </div>
      
      {/* SIP Control */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-lg font-semibold text-white mb-4">SIP Control</h3>
        <div className="flex items-center gap-4">
          <button
            onClick={restartSip}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Restart SIP Client
          </button>
          <div className="text-sm text-gray-400">
            {websocket.sipStatus?.registered ? (
              <span className="text-green-400">Registered to PBX</span>
            ) : (
              <span className="text-red-400">Not Registered</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

