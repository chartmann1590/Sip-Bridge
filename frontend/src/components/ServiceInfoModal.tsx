import { X, Calendar, Mail, Cloud, Map, Info, Zap, FileText } from 'lucide-react';

interface ServiceInfo {
  name: string;
  icon: React.ReactNode;
  description: string;
  howToTrigger: string[];
  examples: string[];
  status: boolean;
}

interface ServiceInfoModalProps {
  service: ServiceInfo;
  onClose: () => void;
}

export function ServiceInfoModal({ service, onClose }: ServiceInfoModalProps) {
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
            <div className="text-4xl mt-1">{service.icon}</div>
            <div className="flex-1">
              <h2 className="text-xl font-bold text-white">{service.name}</h2>
              <div className="flex items-center gap-2 mt-2">
                <div className={`px-2 py-1 rounded text-xs font-semibold ${
                  service.status
                    ? 'bg-green-500/20 text-green-300'
                    : 'bg-red-500/20 text-red-300'
                }`}>
                  {service.status ? 'Active' : 'Inactive'}
                </div>
              </div>
              <p className="text-sm text-gray-400 mt-2">{service.description}</p>
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
        <div className="px-6 py-4 space-y-6">
          {/* How to Trigger */}
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-400 mb-3">
              <Zap className="w-4 h-4" />
              <span>How to Trigger</span>
            </div>
            <div className="pl-6 space-y-2">
              {service.howToTrigger.map((trigger, idx) => (
                <div key={idx} className="bg-gray-800/50 rounded-lg p-3 flex gap-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-500/20 rounded-full flex items-center justify-center text-xs font-semibold text-blue-300">
                    {idx + 1}
                  </div>
                  <div className="text-sm text-gray-300 flex-1">{trigger}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Examples */}
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-purple-400 mb-3">
              <Info className="w-4 h-4" />
              <span>Example Queries</span>
            </div>
            <div className="pl-6 space-y-2">
              {service.examples.map((example, idx) => (
                <div key={idx} className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-sm text-gray-300 font-mono">"{example}"</div>
                </div>
              ))}
            </div>
          </div>

          {!service.status && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-amber-300 font-semibold">Service Not Configured</p>
                  <p className="text-xs text-amber-300/80 mt-1">
                    This service requires configuration in the Settings page. Add the necessary API keys or credentials to enable this feature.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Service configurations
export const serviceInfoMap: Record<string, ServiceInfo> = {
  calendar: {
    name: 'Calendar Integration',
    icon: <Calendar className="w-6 h-6 text-indigo-400" />,
    description: 'Access your calendar events and schedules during phone conversations.',
    howToTrigger: [
      'Simply ask about your schedule or upcoming events',
      'AI will automatically fetch your calendar when relevant',
      'Ask about specific dates or time periods',
    ],
    examples: [
      'What do I have on my calendar today?',
      'Do I have any meetings tomorrow?',
      'What\'s on my schedule next week?',
      'Am I free on Friday afternoon?',
    ],
    status: false,
  },
  email: {
    name: 'Email Integration',
    icon: <Mail className="w-6 h-6 text-blue-400" />,
    description: 'Check recent emails and get summaries during phone calls.',
    howToTrigger: [
      'Ask about your inbox or recent emails',
      'AI will fetch emails when questions are asked',
      'Can filter by sender or recent timeframe',
    ],
    examples: [
      'Do I have any new emails?',
      'What are my recent emails about?',
      'Did I get any emails from John?',
      'Check my inbox',
    ],
    status: false,
  },
  weather: {
    name: 'Weather Information',
    icon: <Cloud className="w-6 h-6 text-cyan-400" />,
    description: 'Get real-time weather information for any location worldwide.',
    howToTrigger: [
      'Ask about weather for any city or location',
      'AI will fetch current weather data automatically',
      'Can provide temperature, conditions, and forecasts',
    ],
    examples: [
      'What\'s the weather like in New York?',
      'Is it raining in Seattle?',
      'How cold is it in Chicago?',
      'Tell me the weather forecast',
    ],
    status: false,
  },
  tomtom: {
    name: 'TomTom Maps & Traffic',
    icon: <Map className="w-6 h-6 text-red-400" />,
    description: 'Get directions, traffic updates, and find points of interest.',
    howToTrigger: [
      'Ask for directions between two locations',
      'Request traffic updates for an area',
      'Search for nearby places or businesses',
    ],
    examples: [
      'Give me directions from Boston to New York',
      'What\'s the traffic like near downtown?',
      'Find nearby gas stations',
      'How long will it take to get to the airport?',
    ],
    status: false,
  },
  notes: {
    name: 'Notes System',
    icon: <FileText className="w-6 h-6 text-purple-400" />,
    description: 'Capture voice notes during phone calls with AI-generated summaries and transcripts.',
    howToTrigger: [
      'Say \'start note\', \'begin note\', or \'take note\' during a call to start recording',
      'Speak your notes - everything will be transcribed with timestamps',
      'Say \'stop note\', \'end note\', \'finish note\', or \'save note\' to save the note',
    ],
    examples: [
      'Start note',
      'Take note',
      'Stop note',
      'Save note',
    ],
    status: false,
  },
};
