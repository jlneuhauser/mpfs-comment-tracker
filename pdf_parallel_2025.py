#!/usr/bin/env python3
"""Parallel PDF extraction for the 2025 baseline corpus (phase 3 accelerator).
Downloads + extracts org-candidate attachments with a process pool, prioritizing
rows whose regulations.gov organization field is filled (most likely real org
letters). Bounded by --max-minutes; resume-safe; snapshot at end via CORPUS_GH_TOKEN."""
import sqlite3, os, re, sys, time, argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from pdf_ingest import download
import subprocess

def extract_text_fast(pdf):
    # text layer only, hard 60s cap: org letters are digital PDFs; OCR-needing
    # scans stall workers for up to an hour and are essentially never org letters
    try:
        out = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                             capture_output=True, text=True, timeout=60).stdout
        return (out or "").strip()
    except Exception:
        return ""''

DB = os.path.join(BASE, "corpus_2025.db")
PDFDIR = os.path.join(BASE, "pdfs_2025"); os.makedirs(PDFDIR, exist_ok=True)


def work(job):
    rowid, cid, aid, url = job
    dest = os.path.join(PDFDIR, re.sub(r"[^A-Za-z0-9_.-]", "_", f"{cid}_{aid}") + ".pdf")
    try:
        if not (os.path.exists(dest) and os.path.getsize(dest) > 1000):
            code = download(url, dest)
            if code != "200" or not os.path.exists(dest) or os.path.getsize(dest) < 200:
                return rowid, None
        text = extract_text_fast(dest)
        try: os.remove(dest)   # keep disk usage bounded
        except OSError: pass
        return rowid, (text or "")[:60000]
    except Exception:
        return rowid, None


def main(max_minutes, workers):
    deadline = time.monotonic() + max_minutes * 60
    db = sqlite3.connect(DB)
    try: db.execute("ALTER TABLE attachments ADD COLUMN extract_tries INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass
    jobs = db.execute("""
        SELECT a.rowid, a.comment_id, a.id, a.source_url
        FROM attachments a JOIN comments c ON c.id = a.comment_id
        WHERE c.org_candidate=1 AND a.file_format='pdf'
          AND (a.extracted_text IS NULL OR length(a.extracted_text) < 50)
          AND COALESCE(a.extract_tries,0) < 2
        ORDER BY (c.organization IS NOT NULL AND c.organization != '') DESC, a.comment_id
    """).fetchall()
    print(f"pending PDFs: {len(jobs)}")
    done = fail = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        it = iter(jobs)
        futures = {}
        def submit_more(n):
            for _ in range(n):
                j = next(it, None)
                if j is None: return False
                futures[ex.submit(work, j)] = j
            return True
        submit_more(workers * 2)
        while futures:
            for f in as_completed(list(futures), timeout=None):
                futures.pop(f)
                rowid, text = f.result()
                if text and len(text) > 50:
                    db.execute("UPDATE attachments SET extracted_text=? WHERE rowid=?", (text, rowid))
                    done += 1
                    if done % 25 == 0:
                        db.commit(); print(f"  ...{done} extracted", flush=True)
                else:
                    fail += 1
                    db.execute("UPDATE attachments SET extract_tries=COALESCE(extract_tries,0)+1 WHERE rowid=?", (rowid,))
                if time.monotonic() > deadline:
                    db.commit()
                    print(f"budget reached: {done} extracted, {fail} failed this run; "
                          f"{len(jobs)-done-fail} remain")
                    return
                submit_more(1)
                break
    db.commit()
    print(f"phase 3 PDF extraction COMPLETE this run: {done} extracted, {fail} failed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutes", type=float, default=8)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    main(a.max_minutes, a.workers)
