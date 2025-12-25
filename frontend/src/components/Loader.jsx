import React from 'react';

const Loader = ({ size = 36 }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: '50%',
      border: '3px solid rgba(255,255,255,0.14)',
      borderTopColor: 'var(--accent)',
      animation: 'spin 1s linear infinite',
      margin: '0 auto',
    }}
  />
);

export default Loader;
