// Pixel mascot engine: turns a character grid + a mood into SVG rectangles.
//
// A mascot definition (persona.json → "mascot"):
//   {
//     "rows":    ["..oooo..", ...],     one char per pixel, "." = empty
//     "palette": { "o": "#1a0f2e", ... },
//     "eye":     [x, y],                LEFT eye anchor; the right eye is mirrored
//     "mouth":   [x, y],                left pixel of the 2-pixel-wide mouth centre
//     "ink":     "e"                    palette key used for eyes (default "e"); mouth uses "m" (falls back to ink)
//   }
// Faces are shared by every mascot, so moods look consistent across the whole Nook.

// Eye shapes for the LEFT eye, as [dx, dy] from the anchor. The right eye is mirrored (dx → -dx),
// except shapes marked `gaze`, which point the same way for both eyes.
export const EYES = {
  open:   [[0, 0], [0, 1]],
  blink:  [[-1, 1], [0, 1]],
  happy:  [[-1, 1], [0, 0], [1, 1]],
  closed: [[-1, 0], [0, 1], [1, 0]],
  wide:   [[0, 0], [0, 1], [1, 0], [1, 1]],
  sad:    [[0, 0], [0, 1], [-1, -1], [0, -2]],
  x:      [[-1, 0], [1, 0], [0, 1], [-1, 2], [1, 2]],
  side:   { gaze: true, px: [[1, 0], [1, 1]] },
};

// Mouth shapes as [dx, dy, paletteKey?] from the mouth anchor (default key "m").
export const MOUTHS = {
  smile:   [[-1, -1], [0, 0], [1, 0], [2, -1]],
  grin:    [[-1, -1], [0, -1], [1, -1], [2, -1], [0, 0, 't'], [1, 0, 't']],
  neutral: [[0, 0], [1, 0]],
  o:       [[0, -1], [1, -1], [0, 0], [1, 0]],
  frown:   [[0, -1], [1, -1], [-1, 0], [2, 0]],
  wavy:    [[-1, 0], [0, -1], [1, 0], [2, -1]],
};

// Mood → face. `mouth` can be a list: the mascot cycles through it (chewing, talking).
export const MOODS = {
  idle:      { eyes: 'open',   mouth: 'smile',           blink: true },
  happy:     { eyes: 'happy',  mouth: 'grin' },
  love:      { eyes: 'happy',  mouth: 'smile',           particles: '♥' },
  working:   { eyes: 'open',   mouth: ['o', 'neutral'],  blink: true },
  thinking:  { eyes: 'side',   mouth: 'neutral',         blink: true },
  surprised: { eyes: 'wide',   mouth: 'o' },
  sad:       { eyes: 'sad',    mouth: 'frown',           blink: true },
  error:     { eyes: 'x',      mouth: 'wavy' },
  sleep:     { eyes: 'closed', mouth: 'neutral',         particles: 'z' },
};

const cache = new Map();

/** Compose the final pixel grid for a mascot with a given face, as merged rectangles. */
export function compose(def, eyes = 'open', mouth = 'smile') {
  const key = `${def.name || ''}|${eyes}|${mouth}|${def.rows.length}`;
  if (cache.has(key)) return cache.get(key);

  const grid = def.rows.map((r) => r.split(''));
  const w = Math.max(...def.rows.map((r) => r.length));
  const h = grid.length;
  const ink = def.ink || 'e';
  const put = (x, y, ch) => { if (y >= 0 && y < h && x >= 0 && x < w) grid[y][x] = ch; };

  if (def.eye) {
    const shape = EYES[eyes] || EYES.open;
    const px = Array.isArray(shape) ? shape : shape.px;
    const gaze = !Array.isArray(shape) && shape.gaze;
    const [lx, ly] = def.eye;
    const rx = w - 1 - lx;
    for (const [dx, dy] of px) {
      put(lx + dx, ly + dy, ink);
      put(rx + (gaze ? dx : -dx), ly + dy, ink);
    }
  }
  if (def.mouth) {
    const [mx, my] = def.mouth;
    for (const [dx, dy, k] of MOUTHS[mouth] || MOUTHS.smile) put(mx + dx, my + dy, k || 'm');
  }

  // merge horizontal runs of the same colour → far fewer <rect>s
  const pal = { m: def.palette[ink], t: '#ff7a9a', ...def.palette };
  const rects = [];
  for (let y = 0; y < h; y++) {
    let x = 0;
    while (x < w) {
      const ch = grid[y][x];
      if (!ch || ch === '.' || ch === ' ' || !pal[ch]) { x++; continue; }
      let run = 1;
      while (x + run < w && grid[y][x + run] === ch) run++;
      rects.push({ x, y, w: run, fill: pal[ch] });
      x += run;
    }
  }
  const out = { w, h, rects };
  cache.set(key, out);
  return out;
}
