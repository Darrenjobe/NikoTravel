#!/usr/bin/env bash
# Run a backend job by hand — the same call Render's cron makes in production.
#
#   scripts/job.sh morning
#   scripts/job.sh insights                 # respects the 2-interaction threshold
#   scripts/job.sh 'insights?force=true'    # run it anyway (testing)
#   scripts/job.sh 'insights?hours=72'      # widen the lookback
#   scripts/job.sh 'summarize?force=true'   # don't wait 10 min for threads to idle
#
# Override the target with HODEGOS_BASE, e.g. to hit the deployed service:
#   HODEGOS_BASE=https://hodegos-backend.onrender.com scripts/job.sh morning
set -euo pipefail

cd "$(dirname "$0")/.."

JOB="${1:-}"
if [ -z "$JOB" ]; then
  echo "usage: scripts/job.sh <morning|evening|insights|summarize>[?params]" >&2
  echo "       scripts/job.sh reindex     # rebuild the knowledge index" >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo "error: backend/.env not found — copy .env.example and fill it in" >&2
  exit 1
fi

TOKEN=$(grep '^API_TOKEN=' .env | cut -d= -f2-)
if [ -z "$TOKEN" ]; then
  echo "error: API_TOKEN is empty in backend/.env (generate: openssl rand -hex 32)" >&2
  exit 1
fi

BASE="${HODEGOS_BASE:-http://localhost:8000}"

if [ "$JOB" = "reindex" ]; then
  PATH_PART="/api/rebuild-index"
else
  PATH_PART="/api/jobs/$JOB"
fi

echo "→ POST $BASE$PATH_PART"
curl -sS --fail-with-body -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE$PATH_PART" | python3 -m json.tool
