import React, { useState, useEffect, useRef } from 'react';
import { Stage, Layer, Rect, Image as KonvaImage } from 'react-konva';
import api from '../api/axios';
import { Badge, Button, Card } from '../components/Primitives';

const ROISetup = () => {
  const [cameras, setCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [rect, setRect] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [roiNormalized, setRoiNormalized] = useState(null);
  const stageRef = useRef();

  useEffect(() => {
    const loadCameras = async () => {
      try {
        const res = await api.get('/cameras/');
        const list = res.data || [];
        setCameras(list);
        if (list.length > 0) {
          setSelectedCameraId(list[0].id);
        }
      } catch (err) {
        console.error('camera list error', err);
      }
    };
    loadCameras();
  }, []);

  useEffect(() => {
    if (!selectedCameraId) return;
    setSnapshot(null);
    setRect(null);
    setRoiNormalized(null);
    const fetchSnapshot = async () => {
      const res = await api.get(`/cameras/${selectedCameraId}/snapshot`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const img = new window.Image();
      img.onload = () => setSnapshot(img);
      img.src = url;
    };
    const fetchRoi = async () => {
      try {
        const res = await api.get(`/cameras/${selectedCameraId}/roi`);
        setRoiNormalized(res.data);
      } catch (err) {
        if (err.response?.status !== 404) {
          console.error('roi load error', err);
        }
      }
    };
    fetchSnapshot();
    fetchRoi();
  }, [selectedCameraId]);

  useEffect(() => {
    if (!snapshot || !roiNormalized) return;
    setRect({
      x: roiNormalized.x * snapshot.width,
      y: roiNormalized.y * snapshot.height,
      width: roiNormalized.w * snapshot.width,
      height: roiNormalized.h * snapshot.height,
    });
  }, [snapshot, roiNormalized]);

  const normalizeRect = (raw) => {
    if (!raw) return null;
    const x = Math.min(raw.x, raw.x + raw.width);
    const y = Math.min(raw.y, raw.y + raw.height);
    const width = Math.abs(raw.width);
    const height = Math.abs(raw.height);
    return { x, y, width, height };
  };

  const handleMouseDown = (e) => {
    if (!snapshot) return;
    const { x, y } = e.target.getStage().getPointerPosition();
    setIsDrawing(true);
    setRect({ x, y, width: 0, height: 0 });
  };
  const handleMouseMove = (e) => {
    if (!rect || !isDrawing) return;
    const { x, y } = e.target.getStage().getPointerPosition();
    setRect({ ...rect, width: x - rect.x, height: y - rect.y });
  };
  const handleMouseUp = () => {
    if (!rect) return;
    setIsDrawing(false);
    setRect(normalizeRect(rect));
  };

  const handleSave = async () => {
    if (!rect || !snapshot || !selectedCameraId) return;
    const normalized = {
      x: rect.x / snapshot.width,
      y: rect.y / snapshot.height,
      w: rect.width / snapshot.width,
      h: rect.height / snapshot.height,
    };
    if (normalized.x < 0 || normalized.y < 0 || normalized.w <= 0 || normalized.h <= 0) {
      alert('ROI must be within the image bounds.');
      return;
    }
    if (normalized.x + normalized.w > 1 || normalized.y + normalized.h > 1) {
      alert('ROI must fit within the image bounds.');
      return;
    }
    try {
      await api.put(`/cameras/${selectedCameraId}/roi`, {
        ...normalized,
        coordinate_type: 'normalized',
      });
      setRoiNormalized(normalized);
      alert('ROI saved');
    } catch (err) {
      console.error('roi save error', err);
      alert(err.response?.data?.detail || 'Failed to save ROI');
    }
  };

  const handleClear = () => {
    setRect(null);
    setRoiNormalized(null);
  };

  const selectedCamera = cameras.find((cam) => cam.id === selectedCameraId);
  const normalizedValues = rect && snapshot
    ? {
      x: rect.x / snapshot.width,
      y: rect.y / snapshot.height,
      w: rect.width / snapshot.width,
      h: rect.height / snapshot.height,
    }
    : null;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="hero">
        <div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Spatial coverage</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>ROI Designer</div>
          <div style={{ fontSize: 14, color: 'var(--muted)' }}>Draw and tune gate regions with live snapshots.</div>
        </div>
        <Badge>{selectedCamera ? `Camera #${selectedCamera.id}` : 'Camera'}</Badge>
      </div>

      <Card title="Camera selection" subtitle="Pick the camera to configure">
        <div className="grid two" style={{ gap: 12 }}>
          <div>
            <label>Camera</label>
            <select value={selectedCameraId || ''} onChange={(e) => setSelectedCameraId(Number(e.target.value))}>
              <option value="" disabled>Select a camera</option>
              {cameras.map((cam) => (
                <option key={cam.id} value={cam.id}>
                  #{cam.id} — {cam.name}
                </option>
              ))}
            </select>
          </div>
          <div className="muted" style={{ alignSelf: 'flex-end' }}>
            {selectedCamera ? `RTSP: ${selectedCamera.rtsp_url}` : 'No camera selected'}
          </div>
        </div>
      </Card>

      <Card title="Draw ROI" subtitle="Click-drag to mark the gate rectangle">
        {!snapshot && <div className="shimmer panel" style={{ height: 280, borderRadius: 12 }} />}
        {snapshot && (
          <div className="panel" style={{ padding: 10, borderRadius: 16 }}>
            <Stage
              width={snapshot.width}
              height={snapshot.height}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
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
                    draggable={!isDrawing}
                    onDragEnd={(e) => {
                      const { x, y } = e.target.position();
                      setRect({ ...rect, x, y });
                    }}
                  />
                )}
              </Layer>
            </Stage>
          </div>
        )}
        {normalizedValues && (
          <div className="muted" style={{ marginTop: 8 }}>
            Normalized ROI: x={normalizedValues.x.toFixed(3)} y={normalizedValues.y.toFixed(3)} w={normalizedValues.w.toFixed(3)} h={normalizedValues.h.toFixed(3)}
          </div>
        )}
        <div className="flex justify-between items-center" style={{ marginTop: 12 }}>
          <div className="muted">Tip: Aim to cover only the gate line to reduce false events.</div>
          <div className="flex gap-md items-center">
            <Button variant="secondary" onClick={handleClear}>Clear</Button>
            <Button onClick={handleSave} disabled={!rect}>Save ROI</Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ROISetup;
