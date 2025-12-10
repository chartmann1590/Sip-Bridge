import { Cloud, Droplets, Wind, Thermometer } from 'lucide-react';

interface WeatherCardProps {
  weather: {
    id: number;
    location: string;
    country?: string;
    temperature: number;
    feels_like?: number;
    description: string;
    main: string;
    humidity?: number;
    wind_speed?: number;
    units: string;
  };
  onClick: () => void;
}

export function WeatherCard({ weather, onClick }: WeatherCardProps) {
  // Determine temperature units symbol
  const unitsSymbol = weather.units === 'imperial' ? '°F' : weather.units === 'metric' ? '°C' : 'K';

  // Determine icon based on weather type
  const getWeatherIcon = () => {
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
      default:
        return '🌤️';
    }
  };

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 px-3 py-2 mx-1 my-0.5 rounded-lg bg-cyan-500/20 border border-cyan-500/30 hover:bg-cyan-500/30 transition-all duration-200 text-sm group"
    >
      <div className="text-2xl">{getWeatherIcon()}</div>

      <div className="flex flex-col items-start text-left">
        <span className="text-cyan-100 font-medium leading-tight">
          {weather.location}{weather.country ? `, ${weather.country}` : ''}
        </span>

        <div className="flex items-center gap-2 text-xs text-cyan-300/80">
          <Thermometer className="w-3 h-3" />
          <span>
            {Math.round(weather.temperature)}{unitsSymbol}
            {weather.feels_like && Math.abs(weather.temperature - weather.feels_like) > 3 && (
              <span className="text-cyan-300/60 ml-1">(feels {Math.round(weather.feels_like)}{unitsSymbol})</span>
            )}
          </span>
        </div>

        <div className="flex items-center gap-1 text-xs text-cyan-300/70 capitalize">
          <Cloud className="w-3 h-3" />
          <span>{weather.description}</span>
        </div>

        {(weather.humidity || weather.wind_speed) && (
          <div className="flex items-center gap-3 text-xs text-cyan-300/60 mt-0.5">
            {weather.humidity && (
              <div className="flex items-center gap-1">
                <Droplets className="w-3 h-3" />
                <span>{weather.humidity}%</span>
              </div>
            )}
            {weather.wind_speed && (
              <div className="flex items-center gap-1">
                <Wind className="w-3 h-3" />
                <span>{Math.round(weather.wind_speed)} {weather.units === 'imperial' ? 'mph' : 'm/s'}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </button>
  );
}
