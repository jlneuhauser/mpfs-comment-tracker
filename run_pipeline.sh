#!/usr/bin/env bash
# Daily pipeline: pull new comments -> extract attachments -> classify -> tag -> publish.
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1. fetch new/updated comments =="
python3 mpfs_ingest.py --mode daily

echo "== 2. download + extract new attachment PDFs =="
python3 pdf_ingest.py

echo "== 3. keyword re-classification =="
python3 reclassify.py

echo "== 4. LLM-tag any newly ingested comments =="
python3 tag_llm.py

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
