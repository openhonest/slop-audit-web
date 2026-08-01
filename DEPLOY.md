# Deploying Slop Audit web

Cloudflare in front, Render origin behind, the pattern the workspace standardizes on. The origin does the real work (clone + static analysis); Cloudflare handles TLS, edge caching of identical audits, and a rate-limit backstop.

## What makes it safe to point at arbitrary public repos

The origin is hardened before Cloudflare ever enters the picture. Every layer:

- **The repo's code is never executed.** The analyzer runs with `exec_tests=False`, so only static source and config indicators run. No test suite, no build, no hooks. This is the whole reason it is safe to audit a stranger's repo.
- **Size cap before cloning.** `check_repo_size` asks the GitHub API for the repo size and rejects anything over `MAX_REPO_SIZE_KB` (default ~300 MB). If the API can't be reached, the check is skipped and the clone timeout is the backstop, so a legitimate audit is never blocked by an API hiccup.
- **Clone timeout.** `git clone --depth 1 --single-branch --no-tags` with a hard `CLONE_TIMEOUT_SECONDS`. A repo too big or slow to clone in time is abandoned.
- **Per-IP rate-limit backstop** on `/audit`, in-process, in case someone hits the `.onrender.com` origin directly and bypasses Cloudflare.
- **Temp dir deleted every request** in a `finally`, whether the audit succeeds or fails.
- **Input validated at the boundary.** `parse_github_url` only accepts `github.com` hosts and safe path segments, so `owner/repo;rm -rf /` and traversal attempts are rejected before any I/O.

Cloudflare then absorbs the repeats: identical audits are served from the edge, so the origin only works on a cache miss.

## 1. Deploy the origin (Render)

`render.yaml` is the blueprint. It runs the app under uvicorn on Render's native Python runtime, which ships `git` (the app shells out to it). Create the service from the blueprint, then in the dashboard set the one secret that isn't committed:

- `GITHUB_TOKEN` — a read-only, no-scope (or `public_repo`) personal access token. Without it the pre-clone size check uses the unauthenticated GitHub API (60 calls/hour/IP); with it, 5000/hour. Optional but recommended for anything past a trickle of traffic.

Everything else (`MAX_REPO_SIZE_KB`, the rate-limit knobs, `WORK_DIR`) has a value in `render.yaml` and can be tuned in the dashboard. After first deploy, confirm git is present (Render shell -> `git --version`) and health is green (`/health` returns `{"status":"ok"}`).

## 2. Put Cloudflare in front (`cloudflare/apply-audit-cdn.sh`)

The tool lives on a subdomain of the existing `slopaudit.org` zone (which already fronts the marketing site), so the script is non-destructive: it adds one proxied CNAME and **merges** its cache and rate-limit rules into the zone's rulesets by description, leaving the marketing site's own rules untouched. All of its rules are scoped to `http.host eq audit.slopaudit.org`.

```bash
export CF_API_TOKEN=...          # Zone:Read, DNS:Edit, Cache Rules:Edit, WAF:Edit
export DOMAIN=slopaudit.org
export SUBDOMAIN=audit           # -> audit.slopaudit.org
export RENDER_ORIGIN=slop-audit-web.onrender.com
./cloudflare/apply-audit-cdn.sh
```

Then add `audit.slopaudit.org` as a custom domain on the Render service so its TLS cert covers the host.

**How caching works here:** the origin sends `Cache-Control: public, max-age=3600` on a successful scorecard and `no-store` on every error. The Cloudflare rule is `respect_origin`, so good results cache at the edge for an hour and errors never cache. Because the audit is a `GET` (`/audit?url=owner/repo`), the edge can key the cache on the URL; a `POST` could not be cached at all, which is why the form uses `hx-get`.

**Rate limit:** the edge rule blocks more than 20 requests/minute/IP to `/audit`. A cache hit doesn't count, so only real origin work is limited. The in-process limiter (default 10/minute/IP) sits behind it for direct-to-origin hits.

## 3. Verify

```bash
# First hit is a MISS, the same URL again should be a HIT:
curl -sI "https://audit.slopaudit.org/audit?url=openhonest/slop-audit" | grep -i cf-cache-status
curl -sI "https://audit.slopaudit.org/audit?url=openhonest/slop-audit" | grep -i cf-cache-status
```

## Cost shape

Render is a fixed-monthly dyno, not per-request billing, so the worst case under abuse is a flat fee plus possible bandwidth overage, never an open-ended bill. Edge caching and the two rate limiters keep the origin from doing repeat or runaway work. The one variable to watch is Cloudflare bandwidth on cache misses; the size cap bounds how big any single miss can be.
