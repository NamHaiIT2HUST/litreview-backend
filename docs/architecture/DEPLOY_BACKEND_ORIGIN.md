# Where the backend address lives

Short answer: **`vercel.json`, in two `rewrites` entries.** Nowhere else.

## Why this file exists

The backend address used to be written in two places that disagreed with each
other, and both were invisible to whoever was affected:

- `frontend/src/utils/apiConfig.js` carried a hardcoded fallback address.
- `vercel.json` carried a proxy rewrite — on some branches, and not on others.

Because `VITE_API_BASE` was documented nowhere, nobody set it, so the hardcoded
fallback decided which backend each developer was talking to. The value differed
per branch: `main` pointed at an AWS EC2 instance, while `develop` and
`feature/ngaedit-integration` still pointed at a Railway deployment `main` had
abandoned. Two people on two branches were reading and writing two different
databases with nothing on screen to say so.

The fallback in `apiConfig.js` is now gone. The only remaining literal is the
`rewrites` destination in `vercel.json`.

## How a request finds the backend

```
Browser
  │
  ├─ VITE_API_BASE set?      → use it verbatim
  │
  ├─ running on localhost?   → http://<hostname>:8000/api/v1
  │
  └─ otherwise               → /api/v1  (same origin)
                                 │
                                 └─ Vercel rewrite → backend origin
```

Local development needs no configuration: the second branch covers it. Deployed
environments rely on the rewrite, so the browser never learns the backend's
address and no CORS or mixed-content problem arises.

## Changing the backend address

Edit the two `destination` values in `vercel.json` and redeploy. That is the
whole procedure.

## Two known problems with the current value

**1. The EC2 instance uses a dynamic IP.** It has already changed once —
`18.143.200.110` on 25 Aug 13:11, `13.212.121.28` on 25 Aug 22:03, the same day.
It will change again on any stop/start, and each change requires a commit and a
redeploy. Fix by attaching an Elastic IP, or better, pointing a DNS name at the
instance and using that name here.

**2. The Vercel-to-EC2 leg is plaintext.** The destination is `http://`. The
browser sees HTTPS because Vercel terminates TLS at the edge, but traffic from
Vercel to the instance crosses the public internet unencrypted. Fix by putting
TLS in front of the backend (a load balancer, or Caddy/nginx with Let's Encrypt)
and switching the destination to `https://`.

Note that `vercel.json` rewrites cannot read environment variables — the
destination must be a literal string. Parameterising it requires either a stable
DNS name (recommended) or a serverless proxy function.

## Deploying somewhere other than Vercel

Set `VITE_API_BASE` at build time to the backend's public URL. It must be
`https://` if the frontend is served over HTTPS; browsers block mixed active
content. The backend must then also allow that origin in `CORS_ORIGINS`.
