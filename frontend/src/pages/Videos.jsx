import React, { useEffect, useMemo, useState } from 'react';
import api from '../api/axios';
import { Button, Card } from '../components/Primitives';

const Videos = () => {
  const [videos, setVideos] = useState([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const baseUrl = useMemo(() => import.meta.env.VITE_API_URL || 'http://localhost:8000', []);
  const maxUploadMb = 300;

  const loadVideos = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/videos/');
      setVideos(res.data || []);
    } catch (err) {
      console.error('videos list error', err);
      setError('Failed to load videos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVideos();
  }, []);

  const formatBytes = (bytes) => {
    if (!bytes && bytes !== 0) return '—';
    const units = ['B', 'KB', 'MB', 'GB'];
    let idx = 0;
    let value = bytes;
    while (value >= 1024 && idx < units.length - 1) {
      value /= 1024;
      idx += 1;
    }
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[idx]}`;
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!title.trim() || !file) {
      setError('Title and video file are required.');
      return;
    }
    setUploading(true);
    setError('');
    try {
      const form = new FormData();
      form.append('title', title.trim());
      if (description.trim()) {
        form.append('description', description.trim());
      }
      form.append('file', file);
      await api.post('/videos/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setTitle('');
      setDescription('');
      setFile(null);
      await loadVideos();
    } catch (err) {
      console.error('upload error', err);
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      if (status === 413) {
        const sizeLabel = file ? formatBytes(file.size) : 'Unknown size';
        setError(`File too large (${sizeLabel}). Max allowed ${maxUploadMb} MB.`);
      } else if (detail) {
        setError(detail);
      } else {
        setError('Upload failed. Please try again.');
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="hero">
        <div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Review queue</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>Videos</div>
          <div style={{ fontSize: 14, color: 'var(--muted)' }}>Upload and review recorded clips.</div>
        </div>
        <div className="flex gap-md">
          <Button variant="secondary" onClick={loadVideos}>Refresh</Button>
        </div>
      </div>

      <Card title="Add video" subtitle="MP4 or WebM up to the configured size limit">
        <form className="grid two" style={{ gap: 12 }} onSubmit={handleUpload}>
          <div>
            <label>Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Yard entry clip" />
          </div>
          <div>
            <label>Description (optional)</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Context for the clip" />
          </div>
          <div className="grid" style={{ gap: 8 }}>
            <label>File</label>
            <input type="file" accept="video/mp4,video/webm" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
          <div className="flex gap-md items-center" style={{ alignSelf: 'flex-end' }}>
            <Button type="submit" disabled={uploading}>{uploading ? 'Uploading...' : 'Upload'}</Button>
            {error && <div className="muted">{error}</div>}
          </div>
        </form>
      </Card>

      <Card title="Video library" subtitle={loading ? 'Loading videos...' : `${videos.length} videos`}>
        {videos.length === 0 && !loading && <div className="muted">No videos uploaded yet.</div>}
        <div className="grid two" style={{ gap: 16 }}>
          {videos.map((video) => {
            const token = localStorage.getItem('token');
            const src = `${baseUrl}/videos/${video.id}/file?token=${token || ''}`;
            return (
              <div key={video.id} className="panel" style={{ padding: 12, borderRadius: 16 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{video.title}</div>
                {video.description && <div className="muted" style={{ marginBottom: 6 }}>{video.description}</div>}
                <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
                  {new Date(video.created_at).toLocaleString()} • {formatBytes(video.size_bytes)}
                </div>
                <video controls style={{ width: '100%', borderRadius: 12 }}>
                  <source src={src} type={video.mime_type} />
                </video>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};

export default Videos;
