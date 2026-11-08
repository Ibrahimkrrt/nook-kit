import { AnimatePresence, motion } from 'motion/react';
import { useTypewriter } from '../hooks.js';
import { spring } from '../motion.js';

/**
 * The mascot's speech bubble. Types the line out; screen readers get the full line at once.
 *   <Speech text="nom nom… 42%" sub="Song title" tail="left" />
 */
export function Speech({ text, sub, tail = 'left', className = '' }) {
  const [shown, done] = useTypewriter(text);
  return (
    <div className={`nk-speech ${className}`} data-tail={tail}>
      <span className="nk-sr" aria-live="polite">{text}{sub ? `. ${sub}` : ''}</span>
      <span aria-hidden="true">
        {shown}
        {!done && <i className="nk-caret" />}
      </span>
      <AnimatePresence mode="wait">
        {sub && done && (
          <motion.small key={sub} aria-hidden="true" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.snappy}>
            {sub}
          </motion.small>
        )}
      </AnimatePresence>
    </div>
  );
}
