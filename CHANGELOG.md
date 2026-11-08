# Changelog

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
