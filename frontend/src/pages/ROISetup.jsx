import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Stage, Layer, Rect, Image as KonvaImage } from 'react-konva';
import api from '../api/axios';
import { Badge, Button, Card } from '../components/Primitives';

const ROISetup = () => {
  const [cameras, setCameras] = useState([]);
  const [cameraId, setCameraId] = useState(null);
  const [gateId, setGateId] = useState(null);

  const [snapshot, setSnapshot] = useState(null);
  const [rect, setRect] = useState(null);
  const [loadingSnap, setLoadingSnap] = useState(false);
  const [error, setError] = useState('');

  const stageRef = useRef();

  // Load cameras and select first one
  useEffect(() => {
    (async () => {
      try {
        setError('');
        const res = await api.get('/cameras/');
        const list = res.data || [];
        setCameras(list);

        if (list.length > 0) {
          setCameraId(list[0].id);
          setGateId(list[0].gate_id);
        } else {
          setCameraId(null);
          setGateId(null);
          setSnapshot(null);
        }
      } catch (e) {
        setError(e?.response?.data?.detail || e.message || 'Failed to load cameras');
      }
    })();
  }, []);

  // Fetch snapshot + existing ROI whenever camera changes
  useEffect(() => {
    if (!cameraId) return;

    let revokedUrl = null;

    (async () => {
      try {
        setError('');
        setLoadingSnap(true);
        setSnapshot(null);

        // Update gateId from selected camera
        const selected = cameras.find((c) => c.id === cameraId);
        if (selected) setGateId(selected.gate_id);

        // snapshot
        const snapRes = await api.get(`/cameras/${cameraId}/snapshot`, { responseType: 'blob' });
        const url = URL.createObjectURL(snapRes.data);
        revokedUrl = url;

        const img = new window.Image();
        img.onload = () => setSnapshot(img);
        img.onerror = () => setError('Snapshot failed to load');
        img.src = url;

        // existing ROI (optional)
        const gId = selected?.gate_id ?? gateId ?? 1;
        try {
          const roiRes = await api.get(`/rois/${gId}/${cameraId}`);
          const roi = roiRes.data;

          // ROI format in backend is [[x1,y1],[x2,y2]]
          if (roi?.coordinates?.length >= 2) {
            const [a, b] = roi.coordinates;
            const x1 = a[0], y1 = a[1];
            const x2 = b[0], y2 = b[1];
            setRect({ x: x1, y: y1, width: x2 - x1, height: y2 - y1 });
          }
        } catch {
          // no ROI yet is fine
          setRect(null);
        }
      } catch (e) {
        setError(e?.response?.data?.detail || e.message || 'Failed to load snapshot');
      } finally {
        setLoadingSnap(false);
      }
    })();

    return () => {
      if (revokedUrl) URL.revokeObjectURL(revokedUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraId]);

  const selectedCamera = useMemo(
    () => cameras.find((c) => c.id === cameraId),
    [cameras, cameraId],
  );

  const handleMouseDown = (e) => {
    if (!snapshot) return;
    const pos = e.target.getStage().getPointerPosition();
    if (!pos) return;
    setRect({ x: pos.x, y: pos.y, width: 0, height: 0 });
  };

  const handleMouseMove = (e) => {
    if (!rect || !snapshot) return;
    const pos = e.target.getStage().getPointerPosition();
    if (!pos) return;
    setRect({ ...rect, width: pos.x - rect.x, height: pos.y - rect.y });
  };

  const handleSave = async () => {
    if (!rect || !cameraId || !gateId) return;

    // normalize rect (support dragging backwards)
    const x1 = Math.round(Math.min(rect.x, rect.x + rect.width));
    const y1 = Math.round(Math.min(rect.y, rect.y + rect.height));
    const x2 = Math.round(Math.max(rect.x, rect.x + rect.width));
    const y2 = Math.round(Math.max(rect.y, rect.y + rect.height));

    if ((x2 - x1) < 5 || (y2 - y1) < 5) {
      alert('ROI too small');
      return;
    }

    try {
      setError('');
      await api.post('/rois/', {
        gate_id: gateId,
        camera_id: cameraId,
        shape: 'rectangle',
        coordinates: [[x1, y1], [x2, y2]],
      });
      alert('ROI saved');
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to save ROI');
    }
  };

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="hero">
        <div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Spatial coverage</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>ROI Designer</div>
          <div style={{ fontSize: 14, color: 'var(--muted)' }}>
            Draw and tune gate regions with live snapshots.
          </div>
        </div>

        <div className="flex items-center gap-md">
          <select
            value={cameraId || ''}
            onChange={(e) => setCameraId(Number(e.target.value))}
            style={{ width: 220 }}
          >
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} — {c.name}
              </option>
            ))}
          </select>
          <Badge>{cameraId ? `Camera #${cameraId}` : 'No Camera'}</Badge>
        </div>
      </div>

      <Card title="Draw ROI" subtitle="Click-drag to mark the gate rectangle">
        {error && (
          <div className="panel" style={{ padding: 10, borderRadius: 12, marginBottom: 12 }}>
            <div style={{ color: 'var(--danger, #ff7a7a)' }}>{error}</div>
          </div>
        )}

        {(!snapshot || loadingSnap) && (
          <div className="shimmer panel" style={{ height: 280, borderRadius: 12 }} />
        )}

        {snapshot && (
          <div className="panel" style={{ padding: 10, borderRadius: 16, overflow: 'auto' }}>
            <Stage
              width={snapshot.width}
              height={snapshot.height}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              ref={stageRef}
            >
              <Layer>
                <KonvaImage image={snapshot} />
                {rect && (
                  <Rect
                    x={rect.x}
                    y={rect.y}
                    width={rect.width}
                    height={rect.height}
                    stroke="#7cf2c4"
                    strokeWidth={3}
                    dash={[8, 4]}
                  />
                )}
              </Layer>
            </Stage>
          </div>
        )}

        <div className="flex justify-between items-center" style={{ marginTop: 12 }}>
          <div className="muted">
            Tip: Aim to cover only the gate line to reduce false events.
            {selectedCamera && (
              <span style={{ marginLeft: 10 }}>
                (Gate: {selectedCamera.gate_id})
              </span>
            )}
          </div>
          <Button onClick={handleSave} disabled={!cameraId || !gateId}>
            Save ROI
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default ROISetup;
