import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { Badge, Button, Card } from '../components/Primitives';

const Cameras = () => {
  const [cameras, setCameras] = useState([]);
  const [name, setName] = useState('');
  const [rtspUrl, setRtspUrl] = useState('');
  const [gateId, setGateId] = useState(1);

  const fetchCameras = async () => {
    const res = await api.get('/cameras/');
    setCameras(res.data);
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    await api.post('/cameras/', { name, rtsp_url: rtspUrl, gate_id: gateId });
    setName('');
    setRtspUrl('');
    fetchCameras();
  };

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="hero">
        <div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Device fabric</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>Cameras & Streams</div>
          <div style={{ fontSize: 14, color: 'var(--muted)' }}>Register RTSP endpoints and keep tabs on stream health.</div>
        </div>
        <Badge tone="success">Online</Badge>
      </div>

      <Card title="Add camera" subtitle="Attach a new RTSP feed to a gate">
        <form onSubmit={handleAdd} className="grid two" style={{ gap: 12 }}>
          <div>
            <label>Name</label>
            <input
              type="text"
              placeholder="North Gate"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div>
            <label>Gate ID</label>
            <input
              type="number"
              value={gateId}
              onChange={(e) => setGateId(Number(e.target.value))}
              min={1}
              required
            />
          </div>
          <div style={{ gridColumn: '1 / span 2' }}>
            <label>RTSP URL</label>
            <input
              type="text"
              placeholder="rtsp://..."
              value={rtspUrl}
              onChange={(e) => setRtspUrl(e.target.value)}
              required
            />
          </div>
          <div>
            <Button type="submit">Add camera</Button>
          </div>
        </form>
      </Card>

      <Card title="Registered cameras" subtitle="Active feeds in the system">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Gate</th>
              <th>RTSP URL</th>
            </tr>
          </thead>
          <tbody>
            {cameras.map((cam) => (
              <tr key={cam.id}>
                <td>{cam.id}</td>
                <td>{cam.name}</td>
                <td>{cam.gate_id}</td>
                <td className="muted">{cam.rtsp_url}</td>
              </tr>
            ))}
            {cameras.length === 0 && (
              <tr>
                <td colSpan="4" className="muted">No cameras added yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

export default Cameras;
