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

echo "== 1. fetch new/updated comments (budget: ${ING_MIN}m) =="
python3 mpfs_ingest.py --mode daily ${ING_MIN:+--max-minutes "$ING_MIN"}

echo "== 2. download + extract new attachment PDFs (budget: ${PDF_MIN}m) =="
python3 pdf_ingest.py ${PDF_MIN:+--max-minutes "$PDF_MIN"}

echo "== 3. keyword re-classification =="
python3 reclassify.py

echo "== 4. LLM-tag any newly ingested comments (budget: ${TAG_MIN}m) =="
python3 tag_llm.py ${TAG_MIN:+--max-minutes "$TAG_MIN"}

echo "== 4b. detect template / form-letter campaigns =="
python3 dedupe.py

echo "== 5. regenerate dashboard =="
python3 export_data.py
python3 build_dashboard.py

echo "== 6. mirror into Supabase Postgres =="
python3 supabase_sync.py

echo "== 7. stage the public site =="
mkdir -p public
cp dashboard.html public/index.html
echo "tracker.51and.com" > public/CNAME   # keep the custom domain across deploys
echo "done."
