// A persona = an app's identity: name, colours, mascot sprite and voice.
// It lives in the app repo as web/src/persona.json, so the Nook can read it too
// (to draw the app's card) without importing any of the app's code.

/** CSS variables for a persona's colours (layer 3 of the tokens). */
export function personaVars(persona) {
  const c = persona?.colors || {};
  const vars = {};
  if (c.accent) vars['--accent'] = c.accent;
  if (c.accent2) vars['--accent-2'] = c.accent2;
  if (c.accentInk) vars['--accent-ink'] = c.accentInk;
  if (c.glowA) vars['--glow-a'] = c.glowA;
  if (c.glowB) vars['--glow-b'] = c.glowB;
  if (c.bg) vars['--bg'] = c.bg;
  return vars;
}

/** Put a persona's colours on <html>, so the page background and portals pick them up. */
export function applyPersona(persona) {
  const root = document.documentElement;
  for (const [k, v] of Object.entries(personaVars(persona))) root.style.setProperty(k, v);
  if (persona?.colors?.bg) document.querySelector('meta[name="theme-color"]')?.setAttribute('content', persona.colors.bg);
}

/**
 * Pick a line from the persona's voice and fill {placeholders}.
 *   say(persona, 'done', { title: 'Song' })
 * A key can hold one string or a list (a random one is picked, so the mascot doesn't repeat itself).
 */
export function say(persona, key, vars = {}, fallback = '') {
  const v = persona?.voice?.[key];
  const line = Array.isArray(v) ? v[Math.floor(Math.random() * v.length)] : v ?? fallback;
  return String(line).replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? ''));
}

/** Time-of-day key: 'night' | 'morning' | 'afternoon' | 'evening'. */
export function partOfDay(d = new Date()) {
  const h = d.getHours();
  if (h < 5) return 'night';
  if (h < 12) return 'morning';
  if (h < 18) return 'afternoon';
  return h < 23 ? 'evening' : 'night';
}
