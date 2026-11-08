# __NAME__

__TAGLINE__

A room in the [Nook](../hub). Mascot: **__MASCOT__**.

| I want to… | Command |
|---|---|
| Work on the front end with live reload | `cd web && npm run dev` → http://localhost:5173/__ID__/ |
| …while also changing the kit | `cd web && NOOK_KIT_DEV=1 npm run dev` |
| Publish front-end changes | `cd web && npm run build` (refresh the page) |
| Apply back-end changes | `systemctl --user restart nook` |
| Check the persona / mascot | `cd web && npm run check` |
| Update to a newer kit | `cd web && npm update @nook/kit && npm run build` |
