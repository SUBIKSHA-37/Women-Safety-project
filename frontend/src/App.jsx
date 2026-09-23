import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Bug } from 'lucide-react';

import Navbar from './components/Navbar';
import RouteForm from './components/RouteForm';
import MapView from './components/MapView';
import SafetyInfo from './components/SafetyInfo';
import SOSButton from './components/SOSButton';
import Loader from './components/Loader';
import RouteOptions from './components/RouteOptions';

// ✅ FIXED API URL (important)
const API_URL = import.meta.env.VITE_API_URL || 'https://nila-backend-production-6ea1.up.railway.app';

// distance calculation
const distance = (a, b) => {
  const r = Math.PI / 180;
  const x = (b.lat - a.lat) * r;
  const y = (b.lon - a.lon) * r;
  return 6371000 * Math.sqrt(
    x * x +
    Math.cos(a.lat * r) * Math.cos(b.lat * r) * y * y
  );
};

export default function App() {

  const [form, setForm] = useState({
    city: 'Chennai',
    source: 'Anna Nagar, Chennai',
    destination: 'Avadi, Chennai'
  });

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [userLocation, setUserLocation] = useState(null);
  const [selectedId, setSelectedId] = useState('safest');

  const [alert, setAlert] = useState(null);
  const [debug, setDebug] = useState(false);

  const selected = useMemo(
    () =>
      data?.routes?.find(r => r.id === selectedId) ||
      data?.best_route,
    [data, selectedId]
  );

  // 📍 User live location tracking
  useEffect(() => {
    if (!navigator.geolocation) return;

    const id = navigator.geolocation.watchPosition(
      (p) =>
        setUserLocation({
          lat: p.coords.latitude,
          lon: p.coords.longitude
        }),
      () =>
        setAlert({
          type: 'warn',
          text: 'Location unavailable. Enable location access.'
        }),
      { enableHighAccuracy: true, maximumAge: 8000, timeout: 12000 }
    );

    return () => navigator.geolocation.clearWatch(id);
  }, []);

  // 🚨 Safety alerts based on route
  useEffect(() => {
    if (!userLocation || !selected) return;

    const nearest = Math.min(
      ...selected.coordinates.map(([lat, lon]) =>
        distance(userLocation, { lat, lon })
      )
    );

    const zone = selected.risk_segments?.find(
      (s) =>
        distance(userLocation, {
          lat: (s.start[0] + s.end[0]) / 2,
          lon: (s.start[1] + s.end[1]) / 2
        }) < 250 && s.risk >= 6
    );

    if (zone) {
      setAlert({
        type: 'danger',
        text: '⚠️ Entering unsafe area. Switch to safe route.'
      });
    } else if (nearest > 120) {
      setAlert({
        type: 'warn',
        text: 'You are moving away from the safe route.'
      });
    } else {
      setAlert({
        type: 'safe',
        text: 'You are on a safe path.'
      });
    }
  }, [userLocation, selected]);

  function chooseRoute(id) {
    setSelectedId(id);
    setAlert(
      id === 'safest'
        ? {
            type: 'safe',
            text: 'Green route selected (recommended)'
          }
        : {
            type: 'warn',
            text: 'This route may be risky'
          }
    );
  }

  // 🚀 MAIN API CALL (already correct, improved logging)
  async function findRoute(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setData(null);

    try {
      console.log("Calling API:", API_URL);

      const response = await fetch(`${API_URL}/get_safe_route`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          source: form.source,
          destination: form.destination
        })
      });

      const json = await response.json();

      console.log("API Response:", json);

      if (!response.ok) {
        throw new Error(json.detail || 'Unable to analyze route');
      }

      setData(json);
      setSelectedId('safest');

      setAlert({
        type: 'safe',
        text: '✅ Safe route generated successfully'
      });

    } catch (err) {
      console.error("Error:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f7faf8]">

      <Navbar />

      <main className="grid min-h-[calc(100vh-64px)] lg:grid-cols-[390px_1fr]">

        {/* LEFT PANEL */}
        <aside className="p-5 md:p-7 lg:border-r border-slate-100">

          <div className="panel">
            <p className="eyebrow">Plan a safer journey</p>
            <h1>
              Move with more <em>confidence.</em>
            </h1>

            <p className="intro">
              Compare route choices using safety analysis.
            </p>

            <RouteForm
              form={form}
              setForm={setForm}
              onSubmit={findRoute}
              loading={loading}
            />
          </div>

          {loading && <Loader />}

          {error && <div className="error">{error}</div>}

          {data && (
            <>
              <RouteOptions
                routes={data.routes}
                selectedId={selectedId}
                onSelect={chooseRoute}
              />

              <button
                className={'debug-toggle ' + (debug ? 'on' : '')}
                onClick={() => setDebug(!debug)}
              >
                <Bug size={15} />
                Debug: {debug ? 'ON' : 'OFF'}
              </button>
            </>
          )}

          {alert && (
            <div className={'nav-alert ' + alert.type}>
              <AlertTriangle size={16} />
              {alert.text}
            </div>
          )}

          <SafetyInfo
            route={selected}
            tracking={!!userLocation && !!data}
          />
        </aside>

        {/* MAP SECTION */}
        <section className="relative min-h-[520px] p-5 lg:p-7">
          <MapView
            routes={data?.routes}
            source={data?.source}
            destination={data?.destination}
            userLocation={userLocation}
            selectedId={selectedId}
            onSelect={chooseRoute}
            debug={debug}
          />
        </section>

      </main>

      <SOSButton location={userLocation} />

    </div>
  );
}