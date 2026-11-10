# Changelog

## 1.2.0 (2026-11-10)

- Inactivity logout. Server: `Accounts(..., idle_minutes=15)` deletes sessions unused for that long (plus a
  75 s grace), per-user choice of 5/10/15/30/60 min (`POST /session/idle`), heartbeat `POST /session/alive`.
  Browser: `useIdle()` (deadline-based, survives sleep, one clock shared by all tabs, pausable),
  `IdleBadge` (countdown ring for the top bar) and `IdleWarning` (the last-minute "Still there?" dialog).
- `Accounts.public()` is now an instance method (it adds `idle` / `idle_choices` when enabled).

## 1.1.0 (2026-11-09)

- `useContextMenu()`: right-click, long-press (touch) and Shift+F10 menus with keyboard navigation, type-ahead,
  edge flipping and focus return. Provided by `NookProvider`. New token `--z-menu`.
- `nookkit.llm`: optional local language model (Ollama, loopback only) with JSON-schema answers and a cached `status()`.
- `nookkit.files.extract_text()`: text from PDFs (pdftotext) and images (tesseract, if installed).
- The Nook imports each app's `api/` folder as a package (relative imports between route modules).

## 1.0.0 (2026-11-08)

First release. Pixel Hub becomes the Nook.

- Design tokens in three layers (primitives, semantic, persona) with persona-derived surfaces and glows
- Components: NookProvider, AppShell, Scene, Card, Button, IconButton, Field, Input, Select, Segmented,
  Chip, Badge, Stat, Progress, Empty, Alert, Sheet, useConfirm, useToast, Speech, Confetti
- Mascot engine: character grids + palettes, shared faces, 9 moods animated with Motion, blinking, particles
- Motion presets: spring.snappy/smooth/bouncy/lazy, rise, pop, stagger, lift
- Vite preset `nookVite({ id })` with kit-dev mode (`NOOK_KIT_DEV=1`)
- Python bricks `nookkit`: http, paths, store (migrations), auth (accounts + sessions), files (safe uploads), jobs, semver
- Tools: nook-new-app scaffolder, nook-persona (check / sheet / icon), nook-install-skills
- Claude Code skills: nook-app, nook-design
