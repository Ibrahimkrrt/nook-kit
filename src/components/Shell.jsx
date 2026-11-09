import { useEffect, useMemo } from 'react';
import { MotionConfig } from 'motion/react';
import { House } from 'lucide-react';
import { applyPersona } from '../persona.js';
import { Sprite } from '../mascot/Mascot.jsx';
import { ToastProvider } from './Toast.jsx';
import { ConfirmProvider } from './Sheet.jsx';
import { MenuProvider } from './Menu.jsx';

/** Wrap every app once: applies the persona's colours, motion settings, toasts, confirm() and context menus. */
export function NookProvider({ persona, children }) {
  useEffect(() => {
    applyPersona(persona);
    if (persona?.app) document.title = persona.app;
  }, [persona]);
  return (
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <ConfirmProvider><MenuProvider>{children}</MenuProvider></ConfirmProvider>
      </ToastProvider>
    </MotionConfig>
  );
}

// small deterministic random, so stars don't jump around between renders
function seeded(seed) {
  let s = seed;
  return () => ((s = (s * 16807) % 2147483647) / 2147483647);
}

/** The living background: persona-tinted light, drifting aurora, pixel grid, stars, film grain. */
export function Scene({ stars = 46, seed = 7 }) {
  const dots = useMemo(() => {
    const r = seeded(seed);
    return Array.from({ length: stars }, () => ({
      left: `${r() * 100}%`, top: `${r() * 70}%`, delay: `${(r() * 3.2).toFixed(2)}s`, big: r() < 0.18,
    }));
  }, [stars, seed]);
  return (
    <div className="nk-scene" aria-hidden="true">
      <div className="nk-aurora a" />
      <div className="nk-aurora b" />
      <div className="nk-dots" />
      {dots.map((d, i) => (
        <i key={i} className={`nk-star${d.big ? ' big' : ''}`} style={{ left: d.left, top: d.top, animationDelay: d.delay }} />
      ))}
      <div className="nk-grain" />
    </div>
  );
}

/**
 * Standard app frame: scene + top bar (back to the Nook, app identity, actions) + main column.
 *   <AppShell persona={persona} actions={<Button…/>} width={760}>…</AppShell>
 */
export function AppShell({ persona, actions, width, home = '/', children }) {
  return (
    <div className="nk-shell" style={width ? { '--nk-width': `${width}px` } : undefined}>
      <Scene seed={persona?.id?.length || 7} />
      <header className="nk-bar">
        {home && (
          <a className="nk-bar-home" href={home} aria-label="Back to the Nook">
            <House size={16} aria-hidden="true" /><span>Nook</span>
          </a>
        )}
        {persona && (
          <div className="nk-bar-id">
            {persona.mascot && <Sprite def={persona.mascot} size={30} />}
            <div style={{ minWidth: 0, display: 'grid' }}>
              <b>{persona.app}</b>
              {persona.tagline && <small>{persona.tagline}</small>}
            </div>
          </div>
        )}
        <div className="nk-bar-end">{actions}</div>
      </header>
      <main className="nk-main">{children}</main>
    </div>
  );
}
