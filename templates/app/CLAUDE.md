# __NAME__

A Nook app: its own repo, built on `@nook/kit` and hosted by the Nook (`~/dev/pixel/hub`).

**Before changing anything, load the shared skills:** `nook-app` (architecture, bricks, workflow)
and `nook-design` (design system, motion, mascots, voice). They are the house rules for every Nook repo.

- Identity: `web/src/persona.json` (colours, mascot __MASCOT__, voice). Validate with `npm run check` in `web/`.
- Back end: `api/routes.py` → served at `/api/__ID__/...`. Use `nookkit` bricks, don't re-invent them.
- Front end: `web/src` → served at `/__ID__/`. Use kit components and tokens; app CSS is layout only.
- Ship: `cd web && npm run build`, then `systemctl --user restart nook` if `api/` changed.
