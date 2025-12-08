import { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { Dashboard } from './components/Dashboard';
import { ConversationLog } from './components/ConversationLog';
import { Settings } from './components/Settings';
import { Phone, MessageSquare, Settings as SettingsIcon, Activity } from 'lucide-react';
import { getCurrentTime, setTimezone } from './utils/timezone';

type TabType = 'dashboard' | 'conversations' | 'settings';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const websocket = useWebSocket();
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
    
    // Refresh timezone when settings tab is active (in case user changed it)
    const interval = setInterval(() => {
      if (activeTab === 'settings') {
        fetchTimezone();
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [activeTab]);
  
  // Update current time display
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(getCurrentTime(timezone));
    }, 1000);
    return () => clearInterval(interval);
  }, [timezone]);
  
  const tabs = [
    { id: 'dashboard' as TabType, label: 'Dashboard', icon: Activity },
    { id: 'conversations' as TabType, label: 'Conversations', icon: MessageSquare },
    { id: 'settings' as TabType, label: 'Settings', icon: SettingsIcon },
  ];
  
  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="glass border-b border-gray-800 flex-shrink-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${websocket.sipStatus?.registered ? 'bg-green-500/20 glow-green' : 'bg-gray-700'}`}>
                <Phone className={`w-6 h-6 ${websocket.sipStatus?.registered ? 'text-green-400' : 'text-gray-400'}`} />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-white">SIP AI Bridge</h1>
                <p className="text-xs text-gray-400">Voice-to-AI Gateway</p>
              </div>
            </div>
            
            {/* Connection Status */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${websocket.isConnected ? 'bg-green-400 status-dot' : 'bg-red-400'}`} />
                <span className="text-sm text-gray-400">
                  {websocket.isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              {websocket.callStatus.status !== 'idle' && (
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
                  websocket.callStatus.status === 'connected' ? 'bg-green-500/20 call-active' :
                  websocket.callStatus.status === 'ringing' ? 'bg-amber-500/20' : 'bg-gray-700'
                }`}>
                  <Phone className={`w-4 h-4 ${
                    websocket.callStatus.status === 'connected' ? 'text-green-400' :
                    websocket.callStatus.status === 'ringing' ? 'text-amber-400' : 'text-gray-400'
                  }`} />
                  <span className="text-sm font-medium">
                    {websocket.callStatus.status === 'connected' ? 'On Call' :
                     websocket.callStatus.status === 'ringing' ? 'Incoming Call' : 'Call Ended'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>
      
      {/* Navigation Tabs */}
      <nav className="glass border-b border-gray-800 flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all border-b-2 ${
                    activeTab === tab.id
                      ? 'text-green-400 border-green-400 bg-green-500/10'
                      : 'text-gray-400 border-transparent hover:text-gray-200 hover:bg-gray-800/50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>
      
      {/* Main Content */}
      <main className="flex-1 overflow-y-auto max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && <Dashboard websocket={websocket} />}
        {activeTab === 'conversations' && <ConversationLog websocket={websocket} />}
        {activeTab === 'settings' && <Settings />}
      </main>
      
      {/* Footer - Fixed at bottom */}
      <footer className="glass border-t border-gray-800 py-3 flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs text-gray-500">
            SIP AI Bridge v1.0.0 • Extension: 5000 • {currentTime || getCurrentTime(timezone)}
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;

