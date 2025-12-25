import React, { useState, useEffect, useMemo } from 'react';
import api from '../api/axios';
import { Badge, Button, Card } from '../components/Primitives';
import SnapshotModal from '../components/SnapshotModal';

const Events = () => {
  const [events, setEvents] = useState([]);
  const [rules, setRules] = useState([]);
  const [tagging, setTagging] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    plate_number: '',
    barcode_value: '',
    material_type: '',
    load_percentage: '',
  });
  const [preview, setPreview] = useState(null);
  const [newRule, setNewRule] = useState({ gate_id: '', channel: 'email', min_confidence: 0, directions: '', vehicle_types: '', recipients: '' });

  const saveRule = async () => {
    await api.post('/notifications/', null, { params: newRule });
    fetchRules();
  };

  const saveTags = async () => {
    if (!tagging) return;
    await api.post(`/events/${tagging.id}/tags`, {
      material_type: tagging.material_type,
      material_confidence: tagging.material_confidence ? Number(tagging.material_confidence) : null,
      load_percentage: tagging.load_percentage ? Number(tagging.load_percentage) : null,
      load_label: tagging.load_label,
      edit_reason: tagging.edit_reason,
    });
    setTagging(null);
    fetchEvents();
  };
  const [filters, setFilters] = useState({
    gate_id: '',
    vehicle_type: '',
    material_type: '',
    entry_exit: '',
    start_date: '',
    end_date: '',
  });

  const filteredEvents = useMemo(() => {
    return events.filter((ev) => {
      if (filters.gate_id && String(ev.gate_id) !== filters.gate_id) return false;
      if (filters.vehicle_type && ev.vehicle_type !== filters.vehicle_type) return false;
      if (filters.material_type && ev.material_type !== filters.material_type) return false;
      if (filters.entry_exit && ev.entry_exit !== filters.entry_exit) return false;
      if (filters.start_date && new Date(ev.timestamp) < new Date(filters.start_date)) return false;
      if (filters.end_date && new Date(ev.timestamp) > new Date(filters.end_date)) return false;
      return true;
    });
  }, [events, filters]);

  const loadBar = (pct) => {
    const val = Math.min(100, Math.max(0, Number(pct) || 0));
    const color = val > 75 ? '#7ab6ff' : val > 50 ? '#7cf2c4' : '#f7b267';
    return (
      <div style={{ minWidth: 120 }}>
        <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>{val.toFixed(0)}%</div>
        <div style={{ height: 8, background: 'rgba(255,255,255,0.08)', borderRadius: 999, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${val}%`, background: color }} />
        </div>
      </div>
    );
  };

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

  const fetchRules = async () => {
    try {
      const res = await api.get('/notifications/');
      setRules(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchEvents();
    fetchRules();
  }, []);

  const startEdit = (event) => {
    setEditingId(event.id);
    setFormData({
      plate_number: event.plate_number || '',
      barcode_value: event.barcode_value || '',
      material_type: event.material_type || '',
      load_percentage: event.load_percentage || '',
    });
  };
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };
  const saveEdit = async (id) => {
    await api.patch(`/events/${id}`, formData);
    setEditingId(null);
    fetchEvents();
  };

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="hero">
        <div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Event ledger</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>Vehicle Events</div>
          <div style={{ fontSize: 14, color: 'var(--muted)' }}>Review detections, correct metadata, and jump to snapshots.</div>
        </div>
        <div className="flex gap-md">
          <Badge tone="success">Live ingest</Badge>
          <Button variant="secondary" onClick={fetchEvents}>Refresh</Button>
        </div>
      </div>

      <Card title="All events" subtitle="Latest first">
        <div className="grid two" style={{ marginBottom: 10 }}>
          <input
            type="datetime-local"
            placeholder="Start date"
            value={filters.start_date}
            onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
          />
          <input
            type="datetime-local"
            placeholder="End date"
            value={filters.end_date}
            onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
          />
          <input
            placeholder="Gate ID"
            value={filters.gate_id}
            onChange={(e) => setFilters({ ...filters, gate_id: e.target.value })}
          />
          <input
            placeholder="Vehicle type"
            value={filters.vehicle_type}
            onChange={(e) => setFilters({ ...filters, vehicle_type: e.target.value })}
          />
          <input
            placeholder="Material"
            value={filters.material_type}
            onChange={(e) => setFilters({ ...filters, material_type: e.target.value })}
          />
          <input
            placeholder="Entry/Exit"
            value={filters.entry_exit}
            onChange={(e) => setFilters({ ...filters, entry_exit: e.target.value })}
          />
          <div className="flex gap-md">
            <Button variant="secondary" onClick={() => setFilters({ gate_id: '', vehicle_type: '', material_type: '', entry_exit: '', start_date: '', end_date: '' })}>Clear</Button>
            <Button onClick={fetchEvents}>Apply</Button>
          </div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Time</th>
              <th>Gate</th>
              <th>Camera</th>
              <th>Direction</th>
              <th>Type</th>
              <th>Plate</th>
              <th>Barcode</th>
              <th>Material</th>
              <th>Load %</th>
              <th>Snapshot</th>
              <th>Tag</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.map((ev) => (
              <tr key={ev.id}>
                <td>{ev.id}</td>
                <td className="muted">{new Date(ev.timestamp).toLocaleString()}</td>
                <td>{ev.gate_id}</td>
                <td>{ev.camera_id}</td>
                <td><Badge>{ev.entry_exit}</Badge></td>
                <td>{ev.vehicle_type}</td>
                <td>
                  {editingId === ev.id ? (
                    <input
                      name="plate_number"
                      value={formData.plate_number}
                      onChange={handleChange}
                    />
                  ) : (
                    ev.plate_number ? <Badge>{ev.plate_number}</Badge> : ''
                  )}
                </td>
                <td>
                  {editingId === ev.id ? (
                    <input
                      name="barcode_value"
                      value={formData.barcode_value}
                      onChange={handleChange}
                    />
                  ) : (
                    ev.barcode_value ? <Badge>{ev.barcode_value}</Badge> : ''
                  )}
                </td>
                <td>
                  {editingId === ev.id ? (
                    <input
                      name="material_type"
                      value={formData.material_type}
                      onChange={handleChange}
                    />
                  ) : (
                    ev.material_type ? <Badge>{ev.material_type}</Badge> : ''
                  )}
                </td>
                <td>
                  {editingId === ev.id ? (
                    <input
                      name="load_percentage"
                      value={formData.load_percentage}
                      onChange={handleChange}
                    />
                  ) : (
                    loadBar(ev.load_percentage)
                  )}
                </td>
                <td>
                  {ev.snapshot_path ? (
                  <Button variant="secondary" onClick={() => setPreview(ev.snapshot_path)}>View</Button>
                ) : (
                  ''
                )}
                </td>
                <td>
                  <Button variant="secondary" onClick={() => setTagging({ id: ev.id, material_type: ev.material_type || '', material_confidence: ev.material_confidence || '', load_percentage: ev.load_percentage || '', load_label: ev.load_label || '', edit_reason: '' })}>Tag</Button>
                </td>
                <td>
                  {editingId === ev.id ? (
                    <Button onClick={() => saveEdit(ev.id)}>Save</Button>
                  ) : (
                    <Button variant="secondary" onClick={() => startEdit(ev)}>Edit</Button>
                  )}
                </td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan="12" className="muted">No events yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <Card title="Notification rules" subtitle="Per-gate/per-channel">
        <div className="grid two" style={{ marginBottom: 10 }}>
          <input
            placeholder="Gate ID"
            value={newRule.gate_id || ''}
            onChange={(e) => setNewRule({ ...newRule, gate_id: e.target.value })}
          />
          <select value={newRule.channel} onChange={(e) => setNewRule({ ...newRule, channel: e.target.value })}>
            <option value="email">email</option>
            <option value="sms">sms</option>
          </select>
          <input
            placeholder="Min confidence"
            value={newRule.min_confidence || ''}
            onChange={(e) => setNewRule({ ...newRule, min_confidence: e.target.value })}
          />
          <input
            placeholder="Directions (ENTRY,EXIT)"
            value={newRule.directions || ''}
            onChange={(e) => setNewRule({ ...newRule, directions: e.target.value })}
          />
          <input
            placeholder="Vehicle types csv"
            value={newRule.vehicle_types || ''}
            onChange={(e) => setNewRule({ ...newRule, vehicle_types: e.target.value })}
          />
          <input
            placeholder="Recipients csv"
            value={newRule.recipients || ''}
            onChange={(e) => setNewRule({ ...newRule, recipients: e.target.value })}
          />
          <Button onClick={saveRule}>Save rule</Button>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Gate</th>
              <th>Channel</th>
              <th>Enabled</th>
              <th>Min conf</th>
              <th>Directions</th>
              <th>Vehicle types</th>
              <th>Recipients</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id}>
                <td>{r.gate_id}</td>
                <td>{r.channel}</td>
                <td>{String(r.enabled)}</td>
                <td>{r.min_confidence}</td>
                <td>{(r.directions || []).join(',')}</td>
                <td>{(r.vehicle_types || []).join(',')}</td>
                <td>{(r.recipients || []).join(',')}</td>
              </tr>
            ))}
            {rules.length === 0 && (
              <tr><td colSpan="7" className="muted">No rules</td></tr>
            )}
          </tbody>
        </table>
      </Card>
      <SnapshotModal open={!!preview} onClose={() => setPreview(null)} src={preview} />
      {tagging && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 40 }} onClick={() => setTagging(null)}>
          <div className="panel card" style={{ minWidth: 360 }} onClick={(e) => e.stopPropagation()}>
            <div className="surface-title">Tag event #{tagging.id}</div>
            <div className="grid" style={{ gap: 10, marginTop: 10 }}>
              <input
                placeholder="Material type"
                value={tagging.material_type}
                onChange={(e) => setTagging({ ...tagging, material_type: e.target.value })}
              />
              <input
                placeholder="Material confidence"
                value={tagging.material_confidence}
                onChange={(e) => setTagging({ ...tagging, material_confidence: e.target.value })}
              />
              <input
                placeholder="Load percentage"
                value={tagging.load_percentage}
                onChange={(e) => setTagging({ ...tagging, load_percentage: e.target.value })}
              />
              <input
                placeholder="Load label"
                value={tagging.load_label}
                onChange={(e) => setTagging({ ...tagging, load_label: e.target.value })}
              />
              <input
                placeholder="Edit reason"
                value={tagging.edit_reason}
                onChange={(e) => setTagging({ ...tagging, edit_reason: e.target.value })}
              />
              <div className="flex gap-md justify-between">
                <Button variant="secondary" onClick={() => setTagging(null)}>Cancel</Button>
                <Button onClick={saveTags}>Save tags</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Events;
