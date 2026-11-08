// Nook motion language, built on Motion (motion.dev).
// Principles (see docs/DESIGN.md → Motion):
//   * Springs, not durations, for anything the user touches.
//   * Enter from below (things "arrive"), leave by fading (they don't fly away).
//   * Mascots exaggerate; the UI stays calm.
//   * Everything respects prefers-reduced-motion (NookProvider sets reducedMotion="user").

export const spring = {
  snappy: { type: 'spring', stiffness: 520, damping: 34, mass: 0.7 },  // buttons, pills, toggles
  smooth: { type: 'spring', stiffness: 260, damping: 30 },             // cards, sheets, layout
  bouncy: { type: 'spring', stiffness: 380, damping: 16 },             // mascots, celebrations
  lazy:   { type: 'spring', stiffness: 120, damping: 20 },             // ambient things
};

export const ease = {
  out: [0.22, 1, 0.36, 1],
  inOut: [0.65, 0, 0.35, 1],
};

/** Fade + rise into place. Use for cards, list rows, sections. */
export const rise = {
  hidden: { opacity: 0, y: 14, filter: 'blur(4px)' },
  show: { opacity: 1, y: 0, filter: 'blur(0px)', transition: spring.smooth },
  exit: { opacity: 0, y: -6, filter: 'blur(2px)', transition: { duration: 0.16 } },
};

/** Small things that appear: badges, toasts, popovers. */
export const pop = {
  hidden: { opacity: 0, scale: 0.92 },
  show: { opacity: 1, scale: 1, transition: spring.snappy },
  exit: { opacity: 0, scale: 0.96, transition: { duration: 0.12 } },
};

/** Parent that staggers its children (children use `rise` or `pop`). */
export const stagger = (gap = 0.05, delay = 0) => ({
  hidden: {},
  show: { transition: { staggerChildren: gap, delayChildren: delay } },
});

/** Hover / press feel for interactive cards. */
export const lift = {
  whileHover: { y: -4, transition: spring.snappy },
  whileTap: { scale: 0.98, transition: spring.snappy },
};

export const press = { whileTap: { scale: 0.97 }, transition: spring.snappy };
