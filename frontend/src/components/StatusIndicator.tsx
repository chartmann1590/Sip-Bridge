import { CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react';

interface StatusIndicatorProps {
  status: boolean | null;
  label: string;
  loading?: boolean;
}

export function StatusIndicator({ status, label, loading = false }: StatusIndicatorProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800/50">
        <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
        <span className="text-sm text-gray-300">{label}</span>
      </div>
    );
  }
  
  if (status === null) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800/50">
        <AlertCircle className="w-4 h-4 text-gray-500" />
        <span className="text-sm text-gray-400">{label}</span>
        <span className="text-xs text-gray-500 ml-auto">Unknown</span>
      </div>
    );
  }
  
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
      status ? 'bg-green-500/10' : 'bg-red-500/10'
    }`}>
      {status ? (
        <CheckCircle className="w-4 h-4 text-green-400" />
      ) : (
        <XCircle className="w-4 h-4 text-red-400" />
      )}
      <span className={`text-sm ${status ? 'text-green-300' : 'text-red-300'}`}>
        {label}
      </span>
      <span className={`text-xs ml-auto ${status ? 'text-green-500' : 'text-red-500'}`}>
        {status ? 'Online' : 'Offline'}
      </span>
    </div>
  );
}

interface ServiceCardProps {
  name: string;
  status: boolean;
  description: string;
  icon: React.ReactNode;
}

export function ServiceCard({ name, status, description, icon }: ServiceCardProps) {
  return (
    <div className={`glass rounded-xl p-4 transition-all ${
      status ? 'border-green-500/30 glow-green' : 'border-red-500/30 glow-red'
    }`}>
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg ${status ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
          {icon}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-white">{name}</h3>
            <div className={`w-2 h-2 rounded-full ${status ? 'bg-green-400 status-dot' : 'bg-red-400'}`} />
          </div>
          <p className="text-xs text-gray-400 mt-1">{description}</p>
        </div>
      </div>
    </div>
  );
}






