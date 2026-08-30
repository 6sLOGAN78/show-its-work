# gemini-proxy

A tiny **OpenAI-compatible** proxy for [Show Its Work](../README.md). It exposes
`POST /v1/chat/completions`, forwards each request to Google Gemini's OpenAI-compat
endpoint, and injects the API key **server-side** — so anyone can run the app against a
real LLM without their own key. The engine still computes every number deterministically;
this only powers the final memo phrasing.

## Run locally
```bash
cd gemini-proxy
npm install
cp .env.example .env          # then put your GEMINI_API_KEY in .env
npm start                     # -> http://localhost:3000
```
Point the Python app at it (this is the default): `SIW_API_BASE=http://localhost:3000/v1`.

Check it: `curl http://localhost:3000/health` → `{"status":"ok","gemini_key_configured":true}`.

## Deploy to Vercel (so end-users need no key)
```bash
cd gemini-proxy
npx vercel            # first run links/creates the project
npx vercel --prod     # deploy
```
Then in the Vercel dashboard → Project → Settings → Environment Variables, add
`GEMINI_API_KEY` (and, recommended, `PROXY_ACCESS_KEY`). Point the app at the deployment:
set `SIW_API_BASE=https://<your-app>.vercel.app/v1` (or edit the default in
`src/show_its_work/config.py`).

> If Vercel returns 401 to the CLI, disable **Vercel Authentication** for the deployment
> (Settings → Deployment Protection) — that's Vercel's gate, not this proxy's.

## Security notes
- **Open by default.** Without `PROXY_ACCESS_KEY`, anyone with the URL can spend your
  Gemini quota (capped by rate limiting). Set `PROXY_ACCESS_KEY` before exposing it
  publicly, and set a spend cap in Google Cloud.
- Rate limited to 20 requests/IP/hour by default (`RATE_LIMIT_MAX`).
- The upstream call times out after 30s (`UPSTREAM_TIMEOUT_MS`).
- `.env` and `api.txt` are gitignored; the key is never logged.
