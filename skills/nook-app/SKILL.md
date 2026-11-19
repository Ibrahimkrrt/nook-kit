---
name: nook-app
description: House rules for building, changing or fixing anything in the user's Nook (formerly "Pixel Hub") at ~/dev/pixel: the hub server, its home screen, any Nook app (Chomp, Burrow, …), the @nook/kit package or the nookkit Python bricks. Use it whenever the user asks for a new personal app, a feature in one of their apps, or a fix in the Nook, before writing code. Covers the many-repos architecture, manifests, back-end bricks, the kit release flow, scaffolding and how to verify work.
---

# Building in the Nook

The Nook is the user's personal app home: a local server (`~/dev/pixel/hub`) that hosts independent
apps, each in its **own git repo** under `~/dev/pixel/<id>`, all built on one shared kit
(`~/dev/pixel/kit`, npm `@nook/kit`, Python `nookkit`). Read
`~/dev/pixel/kit/docs/ARCHITECTURE.md` once per session; it's the source of truth for the contracts.
For anything visual also load the **nook-design** skill.

## Golden rules

1. **New app = new repo**, made with the scaffolder, never by copying another app:
   `~/dev/pixel/kit/bin/nook-new-app <id> "<Name>" "<tagline>" "<Mascot name>"`.
   Then design its persona (mascot + voice + colours) *before* building features.
   Then give it a **private** GitHub repo: `gh repo create Ibrahimkrrt/nook-<id> --private --source . --remote origin --push`.
   GitHub: `nook-kit` and `nook-chomp` are public, everything else private. Commits use the noreply email
   (set per repo); never make a repo public without checking its history for personal data first.
2. **Use the bricks, don't re-invent them.** Accounts → `nookkit.auth.Accounts`. SQLite → `nookkit.store.Database`
   (append migrations, never edit old ones). Uploads → `nookkit.files.decode_upload` + `safe_name` + `unique_path` + `inside`.
   Background work with progress → `nookkit.jobs.Job`. Data folders → `nookkit.paths`.
   Document text → `nookkit.files.extract_text`. Local AI → `nookkit.llm` (the user's own models via LM Studio,
   llama.cpp or Ollama, loopback only; never ask them to download one; always keep a no-AI fallback and
   show which one answered). Always go through `llm.ask_json`: with LM Studio it runs `nookkit.warden`
   (load on demand, GPU only, measured memory checks, one model at a time, unload after). Never send a
   model *name* to LM Studio's chat API yourself: its just-in-time loading would load it with huge defaults
   (40k context, 4 parallel) and eat the PC's RAM; that happened once.
   Accounts with private data → `Accounts(db, id, idle_minutes=15)` + `useIdle`/`IdleBadge`/`IdleWarning`
   (inactivity logout, enforced on the server too) + `"lock_on_leave": true` in the manifest and
   `useStillHere` (going back to the Nook home logs the app out).
   Front end: kit components, `api('/api/<id>')`, `usePoll`, `useFlash`, `useToast`, `useConfirm`,
   `useContextMenu` (right-click menus; the same actions must also be reachable from a visible "More" button),
   `usePageMenu` (the screen's items for the page-wide right-click menu; give each area of a screen its own
   `bind` menu where there's something specific to do there).
3. **Something reusable belongs in the kit**, not copy-pasted into two apps. Add it to the kit, test it,
   release a minor version (see below), then update the apps.
4. **App code never imports another app.** Apps talk to the Nook only through the manifest, `persona.json`
   and `/api/<id>/` routes.
5. **Keep the security model:** POSTs are JSON (CSRF), phone access needs the hub key, accounts use the
   auth brick (scrypt, HttpOnly cookie scoped to `/api/<id>`), files are checked with `inside()` before
   being served or deleted, data lives in `~/.local/share/nook/<id>/` (0700).
6. **The user's data is precious.** Never delete user files or accounts to "clean up" without asking.
   Schema changes are migrations.

## Repo layout of an app

```
<id>/
├── nook.app.json        manifest (id, name, version, engine "^1.0.0", api, web, persona)
├── api/routes.py        ROUTES = {"GET /x": fn}; fn(req) -> req.json(...) | req.error(...) | req.file(...)
├── web/src/persona.json identity: colours, mascot, voice (the Nook reads it for the home card)
├── web/src/…            React 19 + Motion, built with nookVite({ id })
├── CLAUDE.md, README.md
```

## Everyday commands

| Task | Command |
|---|---|
| What's installed / why an app doesn't load | `python3 ~/dev/pixel/hub/server/nook.py --check` |
| Restart after back-end (`api/`, `nookkit`, `nook.py`) changes | `systemctl --user restart nook` |
| Logs | `journalctl --user -u nook -n 50` |
| Front-end live reload | `cd <app>/web && npm run dev` → http://localhost:5173/<id>/ (proxies `/api` to the Nook) |
| Publish front end | `cd <app>/web && npm run build` (no restart needed) |
| Validate a persona | `cd <app>/web && npm run check` |
| Kit Python tests | `cd ~/dev/pixel/kit && npm test` |
| Test a server copy without touching the real one | `NOOK_PORT=8799 NOOK_NO_MDNS=1 python3 ~/dev/pixel/hub/server/nook.py` |

Test copies with real-looking data: also set `HOME=<scratch dir>` (copy `~/.config/nook/config.json` there) so
app databases and files go to the sandbox, never the user's. Stop a test copy **by port**, never by name (a
name pattern also kills the live `nook.service`):
`kill $(ss -ltnp | grep ':8799 ' | grep -o 'pid=[0-9]*' | cut -d= -f2)`.
Don't test timers with Playwright's `clock.fastForward`/`runFor`: they freeze Motion's animations (sheets
never finish closing). Shorten the real delay instead (e.g. set it in the sandbox DB) and wait in real time.
Motion components (`motion.li`, `motion.button`…) claim `onDragStart` for their own gestures: put native
HTML drag-and-drop handlers on a plain element inside them.

## Changing the kit

1. Edit `~/dev/pixel/kit`. Try it in an app *before* releasing: `NOOK_KIT_DEV=1 npm run build` (or `dev`)
   in that app's `web/` uses the kit checkout directly.
2. `npm test` in the kit; `nook-persona check` the personas if the mascot engine changed.
3. Release: bump `version` in `package.json` **and** `py/nookkit/__init__.py` (a test enforces this),
   add to `CHANGELOG.md`, commit, `git tag vX.Y.Z`. Patch = fix, minor = additions, major = breaking.
4. Each app: `cd web && npm update @nook/kit && npm run build`. Nook home too (`hub/web`).

## Verify like you mean it

- Build every front end you touched; restart the Nook if Python changed; `nook.py --check` shows ✔.
- Exercise real flows, not just builds: drive the page with Playwright (`playwright-core` +
  `executablePath: '/usr/bin/google-chrome'`), take screenshots at 1280×900 **and** 390×844, read them,
  collect console errors, check `document.documentElement.scrollWidth <= innerWidth` on phones.
- Remove any test accounts/files you created (and only those).
- Zen (the user's browser) scrambles canvas read-back: never `toDataURL`/`getImageData`; use SVG.

## Hub facts worth knowing

- Port 8765, `hub.local` announced over Avahi D-Bus (not `/etc/avahi/hosts`), phone key cookie `hub_key`
  (SameSite=Lax), config + key in `~/.config/nook/`. Troubleshooting lives in `~/dev/pixel/hub/README.md`:
  add new known issues there.
