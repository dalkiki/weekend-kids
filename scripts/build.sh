#!/usr/bin/env bash
set -euo pipefail

API_KEY="${SEOUL_OPENAPI_KEY:-}"
LIMIT="${JUMALI_EVENT_LIMIT:-200}"
SITE_URL="${JUMALI_SITE_URL:-https://jumali-did.pages.dev}"
DATA_FILE="data/seoul_cultural_events_mvp.json"

if [[ -n "$API_KEY" ]]; then
  echo "build env: SEOUL_OPENAPI_KEY=present JUMALI_EVENT_LIMIT=${LIMIT} JUMALI_SITE_URL=${SITE_URL}"
  PYTHONPATH=src python -m jumali.collect --api-key "$API_KEY" --limit "$LIMIT" --out-dir data
elif [[ -f "$DATA_FILE" ]]; then
  echo "build env: SEOUL_OPENAPI_KEY=missing; using committed ${DATA_FILE}; JUMALI_SITE_URL=${SITE_URL}"
else
  echo "build env: SEOUL_OPENAPI_KEY=missing; using Seoul sample key; JUMALI_SITE_URL=${SITE_URL}"
  PYTHONPATH=src python -m jumali.collect --api-key sample --limit "$LIMIT" --out-dir data
fi

PYTHONPATH=src python -m jumali.site --events "$DATA_FILE" --out-dir public --site-url "$SITE_URL"
