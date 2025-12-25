import React, { useState } from 'react';
import api from '../api/axios';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/Primitives';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);
      const res = await api.post('/auth/login', params);
      localStorage.setItem('token', res.data.access_token);
      navigate('/');
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: '80px auto', textAlign: 'left' }} className="fade-up">
      <div className="hero shadow-strong">
        <div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Secure Access</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>CCTV Vehicle Analytics</div>
          <div style={{ fontSize: 14, color: 'var(--muted)' }}>Sign in to monitor cameras, ROI and events.</div>
        </div>
        <span className="pill success">Live</span>
      </div>
      <div className="panel card" style={{ marginTop: 18 }}>
        <form onSubmit={handleSubmit} className="grid" style={{ gap: 14 }}>
          <div>
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
            />
          </div>
          <div>
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          {error && <div className="pill danger">{error}</div>}
          <Button type="submit">Login</Button>
        </form>
      </div>
    </div>
  );
};

export default Login;
