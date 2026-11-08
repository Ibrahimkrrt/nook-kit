# @nook/kit

The shared craft behind every Nook app: design system, motion, pixel mascots, build preset,
Python back-end bricks, Claude Code skills and the app scaffolder.

- **Design system:** [docs/DESIGN.md](docs/DESIGN.md) (tokens, components, motion, mascots, voice)
- **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (many repos, contracts, versioning)

```
src/styles/      tokens.css (3 layers) · base.css (scene) · components.css
src/components/  AppShell, Card, Button, Field, Segmented, Sheet, Toast, Speech, Confetti…
src/mascot/      sprite engine (grid → SVG, shared faces) + <Mascot> with 9 moods
src/motion.js    springs + variants        src/persona.js  persona colours + voice (say)
src/api.js       fetch helpers, base64 uploads, safe storage
vite/preset.js   nookVite({ id }): base path, dev proxy, kit-dev mode
py/nookkit/      http · paths · store · auth · files · jobs · semver   (+ py/tests)
skills/          nook-app, nook-design (linked into ~/.claude/skills)
templates/app/   what nook-new-app copies
bin/             nook-new-app · nook-persona (check|sheet|icon) · nook-install-skills
```

| I want to… | Command |
|---|---|
| Start a new app | `bin/nook-new-app <id> "<Name>" "<tagline>" "<Mascot>"` |
| Test the Python bricks | `npm test` |
| Check / preview a mascot | `bin/nook-persona.mjs check persona.json` · `sheet persona.json > moods.html` |
| Link the Claude Code skills | `bin/nook-install-skills` |
| Release | bump `package.json` + `py/nookkit/__init__.py`, CHANGELOG, commit, `git tag vX.Y.Z` |
