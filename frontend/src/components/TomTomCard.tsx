import { Map, AlertTriangle, MapPin, Clock, Route } from 'lucide-react';

interface TomTomCardProps {
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
  };
  onClick: () => void;
}

export function TomTomCard({ tomtom, onClick }: TomTomCardProps) {
  // Render based on data type
  if (tomtom.data_type === 'directions') {
    return (
      <button
        onClick={onClick}
        className="inline-flex items-center gap-2 px-3 py-2 mx-1 my-0.5 rounded-lg bg-red-500/20 border border-red-500/30 hover:bg-red-500/30 transition-all duration-200 text-sm group"
      >
        <div className="text-2xl">🚗</div>

        <div className="flex flex-col items-start text-left">
          <span className="text-red-100 font-medium leading-tight">
            Directions: {tomtom.origin} → {tomtom.destination}
          </span>

          <div className="flex items-center gap-2 text-xs text-red-300/80">
            <Route className="w-3 h-3" />
            <span>
              {tomtom.distance_miles?.toFixed(1)} miles
            </span>
          </div>

          {tomtom.travel_time_minutes && (
            <div className="flex items-center gap-1 text-xs text-red-300/70">
              <Clock className="w-3 h-3" />
              <span>{tomtom.travel_time_minutes} min</span>
            </div>
          )}
        </div>
      </button>
    );
  }

  if (tomtom.data_type === 'traffic') {
    const hasIncidents = (tomtom.incident_count || 0) > 0;

    return (
      <button
        onClick={onClick}
        className="inline-flex items-center gap-2 px-3 py-2 mx-1 my-0.5 rounded-lg bg-red-500/20 border border-red-500/30 hover:bg-red-500/30 transition-all duration-200 text-sm group"
      >
        <div className="text-2xl">{hasIncidents ? '🚦' : '✅'}</div>

        <div className="flex flex-col items-start text-left">
          <span className="text-red-100 font-medium leading-tight">
            Traffic: {tomtom.location}
          </span>

          <div className="flex items-center gap-2 text-xs text-red-300/80">
            <AlertTriangle className="w-3 h-3" />
            <span>
              {hasIncidents
                ? `${tomtom.incident_count} incident${tomtom.incident_count !== 1 ? 's' : ''}`
                : 'No incidents'}
            </span>
          </div>
        </div>
      </button>
    );
  }

  if (tomtom.data_type === 'poi') {
    // Parse result_data to get count
    let poiCount = 0;
    try {
      const resultData = typeof tomtom.result_data === 'string'
        ? JSON.parse(tomtom.result_data)
        : tomtom.result_data;
      poiCount = resultData?.results?.length || 0;
    } catch (e) {
      // Ignore parse errors
    }

    return (
      <button
        onClick={onClick}
        className="inline-flex items-center gap-2 px-3 py-2 mx-1 my-0.5 rounded-lg bg-red-500/20 border border-red-500/30 hover:bg-red-500/30 transition-all duration-200 text-sm group"
      >
        <div className="text-2xl">📍</div>

        <div className="flex flex-col items-start text-left">
          <span className="text-red-100 font-medium leading-tight">
            POI Search: {tomtom.query}
          </span>

          {tomtom.location && (
            <div className="flex items-center gap-2 text-xs text-red-300/80">
              <MapPin className="w-3 h-3" />
              <span>{tomtom.location}</span>
            </div>
          )}

          <div className="flex items-center gap-1 text-xs text-red-300/70">
            <Map className="w-3 h-3" />
            <span>{poiCount} place{poiCount !== 1 ? 's' : ''} found</span>
          </div>
        </div>
      </button>
    );
  }

  return null;
}
