---
name: nook-design
description: The Nook design system for the user's personal apps in ~/dev/pixel: tokens, @nook/kit components, motion rules (Motion/motion.dev), pixel mascots and their moods, persona colours and mascot voice. Use it whenever designing or restyling a Nook screen, creating or editing an app's mascot/persona, adding animation, or reviewing how a Nook app looks and feels.
---

# Designing in the Nook

The full reference is `~/dev/pixel/kit/docs/DESIGN.md`. Read it before designing. This is the short
version and the review checklist.

**Identity:** cozy night-time desktop. *Pixel souls, modern bodies.* The kit owns the system; each app's
`persona.json` owns its personality (accent colours, mascot, voice).

## Building a screen

- Start from `<AppShell persona={persona}>` inside `<NookProvider persona={persona}>`.
- First card is the **stage**: `<Card tone="accent">` with the `<Mascot>` (with `vt="mascot-<id>"`,
  `onPoke`) and its `<Speech>`. The mascot reflects the app's state through `mood`.
- Then the main action card, then lists/history. One `variant="primary"` button per view.
- Use kit components (Button, IconButton, Field/Input/Select, Segmented, Chip, Badge, Stat, Progress,
  Sheet, useConfirm, useToast, Empty, Alert). Icons from `@nook/kit/icons`. No emoji as UI icons.
- App CSS = layout only, prefixed with the app's 2 letters. Colours/type/radius/shadow come from tokens
  (`--accent`, `--text-2`, `--line`, `--surface`, `--r-lg`, `--s-4`, …). If something needs a new token
  or component, add it to the kit instead.
- Numbers, times, sizes: `nk-mono` (tabular). Names and headings: `nk-display` (pixel). Body: default.
- Phone first: test at 390px wide. Hero rows collapse to one column; speech-bubble tails flip upward.

## Motion

Use `spring`, `rise`, `pop`, `stagger`, `lift` from the kit. Springs for touch, fades for exits,
lists stagger 30–80ms, sheets slide up. Only the mascot, the scene and progress loop. `NookProvider`
already honours reduced motion: don't bypass it with raw CSS keyframes on content.

## Personas & mascots

- Personality in 3 words first, then colours, then the sprite, then the voice.
- Colours: `accent` (signature), `accent2` (complement), `accentInk` (text on accent, high contrast),
  `bg` (near-black, tinted). Make sure the new accent differs clearly from existing apps
  (Nook amber `#ffc56b`, Chomp pink `#ff4f9a`, Burrow mint `#8ad8a8`).
- Sprite: even width 16–18, 14–16 rows, 1px dark outline, highlight top-left, shade bottom-right, cheeks.
  Anchors: `eye` = LEFT eye (mirrored), `mouth` x = width/2 − 1. Keep space around eyes and mouth so all
  9 moods fit (idle, happy, love, working, thinking, surprised, sad, error, sleep).
- Always run `node ~/dev/pixel/kit/bin/nook-persona.mjs check <persona.json>` and render
  `… sheet <persona.json> > moods.html`, screenshot it with headless Chrome and **look at it**.
  Regenerate the icon: `… icon <persona.json> > web/public/icon.svg`.
- Voice: short lines (≤ 60 chars), random lists, placeholders `{name}`. The mascot speaks, the UI stays
  plain. Pick lines once per state (memoise on the state key) so polling doesn't make the bubble flicker.

## Review checklist

- [ ] Mascot reacts to every state (loading, success, empty, error, offline) and can be poked
- [ ] One primary action; everything else secondary/ghost
- [ ] Works at 390px, no horizontal scroll, touch targets ≥ 40px
- [ ] Every icon button has a label; forms use `Field`
- [ ] Empty state has art + a sentence + an action
- [ ] No hard-coded colours or fonts in app CSS
- [ ] Reduced motion still works; nothing essential depends on animation
