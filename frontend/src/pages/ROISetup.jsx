import React, { useState, useEffect, useRef } from 'react';
import { Stage, Layer, Rect, Image as KonvaImage } from 'react-konva';
import api from '../api/axios';
import { Badge, Button, Card } from '../components/Primitives';

const ROISetup = () => {
  const [snapshot, setSnapshot] = useState(null);
  const [rect, setRect] = useState(null);
  const stageRef = useRef();

  const cameraId = 1; // demo camera
  const gateId = 1;

  useEffect(() => {
    const fetchSnapshot = async () => {
      const res = await api.get(`/cameras/${cameraId}/snapshot`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const img = new window.Image();
      img.onload = () => setSnapshot(img);
      img.src = url;
    };
    fetchSnapshot();
  }, []);

  const handleMouseDown = (e) => {
    const { x, y } = e.target.getStage().getPointerPosition();
    setRect({ x, y, width: 0, height: 0 });
  };
  const handleMouseMove = (e) => {
    if (!rect) return;
    const { x, y } = e.target.getStage().getPointerPosition();
    setRect({ ...rect, width: x - rect.x, height: y - rect.y });
  };
  const handleMouseUp = () => {};

  const handleSave = async () => {
    if (!rect) return;
    const coords = [
      [rect.x, rect.y],
      [rect.x + rect.width, rect.y + rect.height],
    ];
    await api.post('/rois/', {
      gate_id: gateId,
      camera_id: cameraId,
      shape: 'rectangle',
      coordinates: coords,
    });
    alert('ROI saved');
  };

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="hero">
        <div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Spatial coverage</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>ROI Designer</div>
          <div style={{ fontSize: 14, color: 'var(--muted)' }}>Draw and tune gate regions with live snapshots.</div>
        </div>
        <Badge>Camera #{cameraId}</Badge>
      </div>

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
                  />
                )}
              </Layer>
            </Stage>
          </div>
        )}
        <div className="flex justify-between items-center" style={{ marginTop: 12 }}>
          <div className="muted">Tip: Aim to cover only the gate line to reduce false events.</div>
          <Button onClick={handleSave}>Save ROI</Button>
        </div>
      </Card>
    </div>
  );
};

export default ROISetup;
