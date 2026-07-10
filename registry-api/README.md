# DreamLayer plugin store — social API

The hosted half of the marketplace (`docs/MARKETPLACE.md`, phase 2): **ratings,
comments, and download counts**. Plugin *code* stays in the git-backed
`registry/` and passes the validation gate — this service only serves the
numbers, so a compromise here can't ship code to anyone.

It's a Cloudflare Worker over a KV namespace. The behaviour is pinned by a
tested Python reference implementation and contract in
`host-python/src/dreamlayer/plugins/social.py` (`SocialStore` + `route`); the
Worker mirrors it exactly.

## Contract

```
GET  /api/plugins                 → {plugins:[{name, ...stats}]}   index + live stats
GET  /api/plugins/<name>          → {name, ...stats, comments:[…]}
POST /api/plugins/<name>/rate     {stars, user} → stats            one vote/user, updatable
POST /api/plugins/<name>/comment  {text, user}  → comment
POST /api/plugins/<name>/download                → {downloads}
```

`stats` = `{downloads, rating, ratings_count, comments_count}`.

## Deploy

```
cd registry-api
npx wrangler kv namespace create SOCIAL      # copy the id into wrangler.toml
npx wrangler deploy
```

It's deployed at **`https://api.dreamlayer.app`** (a Workers custom domain; the
`*.workers.dev` URL keeps working too). The clients already point at it:

- **Website** — `SOCIAL_API` in `landing/plugins.html`.
- **Phone app** — `SOCIAL_API` in `phone-app/src/state/usePluginStore.ts`.

Both clients **degrade gracefully**: with `SOCIAL_API` empty or the Worker
unreachable, they fall back to the static `registry/index.json` (the git-backed
phase 1). So the store works before this is deployed, and gets live numbers +
one-tap rating once it is — zero rework, exactly the phased plan.

## Notes / hardening

- v1 identifies raters by a client-generated `user` id (anonymous, stable per
  device). **Per-IP rate limits now run at the Worker edge** (fixed-window
  over KV: 10 rates/h, 10 comments/h, 60 downloads/h, 5 waitlist joins/h;
  fails open on KV errors — the numbers are decoration, availability wins).
  That is the floor, not the ceiling: the `user` field is still spoofable
  one-vote-per-hour-per-IP, so do NOT surface a "top rated" ranking as an
  editorial signal until votes are account-bound (Cloud P1 accounts + signed
  session tokens; Turnstile is the interim option if rankings must ship
  sooner).
- CORS is open (`*`) so the static site can call it; tighten to your domains in
  production.
