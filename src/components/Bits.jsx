// Small presentational pieces: Card, Chip, Badge, Stat, Progress, Empty, Alert.
import { motion } from 'motion/react';
import { rise } from '../motion.js';

/** Glass surface. tone: undefined | "sunken" | "accent". `animate` gives it the standard rise-in. */
export function Card({ tone, pad, as: Tag = 'section', animate, className = '', children, ...rest }) {
  const props = { className: `nk-card ${className}`, 'data-tone': tone, 'data-pad': pad, ...rest };
  if (animate) {
    const M = motion[Tag] || motion.section;
    return <M variants={rise} initial="hidden" animate="show" {...props}>{children}</M>;
  }
  return <Tag {...props}>{children}</Tag>;
}

export function CardHead({ title, eyebrow, children }) {
  return (
    <header className="nk-card-head">
      <div>
        {eyebrow && <div className="nk-eyebrow">{eyebrow}</div>}
        {title && <h2>{title}</h2>}
      </div>
      {children && <div className="nk-row">{children}</div>}
    </header>
  );
}

export function Chip({ pressed, icon: Icon, count, children, ...rest }) {
  return (
    <button type="button" className="nk-chip" aria-pressed={pressed} {...rest}>
      {Icon && <Icon aria-hidden="true" />}
      {children}
      {count != null && <small>{count}</small>}
    </button>
  );
}

export function Badge({ tone, icon: Icon, dot, children }) {
  return (
    <span className="nk-badge" data-tone={tone}>
      {dot && <i className="nk-dot" aria-hidden="true" />}
      {Icon && <Icon aria-hidden="true" />}
      {children}
    </span>
  );
}

export function Stat({ value, label }) {
  return <div className="nk-stat"><b>{value}</b><span>{label}</span></div>;
}

/** Pixel-cell progress bar. Omit `value` (0–100) for an indeterminate shimmer. */
export function Progress({ value, cells = 24, label = 'Progress' }) {
  const on = value == null ? 0 : Math.round((Math.min(100, Math.max(0, value)) / 100) * cells);
  return (
    <div
      className="nk-progress" style={{ '--cells': cells }}
      role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100}
      aria-valuenow={value == null ? undefined : Math.round(value)}
      data-indeterminate={value == null ? '' : undefined}
    >
      {Array.from({ length: cells }, (_, i) => (
        <i key={i} className={i < on ? 'on' : ''} style={{ '--i': i, '--mix': `${Math.round((i / cells) * 100)}%` }} />
      ))}
    </div>
  );
}

export function Empty({ art, title, children, action }) {
  return (
    <div className="nk-empty">
      {art}
      {title && <h3>{title}</h3>}
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function Alert({ tone, icon: Icon, children }) {
  return (
    <div className="nk-alert" data-tone={tone} role={tone === 'danger' ? 'alert' : 'status'}>
      {Icon && <Icon aria-hidden="true" />}
      <div>{children}</div>
    </div>
  );
}
