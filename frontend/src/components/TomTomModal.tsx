import { X, Navigation, AlertTriangle, MapPin, Clock, Route, Info } from 'lucide-react';

interface TomTomModalProps {
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
  onClose: () => void;
}

export function TomTomModal({ tomtom, onClose }: TomTomModalProps) {
  // Parse result_data
  let resultData: any = {};
  try {
    if (tomtom.result_data) {
      resultData = typeof tomtom.result_data === 'string'
        ? JSON.parse(tomtom.result_data)
        : tomtom.result_data;
    }
  } catch (e) {
    console.error('Failed to parse TomTom result data:', e);
  }

  // Render directions modal
  if (tomtom.data_type === 'directions') {
    const instructions = resultData.instructions || [];
    const trafficDelayMinutes = Math.round((resultData.traffic_delay_seconds || 0) / 60);

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
              <div className="text-4xl mt-1">🚗</div>
              <div className="flex-1">
                <h2 className="text-xl font-bold text-white">Directions</h2>
                <div className="flex items-center gap-2 mt-2 text-sm text-gray-300">
                  <Navigation className="w-4 h-4" />
                  <span>{tomtom.origin}</span>
                  <span className="text-gray-500">→</span>
                  <span>{tomtom.destination}</span>
                </div>
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
            {/* Route Summary */}
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-red-400 mb-3">
                <Route className="w-4 h-4" />
                <span>Route Summary</span>
              </div>
              <div className="pl-6 grid grid-cols-2 gap-4">
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">Distance</div>
                  <div className="text-lg font-semibold text-white">
                    {tomtom.distance_miles?.toFixed(1)} miles
                  </div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">Travel Time</div>
                  <div className="text-lg font-semibold text-white">
                    {tomtom.travel_time_minutes} min
                  </div>
                </div>
                {trafficDelayMinutes > 0 && (
                  <div className="bg-gray-800/50 rounded-lg p-3 col-span-2">
                    <div className="text-xs text-gray-400 mb-1">Traffic Delay</div>
                    <div className="text-lg font-semibold text-yellow-400">
                      +{trafficDelayMinutes} min delay due to traffic
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Turn-by-turn Instructions */}
            {instructions.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-red-400 mb-3">
                  <Info className="w-4 h-4" />
                  <span>Directions (First 10 steps)</span>
                </div>
                <div className="pl-6 space-y-2">
                  {instructions.map((instruction: string, idx: number) => (
                    <div key={idx} className="bg-gray-800/50 rounded-lg p-3 flex gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-red-500/20 rounded-full flex items-center justify-center text-xs font-semibold text-red-300">
                        {idx + 1}
                      </div>
                      <div className="text-sm text-gray-300 flex-1">{instruction}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Fetched Time */}
            {tomtom.fetched_at && (
              <div className="text-xs text-gray-500 text-center pt-2 border-t border-white/10">
                Route fetched at {new Date(tomtom.fetched_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Render traffic modal
  if (tomtom.data_type === 'traffic') {
    const incidents = resultData.incidents || [];
    const hasIncidents = incidents.length > 0;

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
              <div className="text-4xl mt-1">{hasIncidents ? '🚦' : '✅'}</div>
              <div className="flex-1">
                <h2 className="text-xl font-bold text-white">Traffic Status</h2>
                <div className="flex items-center gap-2 mt-2 text-sm text-gray-300">
                  <MapPin className="w-4 h-4" />
                  <span>{tomtom.location}</span>
                </div>
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
            {/* Incident Summary */}
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-red-400 mb-3">
                <AlertTriangle className="w-4 h-4" />
                <span>Incident Summary</span>
              </div>
              <div className="pl-6">
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-lg font-semibold text-white">
                    {hasIncidents
                      ? `${tomtom.incident_count} incident${tomtom.incident_count !== 1 ? 's' : ''} detected`
                      : 'No traffic incidents reported'}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Within {resultData.radius_km || 10} km radius
                  </div>
                </div>
              </div>
            </div>

            {/* Incident Details */}
            {hasIncidents && (
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-red-400 mb-3">
                  <Info className="w-4 h-4" />
                  <span>Incident Details</span>
                </div>
                <div className="pl-6 space-y-3">
                  {incidents.map((incident: any, idx: number) => (
                    <div key={idx} className="bg-gray-800/50 rounded-lg p-4 space-y-2">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="font-semibold text-white">{incident.description || 'Unknown incident'}</div>
                          <div className="text-sm text-gray-400 mt-1">
                            {incident.road || 'Unknown location'}
                          </div>
                        </div>
                        {incident.severity && (
                          <div className={`px-2 py-1 rounded text-xs font-semibold ${
                            incident.severity === 'Severe' ? 'bg-red-500/20 text-red-300' :
                            incident.severity === 'Major' ? 'bg-orange-500/20 text-orange-300' :
                            incident.severity === 'Moderate' ? 'bg-yellow-500/20 text-yellow-300' :
                            'bg-blue-500/20 text-blue-300'
                          }`}>
                            {incident.severity}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-gray-400">
                        {incident.delay_minutes > 0 && (
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>{incident.delay_minutes} min delay</span>
                          </div>
                        )}
                        {incident.length_meters > 0 && (
                          <div>
                            <span>{(incident.length_meters / 1000).toFixed(1)} km long</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Fetched Time */}
            {tomtom.fetched_at && (
              <div className="text-xs text-gray-500 text-center pt-2 border-t border-white/10">
                Traffic data fetched at {new Date(tomtom.fetched_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Render POI modal
  if (tomtom.data_type === 'poi') {
    const results = resultData.results || [];

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
              <div className="text-4xl mt-1">📍</div>
              <div className="flex-1">
                <h2 className="text-xl font-bold text-white">Points of Interest</h2>
                <div className="flex items-center gap-2 mt-2 text-sm text-gray-300">
                  <span>Search: {tomtom.query}</span>
                </div>
                {tomtom.location && (
                  <div className="flex items-center gap-2 mt-1 text-sm text-gray-400">
                    <MapPin className="w-3 h-3" />
                    <span>{tomtom.location}</span>
                  </div>
                )}
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
            {/* Results Summary */}
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-red-400 mb-3">
                <MapPin className="w-4 h-4" />
                <span>Search Results</span>
              </div>
              <div className="pl-6">
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-lg font-semibold text-white">
                    {results.length} place{results.length !== 1 ? 's' : ''} found
                  </div>
                </div>
              </div>
            </div>

            {/* POI List */}
            {results.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-red-400 mb-3">
                  <Info className="w-4 h-4" />
                  <span>Places</span>
                </div>
                <div className="pl-6 space-y-3">
                  {results.map((poi: any, idx: number) => (
                    <div key={idx} className="bg-gray-800/50 rounded-lg p-4 space-y-2">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="font-semibold text-white">{poi.name || 'Unknown'}</div>
                          <div className="text-sm text-gray-400 mt-1">
                            {poi.address || 'No address available'}
                          </div>
                        </div>
                        {poi.distance && (
                          <div className="px-2 py-1 rounded text-xs font-semibold bg-blue-500/20 text-blue-300">
                            {(poi.distance / 1000).toFixed(1)} km
                          </div>
                        )}
                      </div>
                      {poi.category && (
                        <div className="text-xs text-gray-500">
                          {poi.category}
                        </div>
                      )}
                      {(poi.phone || poi.url) && (
                        <div className="flex flex-wrap gap-2 text-xs">
                          {poi.phone && (
                            <a
                              href={`tel:${poi.phone}`}
                              className="text-blue-400 hover:underline"
                            >
                              {poi.phone}
                            </a>
                          )}
                          {poi.url && (
                            <a
                              href={poi.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-400 hover:underline"
                            >
                              Website
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Fetched Time */}
            {tomtom.fetched_at && (
              <div className="text-xs text-gray-500 text-center pt-2 border-t border-white/10">
                POI data fetched at {new Date(tomtom.fetched_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
