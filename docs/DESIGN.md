# Nook design system

> Cozy night-time desktop. Pixel souls, modern bodies.

Every app in the Nook is a **room** with its own character, but they're clearly part of one home.
The rule that makes both true: **the kit owns the system, the persona owns the personality.**

---

## 1. Principles

1. **Pixel souls, modern bodies.** Mascots, icons and display type are pixel art. Everything you
   *use* (buttons, inputs, text) is modern, readable and comfortable. Never set body text in a pixel font.
2. **One character per room.** Each app has a mascot with a name, a mood and a way of talking.
   The mascot reacts to what's happening (working, done, error) and can be poked.
3. **Calm UI, expressive mascot.** The interface moves gently; the mascot is allowed to overreact.
4. **Night, glass, glow.** Dark scenes, translucent surfaces, light coming from the persona's accent.
5. **Tactile.** Primary buttons have a pixel "step" shadow and press down 2px. Things you touch spring.
6. **Respect people.** Every motion honours `prefers-reduced-motion`. Every control has a label.
   Contrast stays readable. Phone first: 16px gutters, no sideways scrolling, 44px+ touch targets.

---

## 2. Tokens (three layers)

| Layer | Examples | Who sets it |
|---|---|---|
| **Primitives** | `--night-900`, `--mint-400` | the kit, never used directly by apps |
| **Semantic** | `--bg`, `--text`, `--text-2`, `--line`, `--fill-1..3`, `--surface`, `--sunken`, `--ok/warn/danger` | the kit |
| **Persona** | `--accent`, `--accent-2`, `--accent-ink`, `--glow-a`, `--glow-b`, `--bg` | the app's `persona.json` |

Derived automatically from the persona (never set by hand): `--accent-soft`, `--accent-softer`,
`--accent-line`, `--accent-deep`, `--accent-text`, `--surface`, `--surface-solid`, `--sunken`,
`--bubble`, `--glow`, `--ring`. If you tint an element with another persona (like app cards on the
home screen), add `className="nk-persona"` so the derived tokens follow.

**Type:** `--font-ui` Geist (everything you read), `--font-display` Pixelify Sans (names, headings,
eyebrows), `--font-mono` Geist Mono (numbers, times, sizes: always tabular).
Scale: `--t-2xs 11` · `xs 12` · `sm 13.5` · `md 15` · `lg 17` · `xl 22` · `2xl 30` · `3xl 42` · `4xl 56`.

**Space:** 4px grid, `--s-1` (4) … `--s-10` (64). Page gutter `--gutter` = clamp(16px, 4vw, 32px).
**Radius:** `--r-xs 6` · `sm 10` · `md 14` · `lg 20` (cards) · `xl 28` (hero cards, sheets) · `full`.
**Elevation:** `--hl` (top highlight on glass) + `--shadow-1/2/3`. Accent emphasis: `--glow`.

### Colour roles in a persona
- `accent`: the app's signature. Primary buttons, selected states, progress, mascot aura.
- `accent2`: a complementary second light. Aurora, secondary icons, progress gradient end.
- `accentInk`: text on top of `accent` (must be readable: aim for 7:1).
- `bg`: the app's night. Near-black, tinted toward the accent family. Surfaces derive from it.

---

## 3. Components (`@nook/kit`)

| Component | Use it for |
|---|---|
| `NookProvider persona` | Wrap the app once: persona colours, reduced motion, toasts, confirm(), context menus |
| `AppShell persona actions width` | Standard page: living scene, top bar (back to Nook, identity, actions), main column |
| `Scene` | The animated background on its own (the home screen uses it) |
| `Card tone="accent\|sunken" animate` / `CardHead` | Glass surfaces. `accent` = the hero card with the mascot |
| `Button variant="primary\|secondary\|ghost\|danger" size icon loading block href` | All buttons. One primary per view |
| `IconButton icon label` | Square icon buttons; `label` is required |
| `Field label aside hint error` + `Input icon` / `Select` | Forms, accessible by construction |
| `Segmented options` | 2–4 exclusive choices, with a sliding pill |
| `Chip pressed count icon` / `Badge tone dot` | Filters, quality pickers / small status |
| `Stat`, `Progress value cells`, `Empty`, `Alert` | Numbers, pixel-cell progress, empty states, warnings |
| `Sheet` / `useConfirm()` | Modal dialog (bottom sheet on phones) / promise-based yes-no |
| `useToast()` | Short confirmations: `toast({ title, description, tone })` |
| `useContextMenu()` | Right-click / long-press / Shift+F10 menus: `{...menu.bind(() => items)}` on a row, `menu.openAt(el, items)` from a "More" button. Items: `{ label, icon, onSelect, danger, disabled, hint }`, `'-'`, `{ heading }` |
| `Mascot def mood size onPoke vt` / `Sprite` | The animated character / static pixels |
| `Speech text sub` | The mascot's typewriter speech bubble |
| `Confetti` | Pixel burst for real achievements (download done), not for every click |

