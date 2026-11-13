# Changelog

## 1.5.1 (2026-11-13)

- `llm.status()` also reports `vram_gb` (AMD via sysfs, NVIDIA via nvidia-smi), so apps don't call a model
  "too big" when it fits the graphics card.

## 1.5.0 (2026-11-13)

- `nookkit.llm` uses the models already on the PC: besides Ollama it speaks to OpenAI-style local servers
  (LM Studio on :1234, llama.cpp's llama-server on :8080), finds whichever is running, and picks the smallest
  proper chat model (embedding models skipped) unless one was chosen. API tokens supported.
- `llm.status()` now also returns `server`, `models`, `picked`, `needs_token`, `ram_gb`; `llm.save(model=…,
  token=…)` remembers a choice in `~/.config/nook/llm.json` (0600). The token never appears in `status()`.
- Qwen3 models are asked to skip their thinking step; stray `<think>` blocks are stripped.

## 1.4.0 (2026-11-13)

- Lock on leave. Apps whose manifest has `"lock_on_leave": true` are logged out whenever the Nook home is
  shown (its button, the Back button, the menu, a typed address): `leaveApps(ids)` ends the session on the
  server and tells open tabs of the app (`useIdle`'s `onExpire` gets `'left'`). `useStillHere(check, onGone)`
  re-checks a page the browser restores from its back/forward cache.

## 1.3.0 (2026-11-13)

- The whole page has a Nook menu: a right click anywhere no `menu.bind` claims shows the page menu (the app's
  own items from the new `usePageMenu(() => items)`, then Back / Reload / Copy page link / Back to the Nook),
  and an unbound link shows Open / Open in a new tab / Copy link. The browser's own menu stays for text
  fields, selected text, and Shift+Alt+right click.
- Menu items can be `{ note }` (small footer text, hidden on touch screens).

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
