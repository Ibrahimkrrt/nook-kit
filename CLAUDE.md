# @nook/kit

The shared design system + bricks for every Nook app. Load the `nook-app` and `nook-design` skills first.

- Apps depend on released tags (`semver:^1.0.0`). Don't break 1.x: additions are minor, fixes are patch.
- Before releasing: `npm test`, try the change in an app with `NOOK_KIT_DEV=1 npm run build`.
- Version lives in two places: `package.json` and `py/nookkit/__init__.py` (a test checks they match).
- `skills/` are linked into `~/.claude/skills`: edits there change how Claude builds every app.