**Context menus are shortcuts, never the only way.** Every action in a menu must also be reachable without
it (a visible `Ellipsis` "More" button that opens the same items, a toolbar button…). Text fields and
selected text keep the browser's own menu; Shift+Alt+right-click always gets it too.

Icons: `import { Film } from '@nook/kit/icons'` (lucide, 1.5–2px strokes). Never emoji as UI icons.

App CSS is **layout only** (grid, gaps, sizes). Colour, type, radius, shadow and motion come from tokens.
Class prefix for app CSS: two letters of the app (`ch-`, `bw-`). The kit owns `nk-`.

---

## 4. Motion (Motion / motion.dev)

From `@nook/kit`: `spring.snappy | smooth | bouncy | lazy`, variants `rise`, `pop`, `stagger()`, `lift`.

| Moment | Motion |
|---|---|
| Page/section enters | `rise` (fade + 14px up + unblur), lists use `stagger(0.03–0.08)` |
| Small things appear | `pop` (scale .92 → 1, snappy) |
| Selection moves | `layoutId` pill (`Segmented`), `snappy` |
| Sheets | slide up 40px + scale .97 → 1, `smooth`; exit fast (150ms) |
| Hover on cards | lift −4..−6px, `snappy`; glow via CSS |
| Press | buttons drop 2px (CSS); cards scale .98 |
| Mascot | exaggerated per mood (hop, chew, shake, breathe): handled by `<Mascot>` |
| Between Nook and an app | View Transitions: the mascot morphs (`vt="mascot-<id>"` on the app's hero mascot) |

Rules: springs for anything touched; leave by fading, not flying; nothing loops in the UI except the
mascot, the scene and progress; `MotionConfig reducedMotion="user"` is set by `NookProvider`.

---

## 5. Mascots

Defined in `persona.json → mascot`. A grid of characters + a palette; the kit draws the face.

```json
"mascot": {
  "name": "Mo", "aura": "#8ad8a8",
  "eye": [6, 6],          // LEFT eye anchor (x, y). The right eye is mirrored.
  "mouth": [8, 12],       // left pixel of the 2px mouth centre. x must be width/2 - 1.
  "palette": { "o": "#23160d", "b": "#8a5a3c", "e": "#23160d", ... },   // "e" = eyes, "m" = mouth (defaults to e), "t" = tongue
  "rows": ["......oooooo......", ...]                                 // "." = empty
}
```

Grid rules: **even width** (16 or 18), 14–16 rows, 1px dark outline (`o`), one highlight colour on the
top-left, one shade colour bottom-right, a cheek colour. Leave 3×4 clear pixels around each eye and
3×2 around the mouth so every expression fits. Validate with `nook-persona check`, look at every mood
with `nook-persona sheet persona.json > moods.html`.

Moods (shared by all mascots, so the whole Nook "speaks" one body language):

| mood | when |
|---|---|
| `idle` | default; blinks on its own |
| `happy` | success, hover on its home card |
| `love` | poked, something saved |
| `working` | a job is running (mouth chews) |
| `thinking` | starting, waiting, unsure |
| `surprised` | dragging something in, bad input |
| `sad` | empty / failed but recoverable |
| `error` | real failure (X eyes, shake) |
| `sleep` | offline, night |

## 6. Voice

`persona.json → voice` holds every line the mascot says. Lists are picked at random (no robotic
repetition). Placeholders: `say(persona, 'hello', { name })` fills `{name}`.

- Every mascot has **one clear personality** in 3 words. Pip: *warm, poetic, calm*. Chomp: *hungry,
  loud, playful*. Mo: *polite, precise, dry humour*.
- Lines are short (≤ 60 chars), present tense, about what's happening *now*.
- The mascot speaks; the UI doesn't. Buttons and labels stay plain ("Download", "Save", "Delete").
- Errors: the mascot sets the mood ("Bleh. That tasted wrong."); the exact technical message goes in the sub-line.
- Required keys: `poke`. Usual keys: `hello`, `working`/state names, `done`, `error`, `empty`, `offline`.
