import { useEffect, useState } from 'react';
import {
  Save,
  RefreshCw,
  Phone,
  Mic,
  MessageSquare,
  Volume2,
  Key,
  Server,
  CheckCircle,
  AlertCircle,
  Eye,
  EyeOff,
  Download,
  Cpu,
  Clock,
  Play,
  Calendar,
  Mail,
  Cloud,
  Map
} from 'lucide-react';
import { setTimezone, getCurrentTime } from '../utils/timezone';

interface Config {
  sip_host: string;
  sip_port: number;
  sip_username: string;
  sip_password?: string;
  sip_extension: string;
  ollama_url: string;
  ollama_model: string;
  tts_url: string;
  tts_api_key?: string;
  tts_voice: string;
  groq_api_key?: string;
  timezone?: string;
  bot_persona?: string;
  calendar_url?: string;
  email_address?: string;
  email_app_password?: string;
  email_imap_server?: string;
  email_imap_port?: number;
  openweather_api_key?: string;
  tomtom_api_key?: string;
}

interface OllamaModel {
  name: string;
  size: number;
  modified_at: string;
  digest: string;
}

export function Settings() {
  const [config, setConfig] = useState<Config>({
    sip_host: '10.0.0.87',
    sip_port: 5060,
    sip_username: 'mumble-bridge',
    sip_extension: '5000',
    ollama_url: 'http://host.docker.internal:11434',
    ollama_model: 'llama3.1',
    tts_url: 'http://10.0.0.59:5050',
    tts_voice: 'en-US-GuyNeural',
    timezone: 'UTC',
  });
  const [voices, setVoices] = useState<string[]>([]);
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
  const [loadingModels, setLoadingModels] = useState(false);
  const [pullingModel, setPullingModel] = useState(false);
  const [newModelName, setNewModelName] = useState('');
  const [previewingVoice, setPreviewingVoice] = useState(false);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);
  const [generatingPersona, setGeneratingPersona] = useState(false);
  
  useEffect(() => {
    fetchConfig();
    fetchVoices();
    fetchOllamaModels();
  }, []);
  
  async function fetchConfig() {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      setConfig(prev => ({ ...prev, ...data }));
    } catch (err) {
      console.error('Failed to fetch config:', err);
    }
  }
  
  async function fetchVoices() {
    try {
      const res = await fetch('/api/voices');
      const data = await res.json();
      setVoices(data.voices || []);
    } catch (err) {
      console.error('Failed to fetch voices:', err);
    }
  }
  
  async function fetchOllamaModels() {
    setLoadingModels(true);
    try {
      const res = await fetch('/api/models');
      const data = await res.json();
      setOllamaModels(data.models || []);
      if (data.current_model) {
        setConfig(prev => ({ ...prev, ollama_model: data.current_model }));
      }
    } catch (err) {
      console.error('Failed to fetch Ollama models:', err);
    } finally {
      setLoadingModels(false);
    }
  }
  
  async function pullModel() {
    if (!newModelName.trim()) return;
    
    setPullingModel(true);
    setError(null);
    
    try {
      const res = await fetch('/api/models/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: newModelName.trim() }),
      });
      
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to pull model');
      }
      
      setNewModelName('');
      await fetchOllamaModels();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setPullingModel(false);
    }
  }
  
  async function selectModel(modelName: string) {
    try {
      const res = await fetch('/api/models/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelName }),
      });
      
      if (res.ok) {
        setConfig(prev => ({ ...prev, ollama_model: modelName }));
      }
    } catch (err) {
      console.error('Failed to select model:', err);
    }
  }
  
  async function saveConfig() {
    setSaving(true);
    setError(null);
    setSaved(false);
    
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      
      if (!res.ok) {
        throw new Error('Failed to save configuration');
      }
      
      // Update global timezone if timezone was changed
      if (config.timezone) {
        setTimezone(config.timezone);
      }
      
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSaving(false);
    }
  }
  
  function handleChange(key: keyof Config, value: string | number) {
    setConfig(prev => ({ ...prev, [key]: value }));
    setSaved(false);
  }
  
  function togglePasswordVisibility(key: string) {
    setShowPasswords(prev => ({ ...prev, [key]: !prev[key] }));
  }
  
  function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  async function previewVoice() {
    if (previewingVoice) {
      // Stop current preview
      if (audioElement) {
        audioElement.pause();
        audioElement.src = '';
      }
      setPreviewingVoice(false);
      return;
    }

    setPreviewingVoice(true);
    setError(null);

    try {
      const res = await fetch('/api/preview/voice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice: config.tts_voice }),
      });

      if (!res.ok) {
        throw new Error('Failed to preview voice');
      }

      const audioBlob = await res.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      const audio = new Audio(audioUrl);
      setAudioElement(audio);

      audio.onended = () => {
        setPreviewingVoice(false);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = () => {
        setPreviewingVoice(false);
        setError('Failed to play audio');
        URL.revokeObjectURL(audioUrl);
      };

      await audio.play();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setPreviewingVoice(false);
    }
  }

  async function generatePersona() {
    if (!config.bot_persona) {
      setError('Please enter a draft persona first');
      return;
    }

    setGeneratingPersona(true);
    setError(null);

    try {
      const res = await fetch('/api/generate/persona', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draft: config.bot_persona }),
      });

      if (!res.ok) {
        throw new Error('Failed to generate persona');
      }

      const data = await res.json();
      setConfig(prev => ({ ...prev, bot_persona: data.persona }));
      setSaved(false); // Mark as unsaved
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setGeneratingPersona(false);
    }
  }
  
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Settings</h2>
          <p className="text-gray-400">Configure your SIP AI Bridge</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <div className="flex items-center gap-2 text-green-400">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm">Saved!</span>
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{error}</span>
            </div>
          )}
          <button
            onClick={saveConfig}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 text-white font-medium transition-colors disabled:opacity-50"
          >
            {saving ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </div>
      </div>
      
      {/* SIP Configuration */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-blue-500/20">
            <Phone className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">SIP Configuration</h3>
            <p className="text-sm text-gray-400">VoIP connection settings</p>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              SIP Host
            </label>
            <input
              type="text"
              value={config.sip_host}
              onChange={(e) => handleChange('sip_host', e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
              placeholder="10.0.0.87"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              SIP Port
            </label>
            <input
              type="number"
              value={config.sip_port}
              onChange={(e) => handleChange('sip_port', parseInt(e.target.value))}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
              placeholder="5060"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Username
            </label>
            <input
              type="text"
              value={config.sip_username}
              onChange={(e) => handleChange('sip_username', e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
              placeholder="mumble-bridge"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Password
            </label>
            <div className="relative">
              <input
                type={showPasswords['sip_password'] ? 'text' : 'password'}
                value={config.sip_password || ''}
                onChange={(e) => handleChange('sip_password', e.target.value)}
                className="w-full px-4 py-2 pr-10 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => togglePasswordVisibility('sip_password')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
              >
                {showPasswords['sip_password'] ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
          
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Extension
            </label>
            <input
              type="text"
              value={config.sip_extension}
              onChange={(e) => handleChange('sip_extension', e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
              placeholder="5000"
            />
          </div>
        </div>
      </div>
      
      {/* Groq API Configuration */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-purple-500/20">
            <Mic className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Groq Speech-to-Text</h3>
            <p className="text-sm text-gray-400">Audio transcription API</p>
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <Key className="w-4 h-4 inline mr-2" />
            Groq API Key
          </label>
          <div className="relative">
            <input
              type={showPasswords['groq_api_key'] ? 'text' : 'password'}
              value={config.groq_api_key || ''}
              onChange={(e) => handleChange('groq_api_key', e.target.value)}
              className="w-full px-4 py-2 pr-10 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500 font-mono text-sm"
              placeholder="gsk_..."
            />
            <button
              type="button"
              onClick={() => togglePasswordVisibility('groq_api_key')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
            >
              {showPasswords['groq_api_key'] ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
      
      {/* Ollama Configuration */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-green-500/20">
            <Cpu className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Ollama (Local LLM)</h3>
            <p className="text-sm text-gray-400">AI response generation using local models</p>
          </div>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Server className="w-4 h-4 inline mr-2" />
              Ollama Server URL
            </label>
            <input
              type="text"
              value={config.ollama_url}
              onChange={(e) => handleChange('ollama_url', e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
              placeholder="http://host.docker.internal:11434"
            />
            <p className="text-xs text-gray-500 mt-1">
              Use host.docker.internal:11434 for Docker to access your local Ollama
            </p>
          </div>
          
          {/* Model Selection */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-300">
                <MessageSquare className="w-4 h-4 inline mr-2" />
                Active Model
              </label>
              <button
                onClick={fetchOllamaModels}
                disabled={loadingModels}
                className="text-sm text-green-400 hover:text-green-300 flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${loadingModels ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
            
            {ollamaModels.length > 0 ? (
              <div className="space-y-2">
                {ollamaModels.map((model) => (
                  <div 
                    key={model.name}
                    onClick={() => selectModel(model.name)}
                    className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                      config.ollama_model === model.name 
                        ? 'bg-green-500/20 border border-green-500/50' 
                        : 'bg-gray-800 border border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {config.ollama_model === model.name && (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      )}
                      <span className="text-gray-200 font-medium">{model.name}</span>
                    </div>
                    <span className="text-gray-500 text-sm">{formatSize(model.size)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">
                {loadingModels ? 'Loading models...' : 'No models found. Pull a model below.'}
              </div>
            )}
          </div>
          
          {/* Pull New Model */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Download className="w-4 h-4 inline mr-2" />
              Pull New Model
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={newModelName}
                onChange={(e) => setNewModelName(e.target.value)}
                className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
                placeholder="llama3.1, mistral, codellama, etc."
              />
              <button
                onClick={pullModel}
                disabled={pullingModel || !newModelName.trim()}
                className="px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 text-white font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {pullingModel ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                Pull
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Popular models: llama3.1, llama3.2, mistral, codellama, phi3, gemma2
            </p>
          </div>
        </div>
      </div>
      
      {/* TTS Configuration */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-amber-500/20">
            <Volume2 className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Text-to-Speech</h3>
            <p className="text-sm text-gray-400">Voice synthesis settings</p>
          </div>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Server className="w-4 h-4 inline mr-2" />
              TTS Server URL
            </label>
            <input
              type="text"
              value={config.tts_url}
              onChange={(e) => handleChange('tts_url', e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
              placeholder="http://10.0.0.59:5050"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Key className="w-4 h-4 inline mr-2" />
              TTS API Key
            </label>
            <div className="relative">
              <input
                type={showPasswords['tts_api_key'] ? 'text' : 'password'}
                value={config.tts_api_key || ''}
                onChange={(e) => handleChange('tts_api_key', e.target.value)}
                className="w-full px-4 py-2 pr-10 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500 font-mono text-sm"
                placeholder="your_api_key_here"
              />
              <button
                type="button"
                onClick={() => togglePasswordVisibility('tts_api_key')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
              >
                {showPasswords['tts_api_key'] ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Voice
            </label>
            <div className="flex gap-2">
              <select
                value={config.tts_voice}
                onChange={(e) => handleChange('tts_voice', e.target.value)}
                className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
              >
                {voices.length > 0 ? (
                  voices.map((voice) => (
                    <option key={voice} value={voice}>
                      {voice}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="en-US-GuyNeural">en-US-GuyNeural (Male)</option>
                    <option value="en-US-JennyNeural">en-US-JennyNeural (Female)</option>
                    <option value="en-US-AriaNeural">en-US-AriaNeural (Female)</option>
                    <option value="en-US-DavisNeural">en-US-DavisNeural (Male)</option>
                    <option value="en-GB-SoniaNeural">en-GB-SoniaNeural (Female, British)</option>
                    <option value="en-GB-RyanNeural">en-GB-RyanNeural (Male, British)</option>
                  </>
                )}
              </select>
              <button
                onClick={previewVoice}
                disabled={previewingVoice}
                className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-medium transition-colors disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
                title="Preview voice"
              >
                {previewingVoice ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Preview
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Click Preview to hear how this voice sounds
            </p>
          </div>
        </div>
      </div>
      
      {/* Bot Persona Configuration */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-pink-500/20">
            <MessageSquare className="w-5 h-5 text-pink-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Bot Persona</h3>
            <p className="text-sm text-gray-400">Define how the AI assistant behaves and responds</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Persona Description
          </label>
          <textarea
            value={config.bot_persona || ''}
            onChange={(e) => handleChange('bot_persona', e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500 min-h-[150px] font-mono text-sm"
            placeholder="You are a helpful AI assistant. You provide clear, concise, and friendly responses."
          />
          <div className="flex items-center justify-between mt-2">
            <p className="text-xs text-gray-500">
              Describe the personality, tone, and behavior of your AI assistant
            </p>
            <button
              onClick={generatePersona}
              disabled={generatingPersona || !config.bot_persona}
              className="px-4 py-2 rounded-lg bg-pink-500 hover:bg-pink-600 text-white font-medium transition-colors disabled:opacity-50 flex items-center gap-2 text-sm"
              title="Use AI to enhance your persona"
            >
              {generatingPersona ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <MessageSquare className="w-4 h-4" />
              )}
              Enhance with AI
            </button>
          </div>
        </div>
      </div>

      {/* Timezone Configuration */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-indigo-500/20">
            <Clock className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Timezone</h3>
            <p className="text-sm text-gray-400">Set the timezone for date and time displays</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Timezone
          </label>
          <select
            value={config.timezone || 'UTC'}
            onChange={(e) => handleChange('timezone', e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
          >
            <optgroup label="UTC">
              <option value="UTC">UTC (Coordinated Universal Time)</option>
            </optgroup>
            <optgroup label="Americas">
              <option value="America/New_York">America/New_York (Eastern Time - US/Canada)</option>
              <option value="America/Chicago">America/Chicago (Central Time - US/Canada)</option>
              <option value="America/Denver">America/Denver (Mountain Time - US/Canada)</option>
              <option value="America/Los_Angeles">America/Los_Angeles (Pacific Time - US/Canada)</option>
              <option value="America/Toronto">America/Toronto (Eastern Time - Canada)</option>
              <option value="America/Vancouver">America/Vancouver (Pacific Time - Canada)</option>
              <option value="America/Mexico_City">America/Mexico_City (Central Time - Mexico)</option>
              <option value="America/Sao_Paulo">America/Sao_Paulo (Brasilia Time - Brazil)</option>
              <option value="America/Buenos_Aires">America/Buenos_Aires (Argentina Time)</option>
            </optgroup>
            <optgroup label="Europe">
              <option value="Europe/London">Europe/London (GMT/BST - UK)</option>
              <option value="Europe/Paris">Europe/Paris (CET/CEST - France, Germany, Italy)</option>
              <option value="Europe/Berlin">Europe/Berlin (CET/CEST - Germany)</option>
              <option value="Europe/Rome">Europe/Rome (CET/CEST - Italy)</option>
              <option value="Europe/Madrid">Europe/Madrid (CET/CEST - Spain)</option>
              <option value="Europe/Amsterdam">Europe/Amsterdam (CET/CEST - Netherlands)</option>
              <option value="Europe/Stockholm">Europe/Stockholm (CET/CEST - Sweden)</option>
              <option value="Europe/Moscow">Europe/Moscow (MSK - Russia)</option>
            </optgroup>
            <optgroup label="Asia">
              <option value="Asia/Tokyo">Asia/Tokyo (JST - Japan)</option>
              <option value="Asia/Shanghai">Asia/Shanghai (CST - China)</option>
              <option value="Asia/Hong_Kong">Asia/Hong_Kong (HKT - Hong Kong)</option>
              <option value="Asia/Singapore">Asia/Singapore (SGT - Singapore)</option>
              <option value="Asia/Seoul">Asia/Seoul (KST - South Korea)</option>
              <option value="Asia/Dubai">Asia/Dubai (GST - UAE)</option>
              <option value="Asia/Kolkata">Asia/Kolkata (IST - India)</option>
              <option value="Asia/Bangkok">Asia/Bangkok (ICT - Thailand)</option>
            </optgroup>
            <optgroup label="Oceania">
              <option value="Australia/Sydney">Australia/Sydney (AEDT/AEST - Australia)</option>
              <option value="Australia/Melbourne">Australia/Melbourne (AEDT/AEST - Australia)</option>
              <option value="Australia/Brisbane">Australia/Brisbane (AEST - Australia)</option>
              <option value="Australia/Perth">Australia/Perth (AWST - Australia)</option>
              <option value="Pacific/Auckland">Pacific/Auckland (NZDT/NZST - New Zealand)</option>
            </optgroup>
            <optgroup label="Africa">
              <option value="Africa/Cairo">Africa/Cairo (EET - Egypt)</option>
              <option value="Africa/Johannesburg">Africa/Johannesburg (SAST - South Africa)</option>
              <option value="Africa/Lagos">Africa/Lagos (WAT - Nigeria)</option>
            </optgroup>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Current time in selected timezone: {getCurrentTime(config.timezone || 'UTC')}
          </p>
        </div>
      </div>

      {/* Calendar Integration */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-teal-500/20">
            <Calendar className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Calendar Integration</h3>
            <p className="text-sm text-gray-400">Connect your calendar so the AI can access your schedule</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Calendar URL (iCalendar/ICS)
          </label>
          <input
            type="text"
            value={config.calendar_url || ''}
            onChange={(e) => handleChange('calendar_url', e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500 font-mono text-sm"
            placeholder="https://api.cupla.app/api/calendars/..."
          />
          <p className="text-xs text-gray-500 mt-1">
            Enter your iCalendar feed URL. Most calendar apps (Google Calendar, Outlook, etc.) provide an ICS export URL. The AI will be able to answer questions about your schedule.
          </p>
        </div>
      </div>

      {/* Email Integration */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-purple-500/20">
            <Mail className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Email Integration (IMAP)</h3>
            <p className="text-sm text-gray-400">Connect your email so the AI can check your inbox when asked</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Email Address
            </label>
            <input
              type="email"
              value={config.email_address || ''}
              onChange={(e) => handleChange('email_address', e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
              placeholder="your.email@gmail.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              App Password
            </label>
            <input
              type="password"
              value={config.email_app_password || ''}
              onChange={(e) => handleChange('email_app_password', e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500 font-mono text-sm"
              placeholder="••••••••••••••••"
            />
            <p className="text-xs text-gray-500 mt-1">
              For Gmail: Create an <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">App Password</a> (not your regular password)
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                IMAP Server
              </label>
              <input
                type="text"
                value={config.email_imap_server || 'imap.gmail.com'}
                onChange={(e) => handleChange('email_imap_server', e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
                placeholder="imap.gmail.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                IMAP Port
              </label>
              <input
                type="number"
                value={config.email_imap_port || 993}
                onChange={(e) => handleChange('email_imap_port', parseInt(e.target.value))}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500"
                placeholder="993"
              />
            </div>
          </div>

          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
            <p className="text-sm text-blue-300">
              <strong>How it works:</strong> The AI will only check your email when you specifically ask about it during a call (e.g., "Do I have any new emails?"). It will fetch your 3 most recent unread emails from your primary inbox.
            </p>
          </div>
        </div>
      </div>

      {/* OpenWeatherMap Integration */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-cyan-500/20">
            <Cloud className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Weather Integration</h3>
            <p className="text-sm text-gray-400">Connect to OpenWeatherMap for weather information</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <Key className="w-4 h-4 inline mr-2" />
            OpenWeatherMap API Key
          </label>
          <div className="relative">
            <input
              type={showPasswords['openweather_api_key'] ? 'text' : 'password'}
              value={config.openweather_api_key || ''}
              onChange={(e) => handleChange('openweather_api_key', e.target.value)}
              className="w-full px-4 py-2 pr-10 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500 font-mono text-sm"
              placeholder="Your OpenWeatherMap API key"
            />
            <button
              type="button"
              onClick={() => togglePasswordVisibility('openweather_api_key')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
            >
              {showPasswords['openweather_api_key'] ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Get your free API key at <a href="https://openweathermap.org/api" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">openweathermap.org/api</a>. The AI will be able to answer questions about the weather when you ask.
          </p>
        </div>
      </div>

      {/* TomTom Integration */}
      <div className="glass rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-red-500/10 rounded-lg">
            <Map className="w-5 h-5 text-red-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">TomTom Maps Integration</h3>
            <p className="text-sm text-gray-400">Connect to TomTom for traffic, directions, and POI searches</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <Key className="w-4 h-4 inline mr-2" />
            TomTom API Key
          </label>
          <div className="relative">
            <input
              type={showPasswords['tomtom_api_key'] ? 'text' : 'password'}
              value={config.tomtom_api_key || ''}
              onChange={(e) => handleChange('tomtom_api_key', e.target.value)}
              className="w-full px-4 py-2 pr-10 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-green-500 font-mono text-sm"
              placeholder="Your TomTom API key"
            />
            <button
              type="button"
              onClick={() => togglePasswordVisibility('tomtom_api_key')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
            >
              {showPasswords['tomtom_api_key'] ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Get your free API key at <a href="https://developer.tomtom.com/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">developer.tomtom.com</a>. The AI will be able to provide traffic updates, directions, and find points of interest.
          </p>
        </div>
      </div>

      {/* Test Buttons */}
      <div className="glass rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Test Services</h3>
        <div className="flex flex-wrap gap-3">
          <TestButton 
            endpoint="/api/test/ollama" 
            method="POST"
            body={{ text: "Hello, this is a test." }}
            label="Test Ollama"
            icon={<Cpu className="w-4 h-4" />}
          />
          <TestButton 
            endpoint="/api/health" 
            method="GET"
            label="Health Check"
            icon={<CheckCircle className="w-4 h-4" />}
          />
        </div>
      </div>
    </div>
  );
}

interface TestButtonProps {
  endpoint: string;
  method: 'GET' | 'POST';
  body?: object;
  label: string;
  icon: React.ReactNode;
}

function TestButton({ endpoint, method, body, label, icon }: TestButtonProps) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<'success' | 'error' | null>(null);
  
  async function runTest() {
    setTesting(true);
    setResult(null);
    
    try {
      const res = await fetch(endpoint, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      
      setResult(res.ok ? 'success' : 'error');
    } catch {
      setResult('error');
    } finally {
      setTesting(false);
      setTimeout(() => setResult(null), 3000);
    }
  }
  
  return (
    <button
      onClick={runTest}
      disabled={testing}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
        result === 'success' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
        result === 'error' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
        'bg-gray-700 hover:bg-gray-600 text-gray-200 border border-transparent'
      }`}
    >
      {testing ? (
        <RefreshCw className="w-4 h-4 animate-spin" />
      ) : result === 'success' ? (
        <CheckCircle className="w-4 h-4" />
      ) : result === 'error' ? (
        <AlertCircle className="w-4 h-4" />
      ) : (
        icon
      )}
      {label}
    </button>
  );
}
