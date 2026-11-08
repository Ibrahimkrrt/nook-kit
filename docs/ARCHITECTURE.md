# Nook architecture

> Many small repos, one shared craft.

```
~/dev/pixel/                  a folder, not a repo
├── kit/      @nook/kit       design system + front-end bricks + Python bricks + skills + scaffolder
├── hub/      the Nook        runtime host (server/nook.py) + home screen (web/)
├── chomp/    an app          own repo, own version, own release
├── burrow/   an app
└── <next>/   nook-new-app <id> "<Name>"
```

## Why many repos

- An app can be rewritten, broken, or deleted without touching another.
- Each app ships at its own pace and pins the kit version it was built against.
- The Nook knows nothing about any app at build time: apps are *installed* (listed in
  `~/.config/nook/config.json → apps`), discovered from their manifest, and checked before loading.

## What keeps them one product

| Shared thing | Where | How apps get it |
|---|---|---|
| Design tokens, components, motion, mascot engine | `kit/src` | npm dependency, pinned by git tag: `"@nook/kit": "git+file://…/kit#semver:^1.0.0"` |
| Build setup (base path, dev proxy, dedupe) | `kit/vite/preset.js` | `nookVite({ id })` |
| Back-end bricks (`nookkit`) | `kit/py/nookkit` | provided by the Nook at runtime; the manifest's `engine` range is checked |
| House rules for humans and Claude | `kit/docs`, `kit/skills` | skills are linked into `~/.claude/skills` (`kit/bin/nook-install-skills`) |
| Starting point | `kit/templates/app` | `kit/bin/nook-new-app` |

## Contracts

**Manifest** `nook.app.json` (app repo root):

```json
{ "id": "chomp", "name": "Chomp", "version": "2.0.0", "engine": "^1.0.0",
  "api": "api/routes.py", "web": "web/dist", "persona": "web/src/persona.json" }
```

- `id`: lowercase; it becomes the URL (`/chomp/`) and API prefix (`/api/chomp/`). Reserved: nook, api, assets, icons, fonts.
- `engine`: the `nookkit` versions the back end works with. A mismatch → the app is skipped, with the reason on the home screen and in `nook.py --check`.

**Back end:** `api/routes.py` exports `ROUTES = {"GET /x": fn, "POST /y": fn}`; `fn(req)` gets a
`nookkit.http.Request` (`body`, `query`, `headers`, `remote`, `cookie()`, `str()`) and returns
`req.json(...)`, `req.error(msg, code)` or `req.file(path, …)`. POST bodies are JSON only (CSRF defence),
so uploads travel base64 (`fileToBase64` ↔ `nookkit.files.decode_upload`).

**Front end:** a Vite app with `base: '/<id>/'` (from `nookVite`), built to `web/dist`. The Nook serves
it with SPA fallback; `/assets/*` is cached forever (hashed names).

**Persona:** `web/src/persona.json` is read by the app *and* by the Nook (to draw the app's card),
so the home screen shows every app's real mascot without importing app code.

**Data:** private app data in `~/.local/share/nook/<id>/` (`nookkit.paths.data_dir`). Files the user
should browse go in a visible folder (`~/Downloads/Chomp`, `~/Documents/Burrow`).

## Versioning the kit

Semver. `1.x` must not break apps on `^1.0.0`.

1. Change the kit; `npm test` (Python bricks) and `nook-persona check` on the personas.
2. Try it live in an app without releasing: `NOOK_KIT_DEV=1 npm run dev` (or `… npm run build`).
3. Bump `version` in `package.json` **and** `py/nookkit/__init__.py` (a test checks they match),
   add a CHANGELOG entry, commit, `git tag vX.Y.Z`.
4. In each app: `cd web && npm update @nook/kit && npm run build`. Restart the Nook for Python changes.

Breaking change → `2.0.0`; apps keep working on `1.x` until they move their range and `engine`.
