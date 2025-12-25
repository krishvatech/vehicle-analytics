import React from 'react';

const SnapshotModal = ({ open, onClose, src }) => {
  if (!open) return null;
  const isHttp = src && (src.startsWith('http://') || src.startsWith('https://'));
  const url = isHttp ? src : `http://${src}`;
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }} onClick={onClose}>
      <div className="panel" style={{ padding: 10, maxWidth: '90%', maxHeight: '90%' }} onClick={(e) => e.stopPropagation()}>
        <img src={url} alt="snapshot" style={{ maxWidth: '100%', maxHeight: '80vh', borderRadius: 12 }} />
        <div className="flex justify-between items-center" style={{ marginTop: 8 }}>
          <div className="muted">Snapshot preview</div>
          <button className="button secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

export default SnapshotModal;
