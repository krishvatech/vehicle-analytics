import React, { useEffect, useMemo, useState } from 'react';
import api from '../api/axios';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';
import { Badge, Button, Card, SectionHeader, Stat } from '../components/Primitives';
import Loader from '../components/Loader';

const Dashboard = () => {
  const [events, setEvents] = useState([]);
  const [snapshotUrl, setSnapshotUrl] = useState('');
  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(1);
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    gate_id: '',
    vehicle_type: '',
    entry_exit: '',
  });
  const [liveUrl, setLiveUrl] = useState(null);
  const [liveError, setLiveError] = useState('');
  const [liveLoading, setLiveLoading] = useState(false);
  const [videos, setVideos] = useState([]);
  const [videosLoading, setVideosLoading] = useState(false);
  const [videosError, setVideosError] = useState('');

  const baseUrl = useMemo(() => import.meta.env.VITE_API_URL || 'http://localhost:8000', []);

  const fetchEvents = async () => {
    const params = {};
    if (filters.start_date) params.start_date = new Date(filters.start_date).toISOString();
    if (filters.end_date) params.end_date = new Date(filters.end_date).toISOString();
    if (filters.gate_id) params.gate_id = filters.gate_id;
    if (filters.vehicle_type) params.vehicle_type = filters.vehicle_type;
    if (filters.entry_exit) params.entry_exit = filters.entry_exit;
    const res = await api.get('/events/', { params });
    setEvents(res.data);
  };

  useEffect(() => {
    fetchEvents();
    const t = setInterval(fetchEvents, 30000);
    return () => clearInterval(t);
  }, [filters]);

  const fetchSnapshot = async (camId = selectedCamera) => {
    try {
      const res = await api.get(`/cameras/${camId}/snapshot`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      setSnapshotUrl(url);
    } catch (err) {
      console.error('snapshot error', err);
    }
  };

  useEffect(() => {
    fetchSnapshot();
    const t = setInterval(() => fetchSnapshot(), 8000);
    return () => clearInterval(t);
  }, [selectedCamera]);

  useEffect(() => {
    const loadVideos = async () => {
      setVideosLoading(true);
      setVideosError('');
      try {
        const res = await api.get('/videos/');
        setVideos(res.data || []);
      } catch (err) {
        console.error('video list error', err);
        setVideosError('Unable to load videos.');
      } finally {
        setVideosLoading(false);
      }
    };
    loadVideos();
  }, []);

  // Load cameras and pick first as default
  useEffect(() => {
    const loadCameras = async () => {
      try {
        const res = await api.get('/cameras/');
        setCameras(res.data || []);
        if (res.data && res.data.length > 0) {
          setSelectedCamera(res.data[0].id);
        }
      } catch (err) {
        console.error('camera list error', err);
      }
    };
    loadCameras();
  }, []);

  // Build live URL with cache-busting and token; refresh query every few seconds
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setLiveUrl(null);
      return;
    }
    const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    setLiveLoading(true);
    setLiveUrl(`${base}/cameras/${selectedCamera}/mjpeg_live?token=${token}`);
  }, [selectedCamera]);

  const chartData = useMemo(() => {
    const counts = {};
    events.forEach((ev) => {
      const type = ev.vehicle_type || 'Unknown';
      counts[type] = (counts[type] || 0) + 1;
    });
    return Object.keys(counts).map((key) => ({ name: key, count: counts[key] }));
  }, [events]);

  const materialData = useMemo(() => {
    const counts = {};
    events.forEach((ev) => {
      const mat = ev.material_type || 'Unknown';
      counts[mat] = (counts[mat] || 0) + 1;
    });
    return Object.keys(counts).map((key) => ({ name: key, value: counts[key] }));
  }, [events]);

  const avgLoad = useMemo(() => {
    const loads = events.map((e) => Number(e.load_percentage || 0)).filter((n) => !Number.isNaN(n));
    if (!loads.length) return 0;
    return loads.reduce((a, b) => a + b, 0) / loads.length;
  }, [events]);

  const recentEvents = events.slice(0, 6);
  const totalEvents = events.length;
  const lastSnapshot = recentEvents[0]?.timestamp;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="hero fade-up">
        <div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Live Operations</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>Vehicle Analytics Control Room</div>
          <div style={{ fontSize: 14, color: 'var(--muted)' }}>
            Monitor stream health, ROI coverage and vehicle events in one pane.
          </div>
        </div>
        <div className="flex gap-md items-center">
          <Badge tone="success">Streams Active</Badge>
          <Button onClick={fetchEvents}>Refresh data</Button>
        </div>
      </div>

      <Card title="Camera selection" subtitle="Choose which camera to preview">
        <div className="grid two" style={{ gap: 12 }}>
          <div>
            <label>Camera</label>
            <select value={selectedCamera} onChange={(e) => setSelectedCamera(Number(e.target.value))}>
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>
                  #{c.id} — {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="muted" style={{ alignSelf: 'flex-end' }}>
            RTSP: {cameras.find((c) => c.id === selectedCamera)?.rtsp_url || '—'}
          </div>
        </div>
      </Card>

      <Card title="Filters" subtitle="Server-side filtering for charts and stats">
        <div className="grid two" style={{ gap: 12 }}>
          <div>
            <label>Start date/time</label>
            <input
              type="datetime-local"
              value={filters.start_date}
              onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
            />
          </div>
          <div>
            <label>End date/time</label>
            <input
              type="datetime-local"
              value={filters.end_date}
              onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
            />
          </div>
          <div>
            <label>Gate ID</label>
            <input
              type="number"
              value={filters.gate_id}
              onChange={(e) => setFilters({ ...filters, gate_id: e.target.value })}
              placeholder="1"
            />
          </div>
          <div>
            <label>Vehicle type</label>
            <input
              value={filters.vehicle_type}
              onChange={(e) => setFilters({ ...filters, vehicle_type: e.target.value })}
              placeholder="Truck, Car..."
            />
          </div>
          <div>
            <label>Direction</label>
            <input
              value={filters.entry_exit}
              onChange={(e) => setFilters({ ...filters, entry_exit: e.target.value })}
              placeholder="ENTRY or EXIT"
            />
          </div>
          <div className="flex gap-md items-center" style={{ alignSelf: 'flex-end' }}>
            <Button variant="secondary" onClick={() => setFilters({ start_date: '', end_date: '', gate_id: '', vehicle_type: '', entry_exit: '' })}>
              Clear
            </Button>
            <Button onClick={fetchEvents}>Apply</Button>
          </div>
        </div>
      </Card>

      <div className="grid three">
        <Stat label="Total events" value={totalEvents} hint="Across all cameras" />
        <Stat label="Cameras monitored" value="1" hint="Sample demo camera" />
        <Stat label="Last snapshot" value={lastSnapshot ? new Date(lastSnapshot).toLocaleTimeString() : '—'} hint="Latest event capture" />
      </div>

      <Card
        title="Vehicle mix"
        subtitle="Distribution by detected vehicle type"
      >
        <div className="chart-wrap">
          <ResponsiveContainer>
            <BarChart data={chartData} margin={{ top: 16, right: 24, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="name" stroke="var(--muted)" tickLine={false} />
              <YAxis allowDecimals={false} stroke="var(--muted)" tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: '#11182d', border: '1px solid var(--border)', borderRadius: 10 }} />
              <Legend />
              <Bar dataKey="count" fill="url(#barGradient)" radius={[6, 6, 0, 0]} />
              <defs>
                <linearGradient id="barGradient" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#7cf2c4" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="#7ab6ff" stopOpacity={0.95} />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="Recent activity" subtitle="Latest detections and metadata">
        <div className="grid two">
          <div className="panel card">
            <SectionHeader title="Timeline" subtitle="Newest to oldest" />
            <div className="grid" style={{ gap: 10 }}>
              {recentEvents.length === 0 && <div className="muted">No events yet.</div>}
              {recentEvents.map((ev) => (
                <div
                  key={ev.id}
                  className="panel card"
                  style={{ borderColor: 'rgba(255,255,255,0.08)' }}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <div style={{ fontWeight: 600 }}>{ev.vehicle_type || 'Unknown'}</div>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {new Date(ev.timestamp).toLocaleString()}
                      </div>
                    </div>
                    <Badge>{ev.entry_exit}</Badge>
                  </div>
                  <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
                    Gate #{ev.gate_id} • Camera #{ev.camera_id} • Confidence {ev.confidence ?? '—'}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="panel card">
            <SectionHeader title="Stream sentiment" subtitle="Smoothed activity curve" />
            <div className="chart-wrap">
              <ResponsiveContainer>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#7cf2c4" stopOpacity={0.7} />
                      <stop offset="95%" stopColor="#7ab6ff" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="name" stroke="var(--muted)" tickLine={false} />
                  <YAxis stroke="var(--muted)" tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: '#11182d', border: '1px solid var(--border)', borderRadius: 10 }} />
                  <Area type="monotone" dataKey="count" stroke="#7ab6ff" fillOpacity={1} fill="url(#areaGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Material & Load" subtitle="Breakdown and average load">
        <div className="grid two">
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={materialData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {materialData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={['#7cf2c4', '#7ab6ff', '#f7b267', '#ff6b6b', '#9d7afc'][index % 5]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#11182d', border: '1px solid var(--border)', borderRadius: 10 }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="panel card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <div className="surface-title">Average load</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{avgLoad.toFixed(1)}%</div>
            <div className="muted" style={{ marginTop: 6 }}>Based on reported load_percentage</div>
            <div style={{ marginTop: 12, height: 12, width: '100%', background: 'rgba(255,255,255,0.08)', borderRadius: 999, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${Math.min(100, Math.max(0, avgLoad))}%`, background: 'linear-gradient(90deg, #7cf2c4, #7ab6ff)' }} />
            </div>
          </div>
        </div>
      </Card>

      <Card title="Live preview" subtitle="Live MJPEG stream + periodic snapshot">
        <div className="flex gap-md items-center" style={{ marginBottom: 10 }}>
          <Button variant="secondary" onClick={() => fetchSnapshot()}>Refresh snapshot</Button>
          <div className="muted">Snapshot auto-refresh every 8s; MJPEG is continuous</div>
        </div>
        <div className="grid two" style={{ gap: 12 }}>
          <div className="panel" style={{ padding: 8 }}>
            <div className="card-subtitle" style={{ marginBottom: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Live stream</span>
              <span className="pill" style={{ animation: 'pulseGlow 2s infinite' }}>Live</span>
            </div>
            {liveUrl ? (
              <div className="panel" style={{ padding: 4, position: 'relative', minHeight: 220 }}>
                {liveLoading && (
                  <div className="loader-overlay">
                    <Loader size={36} />
                  </div>
                )}
                <img
                  key={liveUrl}
                  src={liveUrl}
                  alt="live stream"
                  style={{ width: '100%', borderRadius: 12 }}
                  onError={() => {
                    setLiveError('Unable to load stream. Check RTSP reachability and token.');
                    setLiveLoading(false);
                  }}
                  onLoad={() => {
                    setLiveError('');
                    setLiveLoading(false);
                  }}
                />
                {liveError && <div className="pill danger" style={{ marginTop: 6 }}>{liveError}</div>}
              </div>
            ) : (
              <div className="muted">Login to view live stream.</div>
            )}
          </div>
          <div className="panel" style={{ padding: 8 }}>
            <div className="card-subtitle" style={{ marginBottom: 6 }}>Latest snapshot</div>
            {snapshotUrl ? (
              <div className="panel" style={{ padding: 4 }}>
                <img src={snapshotUrl} alt="snapshot" style={{ width: '100%', borderRadius: 12 }} />
              </div>
            ) : (
              <div className="muted">No snapshot yet. Click refresh.</div>
            )}
          </div>
        </div>
      </Card>

      <Card title="Videos" subtitle="Uploaded clips">
        <div className="grid two" style={{ gap: 12 }}>
          {videosLoading && (
            <div className="panel" style={{ padding: 16 }}>
              <Loader size={32} />
            </div>
          )}
          {!videosLoading && videosError && (
            <div className="panel" style={{ padding: 16 }}>
              <div className="pill danger">{videosError}</div>
            </div>
          )}
          {!videosLoading && !videosError && videos.length === 0 && (
            <div className="panel" style={{ padding: 16 }}>
              <div className="muted">No videos uploaded yet.</div>
            </div>
          )}
          {!videosLoading && !videosError && videos.map((video) => {
            const token = localStorage.getItem('token');
            const src = `${baseUrl}/videos/${video.id}/file?token=${token || ''}`;
            return (
              <div key={video.id} className="panel" style={{ padding: 8 }}>
                <div className="card-subtitle" style={{ marginBottom: 6 }}>{video.title}</div>
                <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
                  {video.created_at ? new Date(video.created_at).toLocaleString() : '—'}
                </div>
                <div className="panel" style={{ padding: 4 }}>
                  <video controls preload="metadata" style={{ width: '100%', borderRadius: 12 }}>
                    <source src={src} type={video.mime_type} />
                  </video>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};

export default Dashboard;
