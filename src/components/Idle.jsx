import { useCallback, useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import { LockKeyhole, LogOut } from 'lucide-react';
import { Button } from './Button.jsx';
import { Sheet } from './Sheet.jsx';
import { spring } from '../motion.js';

/**
 * Inactivity logout for apps with accounts (pairs with nookkit.auth idle_minutes).
 *
 *   const idle = useIdle({ seconds: user.idle, channel: 'burrow', ping: () => api.post('/session/alive'),
 *                          onExpire: () => logout('idle'), paused: busy });
 *   <AppShell actions={<IdleBadge idle={idle} />}> … <IdleWarning idle={idle} onLogout={…} />
 *
 * - Counts down from `seconds`; any real use (click, key, scroll, touch, mouse move) starts it again.
 * - Works from a deadline, not ticks: a laptop that slept for an hour logs out the moment it wakes.
 * - Tabs of the same app share one clock (BroadcastChannel): activity in one keeps all alive, a logout in
 *   one logs out all.
 * - While the person is active, `ping` tells the server at most every 30 s, so reading a page without
 *   making requests doesn't let the server-side session expire.
 * - `paused` (e.g. while uploads run) holds the clock at full.
 */
const ACTIVITY = ['pointerdown', 'keydown', 'wheel', 'touchstart', 'scroll'];
const PING_EVERY = 30_000;

export function useIdle({ seconds, onExpire, ping, channel = 'nook', warnAt = 60, paused = false }) {
  const enabled = !!seconds;
  const deadline = useRef(Date.now() + (seconds || 0) * 1000);
  const lastPing = useRef(0);
  const lastMove = useRef(0);
  const lastShare = useRef(0);
  const expired = useRef(false);
  const bc = useRef(null);
  const [left, setLeft] = useState(seconds || 0);
  const cb = useRef({ onExpire, ping });
  cb.current = { onExpire, ping };

  const warning = enabled && !paused && left <= warnAt;
  const warnRef = useRef(warning);
  warnRef.current = warning;

  const restart = useCallback((fromOtherTab = false, at = Date.now()) => {
    if (!enabled || expired.current) return;
    deadline.current = at + seconds * 1000;
    setLeft(seconds);
    // scroll and wheel fire dozens of times a second: tell other tabs at most once a second
    if (!fromOtherTab && at - lastShare.current > 1000) {
      lastShare.current = at;
      bc.current?.postMessage({ type: 'active', at });
      if (at - lastPing.current > PING_EVERY) {
        lastPing.current = at;
        Promise.resolve(cb.current.ping?.()).catch(() => {});
      }
    }
  }, [enabled, seconds]);

  const expire = useCallback((fromOtherTab = false) => {
    if (expired.current) return;
    expired.current = true;
    if (!fromOtherTab) bc.current?.postMessage({ type: 'expired' });
    cb.current.onExpire?.(fromOtherTab ? 'other-tab' : 'idle');
  }, []);

  // one clock for every tab of this app
  useEffect(() => {
    if (!enabled || typeof BroadcastChannel === 'undefined') return undefined;
    const ch = new BroadcastChannel(`nook-idle-${channel}`);
    ch.onmessage = (e) => {
      if (e.data?.type === 'active') restart(true, e.data.at);
      if (e.data?.type === 'expired') expire(true);
    };
    bc.current = ch;
    return () => { ch.close(); bc.current = null; };
  }, [enabled, channel, restart, expire]);

  // a new limit (the user picked another delay) or pause → start counting again
  useEffect(() => { expired.current = false; restart(); }, [seconds, paused]); // eslint-disable-line react-hooks/exhaustive-deps

  // what counts as being there. While the warning shows, a mouse drifting past doesn't: only a real
  // click or key (or the button) says "I'm here".
  useEffect(() => {
    if (!enabled) return undefined;
    const active = () => restart();
    const moved = () => {
      const now = Date.now();
      if (warnRef.current || now - lastMove.current < 1000) return;
      lastMove.current = now;
      restart();
    };
    ACTIVITY.forEach((t) => addEventListener(t, active, { capture: true, passive: true }));
    addEventListener('pointermove', moved, { passive: true });
    return () => {
      ACTIVITY.forEach((t) => removeEventListener(t, active, { capture: true }));
      removeEventListener('pointermove', moved);
    };
  }, [enabled, restart]);

  // the clock itself
  useEffect(() => {
    if (!enabled) return undefined;
    const tick = () => {
      if (paused) { deadline.current = Date.now() + seconds * 1000; setLeft(seconds); return; }
      const s = Math.max(0, Math.ceil((deadline.current - Date.now()) / 1000));
      setLeft(s);
      if (s === 0) expire();
    };
    tick();
    const t = setInterval(tick, 1000);
    document.addEventListener('visibilitychange', tick);
    return () => { clearInterval(t); document.removeEventListener('visibilitychange', tick); };
  }, [enabled, seconds, paused, expire]);

  return { enabled, left, total: seconds || 0, warning, paused, stay: () => restart(), expire: () => expire() };
}

export const clock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

/** Small countdown pill for the top bar. Calm until the last minutes, then it warms up. */
export function IdleBadge({ idle, onClick }) {
  if (!idle?.enabled) return null;
  const frac = idle.total ? idle.left / idle.total : 1;
  const tone = idle.left <= 60 ? 'danger' : idle.left <= 180 ? 'warn' : undefined;
  const r = 7, c = 2 * Math.PI * r;
  return (
    <button
      type="button" className="nk-idle" data-tone={tone} onClick={onClick}
      aria-label={`Auto log out in ${clock(idle.left)}`} title="Logs you out after a while without activity"
    >
      <svg viewBox="0 0 18 18" aria-hidden="true">
        <circle cx="9" cy="9" r={r} className="nk-idle-track" />
        <circle cx="9" cy="9" r={r} className="nk-idle-ring" strokeDasharray={c} strokeDashoffset={c * (1 - frac)} />
      </svg>
      <span className="nk-mono">{clock(idle.left)}</span>
    </button>
  );
}

/** The "still there?" dialog for the final countdown. */
export function IdleWarning({ idle, onLogout, title = 'Still there?', children }) {
  if (!idle?.enabled) return null;
  return (
    <Sheet
      open={idle.warning} onClose={idle.stay} title={title} width={400}
      footer={(
        <>
          <Button variant="ghost" icon={LogOut} onClick={onLogout || idle.expire}>Log out now</Button>
          <Button variant="primary" onClick={idle.stay} data-autofocus>Stay signed in</Button>
        </>
      )}
    >
      <div className="nk-idle-warn">
        <motion.span className="nk-idle-big nk-mono" key={idle.left} initial={{ scale: 1.12, opacity: 0.6 }} animate={{ scale: 1, opacity: 1 }} transition={spring.snappy}>
          {clock(idle.left)}
        </motion.span>
        <p className="nk-muted"><LockKeyhole aria-hidden="true" /> {children || 'You’ll be logged out to keep things private.'}</p>
      </div>
    </Sheet>
  );
}
