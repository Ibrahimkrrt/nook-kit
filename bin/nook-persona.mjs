#!/usr/bin/env node
// Persona tooling.
//   nook-persona check web/src/persona.json        validate (exit 1 on problems)
//   nook-persona sheet a.json b.json > moods.html  every mood of every mascot, for eyeballing
//   nook-persona icon web/src/persona.json > web/public/icon.svg   the mascot as an app icon
import { readFileSync } from 'node:fs';
import { compose, MOODS } from '../src/mascot/sprite.js';

const [cmd, ...files] = process.argv.slice(2);
const HEX = /^#[0-9a-f]{6}$/i;
const VOICE_REQUIRED = ['poke'];

export function check(p) {
  const errs = [];
  for (const k of ['id', 'app', 'tagline', 'colors', 'mascot', 'voice']) if (!p[k]) errs.push(`missing "${k}"`);
  if (p.id && !/^[a-z][a-z0-9-]{1,23}$/.test(p.id)) errs.push(`id "${p.id}" must be lowercase letters/numbers/-`);
  for (const k of ['accent', 'accent2', 'accentInk', 'bg']) if (!HEX.test(p.colors?.[k] || '')) errs.push(`colors.${k} must be #rrggbb`);
  const m = p.mascot || {};
  if (!m.name) errs.push('mascot.name missing');
  if (!Array.isArray(m.rows) || !m.rows.length) errs.push('mascot.rows missing');
  else {
    const w = m.rows[0].length;
    m.rows.forEach((r, y) => {
      if (r.length !== w) errs.push(`mascot.rows[${y}] is ${r.length} wide, expected ${w}`);
      for (const ch of r) if (ch !== '.' && !m.palette?.[ch]) errs.push(`mascot.rows[${y}] uses "${ch}" which isn't in the palette`);
    });
    const [ex, ey] = m.eye || [];
    if (!(ex >= 1 && ex < w / 2 && ey >= 1 && ey < m.rows.length - 2)) errs.push('mascot.eye must be the LEFT eye, inside the sprite');
    const [mx, my] = m.mouth || [];
    if (!(mx >= 1 && mx < w - 2 && my >= 1 && my < m.rows.length)) errs.push('mascot.mouth must be inside the sprite');
    if (w % 2 && m.mouth) errs.push('odd width: mouth/eyes cannot be symmetric, use an even width');
    if (m.mouth && mx !== w / 2 - 1) errs.push(`mascot.mouth x should be ${w / 2 - 1} (centred)`);
  }
  for (const k of Object.keys(m.palette || {})) if (!HEX.test(m.palette[k])) errs.push(`mascot.palette.${k} must be #rrggbb`);
  for (const k of VOICE_REQUIRED) if (!p.voice?.[k]) errs.push(`voice.${k} missing`);
  return errs;
}

function svg(def, mood, px = 8) {
  const f = MOODS[mood];
  const { w, h, rects } = compose(def, f.eyes, Array.isArray(f.mouth) ? f.mouth[0] : f.mouth);
  return `<svg width="${w * px}" height="${h * px}" viewBox="0 0 ${w} ${h}" shape-rendering="crispEdges">${rects
    .map((r) => `<rect x="${r.x}" y="${r.y}" width="${r.w}" height="1" fill="${r.fill}"/>`).join('')}</svg>`;
}

const personas = files.map((f) => JSON.parse(readFileSync(f, 'utf8')));
if (cmd === 'check') {
  let bad = 0;
  personas.forEach((p, i) => {
    const errs = check(p);
    console.log(errs.length ? `✖ ${files[i]}\n  - ${errs.join('\n  - ')}` : `✔ ${files[i]} (${p.mascot.name})`);
    bad += errs.length;
  });
  process.exit(bad ? 1 : 0);
} else if (cmd === 'sheet') {
  const rows = personas.map((p) => `<section style="background:${p.colors.bg}"><h2 style="color:${p.colors.accent}">${p.app} · ${p.mascot.name}</h2><div class="g">${Object.keys(MOODS)
    .map((m) => `<figure>${svg(p.mascot, m)}<figcaption>${m}</figcaption></figure>`).join('')}</div></section>`).join('');
  console.log(`<!doctype html><meta charset="utf-8"><style>body{margin:0;font:13px system-ui;color:#ccc;background:#000}section{padding:16px 20px}h2{margin:0 0 10px;font-size:15px}.g{display:flex;gap:18px;flex-wrap:wrap}figure{margin:0;text-align:center}svg{display:block}</style>${rows}`);
} else if (cmd === 'icon') {
  const p = personas[0];
  const { w, h, rects } = compose(p.mascot, 'open', 'smile');
  const size = Math.max(w, h) + 4;
  const ox = Math.floor((size - w) / 2), oy = Math.floor((size - h) / 2); // whole pixels only, or edges blur
  console.log(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" shape-rendering="crispEdges"><rect width="${size}" height="${size}" rx="${size * 0.22}" fill="${p.colors.bg}"/>${rects
    .map((r) => `<rect x="${r.x + ox}" y="${r.y + oy}" width="${r.w}" height="1" fill="${r.fill}"/>`).join('')}</svg>`);
} else {
  console.log('usage: nook-persona check|sheet|icon <persona.json>…');
  process.exit(2);
}
