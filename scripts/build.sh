#!/usr/bin/env bash
set -euo pipefail

API_KEY="${SEOUL_OPENAPI_KEY:-sample}"
LIMIT="${JUMALI_EVENT_LIMIT:-200}"
SITE_URL="${JUMALI_SITE_URL:-https://jumali.pages.dev}"

PYTHONPATH=src python -m jumali.collect --api-key "$API_KEY" --limit "$LIMIT" --out-dir data
PYTHONPATH=src python -m jumali.site --events data/seoul_cultural_events_mvp.json --out-dir public --site-url "$SITE_URL"
