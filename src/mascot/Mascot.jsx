import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { compose, MOODS } from './sprite.js';

/** Just the pixels, no animation. Handy for icons and tiny avatars. */
export function Sprite({ def, eyes = 'open', mouth = 'smile', size = 64, title }) {
  const { w, h, rects } = compose(def, eyes, mouth);
  return (
    <svg width={size} height={(size * h) / w} viewBox={`0 0 ${w} ${h}`} shapeRendering="crispEdges"
      role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true}>
      {rects.map((r, i) => <rect key={i} x={r.x} y={r.y} width={r.w} height={1} fill={r.fill} />)}
    </svg>
  );
}

// How each mood moves. `u` = one "mascot unit" (scales with size).
function moves(mood, u) {
  const loop = (duration, extra = {}) => ({ duration, repeat: Infinity, ease: 'easeInOut', ...extra });
  switch (mood) {
    case 'happy':
      return { body: { y: [0, -5 * u, 0, -2.5 * u, 0], scaleY: [1, 0.9, 1.05, 0.97, 1], scaleX: [1, 1.06, 0.97, 1.02, 1] }, t: loop(0.9, { repeatDelay: 0.5 }), shadow: { scale: [1, 0.7, 1, 0.85, 1] } };
    case 'love':
      return { body: { y: [0, -2 * u, 0], scale: [1, 1.04, 1] }, t: loop(1.2), shadow: { scale: [1, 0.88, 1] } };
    case 'working':
      return { body: { y: [0, -1.5 * u, 0], rotate: [-2.5, 2.5, -2.5] }, t: loop(0.5), shadow: { scale: [1, 0.92, 1] } };
    case 'thinking':
      return { body: { rotate: [0, -6, -6, -4, 0], y: [0, -u, -u, -u, 0] }, t: loop(3.2, { times: [0, 0.2, 0.6, 0.8, 1] }), shadow: { scale: 1 } };
    case 'surprised':
      return { body: { y: [0, -4 * u, 0], scale: [1, 1.12, 1] }, t: { duration: 0.42, ease: 'easeOut' }, shadow: { scale: [1, 0.7, 1] } };
    case 'sad':
      return { body: { y: [u, 1.6 * u, u], rotate: -3, scaleY: 0.96 }, t: loop(3.4), shadow: { scale: 1.04 } };
    case 'error':
      return { body: { x: [0, -2.5 * u, 2.5 * u, -1.8 * u, 1.8 * u, 0], rotate: [0, -4, 4, -2, 2, 0] }, t: { duration: 0.5 }, shadow: { scale: 1 } };
    case 'sleep':
      return { body: { scaleY: [1, 1.04, 1], scaleX: [1, 0.985, 1], y: u }, t: loop(3.4), shadow: { scale: [1.04, 1.08, 1.04] } };
    default: // idle
      return { body: { y: [0, -1.4 * u, 0] }, t: loop(2.8), shadow: { scale: [1, 0.9, 1] } };
  }
}

function Particles({ glyph, size }) {
  const reduce = useReducedMotion();
  if (reduce) return null;
  return [0, 1, 2].map((i) => (
    <motion.span
      key={`${glyph}${i}`}
      className="nk-particle"
      style={{ right: `${8 + i * 6}%`, top: '18%', fontSize: Math.max(12, size * (glyph === 'z' ? 0.14 : 0.12)) }}
      initial={{ opacity: 0, y: 0, x: 0, scale: 0.6 }}
      animate={{ opacity: [0, 1, 0], y: -size * 0.45, x: size * 0.12 * (i % 2 ? 1 : -0.4), scale: 1 }}
      transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.8, ease: 'easeOut' }}
      aria-hidden="true"
    >
      {glyph}
    </motion.span>
  ));
}

/**
 * An animated mascot.
 *   <Mascot def={persona.mascot} mood="working" size={160} onPoke={() => …} />
 * Moods: idle · happy · love · working · thinking · surprised · sad · error · sleep
 * `vt` sets a view-transition-name so the mascot morphs between the Nook and the app.
 */
export function Mascot({ def, mood = 'idle', size = 128, onPoke, label, vt, className = '' }) {
  const reduce = useReducedMotion();
  const face = MOODS[mood] || MOODS.idle;
  const [blinking, setBlinking] = useState(false);
  const [frame, setFrame] = useState(0);

  // natural blinking: every 2.5–5.5 s, 130 ms long
  useEffect(() => {
    if (!face.blink) return;
    let t1, t2;
    const loop = () => {
      t1 = setTimeout(() => {
        setBlinking(true);
        t2 = setTimeout(() => { setBlinking(false); loop(); }, 130);
      }, 2500 + Math.random() * 3000);
    };
    loop();
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [face.blink]);

  // mouth animation (chewing / talking) when the mood lists several mouths
  const mouths = Array.isArray(face.mouth) ? face.mouth : [face.mouth];
  useEffect(() => {
    setFrame(0);
    if (mouths.length < 2 || reduce) return;
    const id = setInterval(() => setFrame((f) => f + 1), 170);
    return () => clearInterval(id);
  }, [mood, mouths.length, reduce]);

  const eyes = blinking ? 'blink' : face.eyes;
  const mouth = mouths[frame % mouths.length];
  const u = size / 48;
  const m = useMemo(() => moves(mood, u), [mood, u]);

  return (
    <div
      className={`nk-mascot ${className}`}
      data-interactive={onPoke ? '' : undefined}
      style={{ '--aura': def.aura || 'var(--accent)', '--aura-blur': `${Math.round(size / 9)}px`, viewTransitionName: vt }}
    >
      <motion.div
        key={mood}
        className="nk-mascot-body"
        style={{ transformOrigin: '50% 100%' }}
        animate={reduce ? undefined : m.body}
        transition={m.t}
        whileTap={onPoke ? { scale: 0.9, transition: { type: 'spring', stiffness: 600, damping: 20 } } : undefined}
        onClick={onPoke}
        role={onPoke ? 'button' : undefined}
        tabIndex={onPoke ? 0 : undefined}
        onKeyDown={onPoke ? (e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onPoke()) : undefined}
        aria-label={onPoke ? `Poke ${def.name || 'the mascot'}` : undefined}
      >
        <Sprite def={def} eyes={eyes} mouth={mouth} size={size} title={label} />
      </motion.div>
      <motion.div className="nk-mascot-shadow" animate={reduce ? undefined : m.shadow} transition={m.t} />
      <AnimatePresence>{face.particles && <Particles key={mood} glyph={face.particles} size={size} />}</AnimatePresence>
    </div>
  );
}
