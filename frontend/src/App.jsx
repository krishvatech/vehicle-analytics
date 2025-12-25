import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Cameras from './pages/Cameras';
import ROISetup from './pages/ROISetup';
import Events from './pages/Events';
import Dashboard from './pages/Dashboard';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  const token = localStorage.getItem('token');
  return (
    <div className="app-shell">
      {token && <Navbar />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={<ProtectedRoute element={<Dashboard />} />}
        />
        <Route
          path="/cameras"
          element={<ProtectedRoute element={<Cameras />} />}
        />
        <Route
          path="/roi"
          element={<ProtectedRoute element={<ROISetup />} />}
        />
        <Route
          path="/events"
          element={<ProtectedRoute element={<Events />} />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
