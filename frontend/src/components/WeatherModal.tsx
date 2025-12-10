import { X, Thermometer, Droplets, Wind, Eye } from 'lucide-react';

interface WeatherModalProps {
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
  onClose: () => void;
}

export function WeatherModal({ weather, onClose }: WeatherModalProps) {
  // Determine temperature units symbol and speed units
  const tempSymbol = weather.units === 'imperial' ? '°F' : weather.units === 'metric' ? '°C' : 'K';
  const speedUnit = weather.units === 'imperial' ? 'mph' : 'm/s';

  // Determine weather emoji based on type
  const getWeatherEmoji = () => {
    switch (weather.main.toLowerCase()) {
      case 'clear':
        return '☀️';
      case 'clouds':
        return '☁️';
      case 'rain':
      case 'drizzle':
        return '🌧️';
      case 'snow':
        return '❄️';
      case 'thunderstorm':
        return '⛈️';
      case 'mist':
      case 'fog':
      case 'haze':
        return '🌫️';
      default:
        return '🌤️';
    }
  };

  // Convert wind degree to cardinal direction
  const getWindDirection = (deg?: number) => {
    if (deg === undefined) return '';
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(deg / 45) % 8;
    return directions[index];
  };

  // Format visibility
  const formatVisibility = (meters?: number) => {
    if (meters === undefined) return 'N/A';
    if (weather.units === 'imperial') {
      const miles = meters / 1609.34;
      return `${miles.toFixed(1)} mi`;
    }
    const km = meters / 1000;
    return `${km.toFixed(1)} km`;
  };

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
            <div className="text-4xl mt-1">{getWeatherEmoji()}</div>
            <div className="flex-1">
              <h2 className="text-xl font-bold text-white">
                {weather.location}{weather.country ? `, ${weather.country}` : ''}
              </h2>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-3xl font-bold text-cyan-300">
                  {Math.round(weather.temperature)}{tempSymbol}
                </span>
                <span className="text-lg text-gray-300 capitalize">{weather.description}</span>
              </div>
              {weather.feels_like && Math.abs(weather.temperature - weather.feels_like) > 3 && (
                <div className="text-sm text-gray-400 mt-1">
                  Feels like {Math.round(weather.feels_like)}{tempSymbol}
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
          {/* Temperature Details */}
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-cyan-400 mb-3">
              <Thermometer className="w-4 h-4" />
              <span>Temperature</span>
            </div>
            <div className="pl-6 grid grid-cols-2 gap-4">
              <div className="bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Current</div>
                <div className="text-lg font-semibold text-white">
                  {Math.round(weather.temperature)}{tempSymbol}
                </div>
              </div>
              {weather.feels_like && (
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">Feels Like</div>
                  <div className="text-lg font-semibold text-white">
                    {Math.round(weather.feels_like)}{tempSymbol}
                  </div>
                </div>
              )}
              {weather.temp_min && (
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">Min</div>
                  <div className="text-lg font-semibold text-blue-300">
                    {Math.round(weather.temp_min)}{tempSymbol}
                  </div>
                </div>
              )}
              {weather.temp_max && (
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">Max</div>
                  <div className="text-lg font-semibold text-red-300">
                    {Math.round(weather.temp_max)}{tempSymbol}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Humidity & Pressure */}
          {(weather.humidity !== undefined || weather.pressure !== undefined) && (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-cyan-400 mb-3">
                <Droplets className="w-4 h-4" />
                <span>Atmospheric Conditions</span>
              </div>
              <div className="pl-6 grid grid-cols-2 gap-4">
                {weather.humidity !== undefined && (
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Humidity</div>
                    <div className="text-lg font-semibold text-white">{weather.humidity}%</div>
                  </div>
                )}
                {weather.pressure !== undefined && (
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Pressure</div>
                    <div className="text-lg font-semibold text-white">{weather.pressure} hPa</div>
                  </div>
                )}
                {weather.clouds !== undefined && (
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Cloud Coverage</div>
                    <div className="text-lg font-semibold text-white">{weather.clouds}%</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Wind */}
          {weather.wind_speed !== undefined && (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-cyan-400 mb-3">
                <Wind className="w-4 h-4" />
                <span>Wind</span>
              </div>
              <div className="pl-6 grid grid-cols-2 gap-4">
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">Speed</div>
                  <div className="text-lg font-semibold text-white">
                    {Math.round(weather.wind_speed)} {speedUnit}
                  </div>
                </div>
                {weather.wind_deg !== undefined && (
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Direction</div>
                    <div className="text-lg font-semibold text-white">
                      {getWindDirection(weather.wind_deg)} ({weather.wind_deg}°)
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Visibility */}
          {weather.visibility !== undefined && (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-cyan-400 mb-3">
                <Eye className="w-4 h-4" />
                <span>Visibility</span>
              </div>
              <div className="pl-6">
                <div className="bg-gray-800/50 rounded-lg p-3 inline-block">
                  <div className="text-lg font-semibold text-white">
                    {formatVisibility(weather.visibility)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Fetched Time */}
          {weather.fetched_at && (
            <div className="text-xs text-gray-500 text-center pt-2 border-t border-white/10">
              Weather data fetched at {new Date(weather.fetched_at).toLocaleString()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
