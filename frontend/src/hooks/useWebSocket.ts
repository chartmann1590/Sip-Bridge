import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

export interface CallStatus {
  status: 'idle' | 'ringing' | 'connected' | 'ended';
  callId?: string;
  callerId?: string;
  timestamp?: string;
}

export interface Message {
  id?: number;
  conversationId: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  callId?: string;
  timestamp: string;
}

export interface LogEntry {
  id?: number;
  level: 'info' | 'warning' | 'error';
  event: string;
  details?: string;
  callId?: string;
  timestamp: string;
}

export interface HealthStatus {
  services: {
    api: boolean;
    database: boolean;
    groq: boolean;
    ollama: boolean;
    tts: boolean;
    sip: boolean;
  };
  timestamp: string;
}

export interface SipStatus {
  registered: boolean;
  details?: Record<string, unknown>;
  timestamp: string;
}

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [callStatus, setCallStatus] = useState<CallStatus>({ status: 'idle' });
  const [messages, setMessages] = useState<Message[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [sipStatus, setSipStatus] = useState<SipStatus | null>(null);
  
  const socketRef = useRef<Socket | null>(null);
  
  useEffect(() => {
    // Connect to WebSocket
    const socket = io(window.location.origin, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    });
    
    socketRef.current = socket;
    // Expose socket globally for components that need direct access
    (window as any).socket = socket;
    
    socket.on('connect', () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    });
    
    socket.on('disconnect', () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    });
    
    socket.on('connected', (data) => {
      console.log('Server acknowledged connection:', data);
    });
    
    socket.on('call_status', (data: CallStatus) => {
      setCallStatus(data);
    });
    
    socket.on('new_message', (data: Message) => {
      console.log('Received new_message:', data);
      setMessages((prev) => [...prev, data].slice(-100)); // Keep last 100 messages
    });
    
    socket.on('log_entry', (data: LogEntry) => {
      setLogs((prev) => [data, ...prev].slice(0, 200)); // Keep last 200 logs
    });
    
    socket.on('health_status', (data: HealthStatus) => {
      setHealthStatus(data);
    });
    
    socket.on('sip_status', (data: SipStatus) => {
      setSipStatus(data);
    });
    
    socket.on('transcription', (data: { callId: string; text: string; isFinal: boolean }) => {
      // Handle real-time transcription updates if needed
      console.log('Transcription:', data);
    });
    
    return () => {
      socket.disconnect();
      delete (window as any).socket;
    };
  }, []);
  
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);
  
  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);
  
  return {
    isConnected,
    callStatus,
    messages,
    logs,
    healthStatus,
    sipStatus,
    clearMessages,
    clearLogs,
  };
}

