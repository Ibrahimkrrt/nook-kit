import { useMemo } from 'react';
import { motion, useReducedMotion } from 'motion/react';

/**
 * A burst of pixel squares. Re-mount it (change `key`) to fire again.
 *   {done && <Confetti key={jobId} />}
 */
export function Confetti({ count = 28, spread = 180, colors }) {
  const reduce = useReducedMotion();
  const bits = useMemo(() => {
    const palette = colors || ['var(--accent)', 'var(--accent-2)', '#ffffff', 'var(--accent-text)'];
    return Array.from({ length: count }, (_, i) => {
      const a = (i / count) * Math.PI * 2 + Math.random() * 0.4;
      const d = spread * (0.45 + Math.random() * 0.55);
      return { x: Math.cos(a) * d, y: Math.sin(a) * d - spread * 0.25, r: Math.random() * 360, c: palette[i % palette.length], s: 5 + Math.round(Math.random() * 4) };
    });
  }, [count, spread, colors]);
  if (reduce) return null;
  return (
    <div className="nk-confetti" aria-hidden="true">
      {bits.map((b, i) => (
        <motion.i
          key={i}
          style={{ background: b.c, width: b.s, height: b.s }}
          initial={{ x: 0, y: 0, opacity: 1, rotate: 0, scale: 0.4 }}
          animate={{ x: b.x, y: [0, b.y, b.y + spread * 0.6], opacity: [1, 1, 0], rotate: b.r, scale: 1 }}
          transition={{ duration: 1.3, ease: [0.22, 1, 0.36, 1], times: [0, 0.45, 1] }}
        />
      ))}
    </div>
  );
}
