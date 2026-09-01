#!/usr/bin/env bash
# Daily pipeline: pull new comments -> extract attachments -> classify -> tag -> publish.
set -euo pipefail
cd "$(dirname "$0")"

# Per-step time budgets (minutes). Every step lands partial progress and resumes
# next run, so the whole pipeline ALWAYS finishes well under GitHub's 6h job
# limit instead of being cancelled with nothing saved (the 8/27–8/30 failure
# mode). Total ≈ 180+40+90 = 310 min + fixed steps, vs the 340-min step timeout
# in daily.yml. Override via env for local/manual runs (empty = unlimited).
ING_MIN="${INGEST_MAX_MINUTES:-180}"
PDF_MIN="${PDF_MAX_MINUTES:-40}"
TAG_MIN="${TAG_MAX_MINUTES:-90}"
EXTRA_MIN="${EXTRA_MAX_MINUTES:-25}"

# hard_stop = backstop around the in-script budgets: if a step hangs past its
# budget (stuck HTTP call, OCR runaway), SIGTERM it and CONTINUE the pipeline,
# so classify/export/Supabase-sync still land whatever was ingested. sqlite
# commits every ~10 rows, so at most a few in-flight items are lost.
hard_stop() {  # hard_stop <minutes> <cmd...>
  local m="$1"; shift
  if [ -n "$m" ]; then
    timeout -k 60 "${m}m" "$@" || echo "!! step hit ${m}m hard stop (or failed) — continuing so partial progress still syncs"
  else
    "$@"
  fi
}

echo "== 0. restore corpus (lives on the corpus-latest GitHub Release, not in git) =="
python3 corpus_store.py fetch

echo "== 1. fetch new/updated comments (budget: ${ING_MIN}m) =="
hard_stop "${ING_MIN:+$((${ING_MIN%.*}+20))}" python3 mpfs_ingest.py --mode daily ${ING_MIN:+--max-minutes "$ING_MIN"}

echo "== 2. download + extract new attachment PDFs (budget: ${PDF_MIN}m) =="
hard_stop "${PDF_MIN:+$((${PDF_MIN%.*}+10))}" python3 pdf_ingest.py ${PDF_MIN:+--max-minutes "$PDF_MIN"}

echo "== 3. keyword re-classification =="
python3 reclassify.py

echo "== 3b. restore any tags Supabase already has (saves tagging budget) =="
python3 restore_tags.py || echo "!! restore_tags failed — tag_llm will cover the gap"

echo "== 4. LLM-tag any newly ingested comments (budget: ${TAG_MIN}m) =="
hard_stop "${TAG_MIN:+$((${TAG_MIN%.*}+15))}" python3 tag_llm.py ${TAG_MIN:+--max-minutes "$TAG_MIN"}

echo "== 4b. detect template / form-letter campaigns =="
python3 dedupe.py

echo "== 4c. second-pass tags: orgs, G-code stance, RFI asks, watchlist verification (budget: ${EXTRA_MIN}m) =="
# note: verifies watch-hit candidates inserted by the PREVIOUS run's export step,
# so a brand-new watchlist match shows as "Filed" one run (<=12h) after ingest.
hard_stop "${EXTRA_MIN:+$((${EXTRA_MIN%.*}+10))}" python3 tag_extra.py ${EXTRA_MIN:+--max-minutes "$EXTRA_MIN"} || echo "!! tag_extra failed — dims stay stale, next run retries"

echo "== 5. regenerate dashboard =="
python3 export_data.py
python3 build_dashboard.py

echo "== 6. mirror into Supabase Postgres =="
python3 supabase_sync.py

echo "== 6b. upload corpus snapshot to the corpus-latest release =="
python3 corpus_store.py store || echo "!! corpus upload FAILED — this run's ingest/tag work will be redone next run"

echo "== 7. stage the public site =="
mkdir -p public
cp dashboard.html public/index.html
echo "tracker.51and.com" > public/CNAME   # keep the custom domain across deploys
echo "done."
