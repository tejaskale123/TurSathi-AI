# TurSathi AI — VPS Deployment Decisions

Decisions finalized for hosting the backend on a VPS. Written so another agent/session can pick up deployment work without re-deriving context.

## Topology

- **Backend**: FastAPI app in `backend/app`, containerized via root `Dockerfile`, orchestrated with `docker-compose.yml`.
- **Database**: PostgreSQL in its own container, bound to `127.0.0.1` only (`127.0.0.1:${POSTGRES_PORT:-5432}:5432` in `docker-compose.yml`) — never exposed to the public internet.
- **Exposed port**: **raw port `7066`**, mapped host `7066` → container `8000`, via `PORT=7066` in the VPS `.env` (compose reads `"${PORT:-8000}:8000"`).
- **No reverse proxy / no TLS termination in front of the backend.** The client talks directly to `http://<vps-ip>:7066`. This was a deliberate choice, not an oversight — see Transport below.
- **Repo visibility**: public. Deploys by `git clone` + `update.sh` on the VPS (fetch + hard reset + rebuild + healthcheck — see `update.sh`).

## Public VPS IP

`88.222.212.15` — already wired into `mobile/.env.example` as `EXPO_PUBLIC_API_URL=http://88.222.212.15:7066`.

## Transport: plain HTTP, not HTTPS

Chosen explicitly over HTTPS-on-7066 to avoid needing a domain + cert bound to a non-standard port on day one.

Consequences accepted:
- Traffic (including JWT and X-API-Key headers) is unencrypted on the wire.
- Android blocks cleartext HTTP by default (API 28+) — already handled: `mobile/app.json` sets `android.usesCleartextTraffic: true`.
- If this is revisited later, the upgrade path is TLS termination in front of 7066 (nginx/caddy) or a Let's Encrypt cert bound directly to that port — not yet implemented.

## Auth layering on the exposed port

Two independent gates stack on every `/api/v1/*` route (see `backend/app/api/v1/__init__.py`):
1. **`X-API-Key` header** — checked by `verify_api_key` (`backend/app/core/security.py`), constant-time compare against `API_KEY` env var. Applied at the `api_router` level, so it covers auth/scans/predictions/recommendations/test_voice uniformly.
   - If `API_KEY` is unset/blank, this check is a no-op (open) — intended for local dev, **must be set** in VPS `.env`.
2. **JWT bearer** (`get_current_user`) — per-route, protects user-scoped data.

`/` and `/health` live in `main.py`, outside `api_router`, so they stay open (required for the Docker healthcheck and `update.sh`'s probe).

Mobile client must send both `X-API-Key` (from `EXPO_PUBLIC_API_KEY`, must equal backend `API_KEY`) and, where applicable, `Authorization: Bearer <jwt>`.

## CORS

`FRONTEND_CORS_ORIGINS` in `.env` governs browser clients only (the `frontend/` web app, if deployed). The native Android app is **not** subject to CORS — no change needed there for mobile-only traffic.

## Firewall

Port 7066 must be opened on the VPS OS firewall / cloud security group — the Docker port mapping alone does not do this.

## Env files / secrets hygiene (confirmed)

Only template files are tracked in git: `.env.docker.example`, `backend/.env.example`, `frontend/.env.example`, `mobile/.env.example`. Real `.env` files are excluded by `.gitignore` (`.env`, `.env.*`, with explicit exceptions for the `*.env.example` / `.env.docker.example` templates). No secrets are pushed to the public repo via this mechanism.

Before going live, fill in on the VPS:
- Root `.env` (from `.env.docker.example`): `PORT=7066`, `SECRET_KEY`, `POSTGRES_PASSWORD`, `API_KEY`, `ANTHROPIC_API_KEY`, `SARVAM_API_KEY`.
- `mobile/.env` (from `mobile/.env.example`, baked in at Expo build time, not runtime): `EXPO_PUBLIC_API_URL=http://88.222.212.15:7066`, `EXPO_PUBLIC_API_KEY` matching the backend's `API_KEY`.

## Known gaps / not yet done

- `mobile/assets/images/*` (icon, adaptive icon layers, splash, favicon) referenced by `mobile/app.json` don't exist in the repo yet — app build will fail until someone supplies these design assets. (`.gitignore` was already fixed to stop blocking them once added.)
- No rate limiting on the exposed port — predictions/scans are ML inference endpoints, vulnerable to volumetric abuse even with a valid API key.
- `git reset --hard origin/<branch>` in `update.sh` blindly trusts whatever is on `origin` — fine for a single-maintainer public repo, but no branch protection / commit pinning is in place.
