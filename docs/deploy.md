# Deploying Ὁδηγός to Render

Do this once, unhurried, at least a week before departure — not the night
before. Budget ~30 minutes for the first run.

## Before you start

- [ ] Repo pushed to GitHub with the work you want deployed
- [ ] `API_TOKEN` generated (`openssl rand -hex 32`) — the same value the iOS
      app uses as `HodegosAPIToken`
- [ ] `ANTHROPIC_API_KEY`
- [ ] `GOOGLE_PLACES_API_KEY` (optional — journal place resolution degrades
      gracefully without it)
- [ ] `TAVILY_API_KEY` (optional — live search degrades gracefully without it)

`render.yaml` lives at the **repo root**. Render only reads blueprints from
the root; a copy inside `backend/` is invisible to it.

## 1. Pick the branch

Render deploys a Blueprint from **one branch**, defaulting to the repo's
default branch. Two options:

- **Merge to `main` first** (recommended — simplest long-term):
  ```bash
  git checkout main
  git merge claude/travel-concierge-ios-prototype-t6hs4h
  git push origin main
  ```
- **Or deploy the feature branch directly** by selecting it in the Blueprint
  creation screen. Fine for now; remember every later fix must land on that
  same branch or Render won't see it.

## 2. Create the Blueprint

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**
2. Connect the GitHub repo, choose the branch from step 1
3. Render parses `render.yaml` and shows **4 services**: `hodegos-backend`
   (web) plus `hodegos-morning` / `-evening` / `-insights` (cron)
4. It prompts for every `sync: false` variable. Paste them. `BACKEND_HOST` is
   **not** prompted — Render resolves it from the web service automatically
5. **Apply**

First build takes several minutes (Docker image + ChromaDB dependencies).

> If the service name `hodegos-backend` is already taken globally, Render
> appends a suffix. That's fine — the cron jobs resolve the real hostname via
> `fromService`, so nothing breaks. Just note the actual URL from the
> dashboard for step 4.

## 3. Verify the deploy

Grab the URL from the dashboard (e.g. `https://hodegos-backend.onrender.com`).

```bash
BASE=https://hodegos-backend.onrender.com     # your actual URL
TOKEN=<your API_TOKEN>

# 1. Unauthenticated health check
curl -s $BASE/healthz                          # → {"ok":true}

# 2. Auth works
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $TOKEN" $BASE/api/today          # → 200
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/today     # → 401 (no token)

# 3. Build the knowledge index — REQUIRED, nothing works without it
curl -s -X POST -H "Authorization: Bearer $TOKEN" $BASE/api/rebuild-index
# → {"indexed_chunks": N}   with N > 0

# 4. Exercise the real path end to end
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"What should I see in Athens today?","memory_mode":false}' \
  $BASE/api/chat

# 5. Prove the cron jobs will work (same call they make)
curl -s -X POST -H "Authorization: Bearer $TOKEN" $BASE/api/jobs/morning

# 6. Full itinerary — expect 21, not "days remaining"
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/itinerary \
  | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["days"]),"days")'

# 7. Map search — the one call that needs GOOGLE_PLACES_API_KEY.
#    An empty list here means the key is missing, NOT that the code is broken.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/places/search?q=taverna&lat=37.9715&lon=23.7267" | head -c 300

# 8. Saved places survive a restart — this is the disk test.
#    Run the POST, restart the service from the dashboard, then run the GET.
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"place_id":"deploy_check","name":"Disk test"}' $BASE/api/saved
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/saved
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" $BASE/api/saved/deploy_check
```

Step 8 is worth doing properly. It is the only check that proves the persistent
disk is actually mounted at `/data` and that `DATA_DIR` points at it — if the
disk were misconfigured, everything above would still pass and you would lose
every journal entry on the first redeploy.

Check the service's **Logs** tab for the startup config block:

```
Ὁδηγός config — .env NOT FOUND at /srv/.env
  ✓ API_TOKEN
  ✓ ANTHROPIC_API_KEY
  ...
```

`.env NOT FOUND` is **correct and expected** in production — Render injects
real environment variables, and the loader deliberately never overrides them.

## 4. Point the app at it

In Xcode's target Info tab:

- `HodegosBaseURL` → the HTTPS Render URL
- `HodegosAPIToken` → unchanged (same `API_TOKEN`)
- **Delete** `NSAllowsLocalNetworking` and `NSLocalNetworkUsageDescription` —
  those exist only for plaintext HTTP to your Mac and are unnecessary (and
  undesirable) against HTTPS

Then cut a TestFlight build. Dev-provisioned builds expire; TestFlight builds
last 90 days and survive without the Mac.

## 4a. What triggers a redeploy

A service with a persistent disk cannot deploy with zero downtime — the disk
attaches to one instance at a time, so Render stops the old one before
starting the new. Every push is therefore a brief outage, which is why
`render.yaml` sets build filters:

```yaml
buildFilters:
  ignoredPaths: [docs/**, ios/**, README.md]
```

Commits touching only those paths are skipped. Everything else — including
`knowledge/` — still deploys, which is deliberate: the itinerary is baked
into the image, and ignoring it would leave `rebuild-index` re-chunking the
old copy still inside the container.

## 5. Re-indexing after content edits

The `knowledge/` folder is baked into the image, so editing the itinerary
means: commit → push → Render redeploys → then re-run
`POST /api/rebuild-index`. The index is **not** rebuilt automatically.

## Cost control

Standard plan + 5GB disk runs roughly $25–30/month. It is safe to **suspend**
the service between now and the trip and resume before departure — the disk
persists. Do not downgrade to a free/spin-down tier: a cold start costs 30–60
seconds on the first request, which is exactly the wrong failure mode
standing in a monastery courtyard.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Blueprint not detected | `render.yaml` must be at the repo root, on the branch Render is watching |
| 503 `API_TOKEN is not set` | The env var wasn't supplied at Blueprint creation — add it in the service's Environment tab and redeploy |
| 401 from the app | `HodegosAPIToken` ≠ `API_TOKEN`; the server log names the exact cause |
| Empty/irrelevant answers | `/api/rebuild-index` was never run after deploy |
| Cron jobs fail | Check the cron service's own log; confirm `BACKEND_HOST` resolved and `API_TOKEN` is set on **each** cron service |
| Chat times out | A tool-using answer can take 20–30s. Lower `CHAT_MODEL` to `claude-haiku-4-5` or reduce effort — both are env vars, changeable from the dashboard without a redeploy |
| Map search returns `{"places":[]}` | `GOOGLE_PLACES_API_KEY` is unset. Search degrades to empty rather than erroring, so check the startup log's `✓/✗` block before suspecting the code |
| Saved places vanish after a redeploy | The disk isn't mounted where `DATA_DIR` points. Confirm the web service shows a 5GB disk at `/data` |
