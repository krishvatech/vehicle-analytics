import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/cameras', label: 'Cameras' },
  { to: '/roi', label: 'ROI Setup' },
  { to: '/events', label: 'Events' },
];

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };
  return (
    <header className="panel" style={{ padding: '12px 16px', marginBottom: 18, display: 'flex', alignItems: 'center', gap: 16, position: 'sticky', top: 0, zIndex: 10, backdropFilter: 'blur(10px)' }}>
      <div style={{ fontWeight: 700, letterSpacing: '0.03em', display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ display: 'inline-flex', width: 34, height: 34, alignItems: 'center', justifyContent: 'center', borderRadius: 10, background: 'linear-gradient(135deg, rgba(124,242,196,0.35), rgba(122,182,255,0.35))', border: '1px solid var(--border)' }}>CV</span>
        CCTV Vehicle Analytics
      </div>
      <nav style={{ display: 'flex', gap: 10, flex: 1 }}>
        {links.map((link) => {
          const active = location.pathname === link.to;
          return (
            <Link
              key={link.to}
              to={link.to}
              className="pill small"
              style={{
                borderColor: active ? 'rgba(124,242,196,0.6)' : 'var(--border)',
                color: active ? 'var(--text)' : 'var(--muted)',
                background: active ? 'rgba(124,242,196,0.12)' : 'rgba(255,255,255,0.04)',
              }}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
      <button className="button secondary" onClick={handleLogout}>Logout</button>
    </header>
  );
};

export default Navbar;
