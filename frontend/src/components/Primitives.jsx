import React from 'react';

export const Card = ({ title, subtitle, action, children, className, style }) => (
  <div className={['panel card fade-up', className].filter(Boolean).join(' ')} style={style}>
    {(title || subtitle || action) && (
      <div className="flex justify-between items-center gap-md">
        <div>
          {title && <h3 className="card-title">{title}</h3>}
          {subtitle && <p className="card-subtitle">{subtitle}</p>}
        </div>
        {action}
      </div>
    )}
    {children}
  </div>
);

export const Button = ({ children, variant = 'primary', ...props }) => (
  <button className={['button', variant === 'secondary' && 'secondary'].filter(Boolean).join(' ')} {...props}>
    {children}
  </button>
);

export const Stat = ({ label, value, hint }) => (
  <div className="panel card fade-up">
    <div className="stat-value">{value}</div>
    <div className="stat-label">{label}</div>
    {hint && <div className="card-subtitle" style={{ marginTop: 6 }}>{hint}</div>}
  </div>
);

export const Badge = ({ children, tone = 'default' }) => (
  <span
    className={[
      'pill small',
      tone === 'success' && 'success',
      tone === 'danger' && 'danger',
    ]
      .filter(Boolean)
      .join(' ')}
  >
    {children}
  </span>
);

export const SectionHeader = ({ title, subtitle, actions }) => (
  <div className="flex justify-between items-center" style={{ marginBottom: 12 }}>
    <div>
      <div className="surface-title">{title}</div>
      {subtitle && <p className="surface-desc">{subtitle}</p>}
    </div>
    {actions}
  </div>
);
