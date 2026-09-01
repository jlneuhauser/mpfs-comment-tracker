#!/usr/bin/env python3
"""One-shot HISTORICAL ingest of last year's PFS docket (CY2026 rule, file code
CMS-1832-P; comments closed Sept 2025) into corpus_2025.db — the baseline for
51&'s year-over-year "State of the Women's Health Voice" analysis.

Design (docket is frozen, so this runs once, resumably):
  phase 1 LIST    windowed metadata listing (beats the API's 5,000-row listing
                  cap by walking -lastModifiedDate windows) -> stub rows
  phase 2 DETAIL  full text + submitter/org/category + attachment metadata for
                  every comment (1 request each; the expensive phase)
  phase 3 PDF     download + extract attachments ONLY for org-letter candidates
                  (societies are a census; individual scans are not needed)
Keyword classification (same taxonomy) runs inline so wh_flag/theme baselines
are directly comparable with the live corpus.

Resume-safe: every phase skips completed work; state is ordinary rows in
corpus_2025.db. Snapshots upload to the corpus-latest GitHub Release as
corpus-2025.db.gz every --snapshot-every minutes (needs CORPUS_GH_TOKEN); on a
fresh machine the script restores from that snapshot before starting.

Usage:
  REGS_API_KEY=... [CORPUS_GH_TOKEN=...] python3 baseline_ingest.py
  add --docket CMS-2025-NNNN to skip auto-discovery; --max-minutes N to budget.
"""
import sqlite3, json, os, re, sys, time, argparse, gzip, shutil, subprocess
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "corpus_2025.db")
FILECODE = "CMS-1832-P"

import mpfs_ingest as M                     # api_get, strip_html, classify
from pdf_ingest import download, extract_text

API = M.API
ASSET = "corpus-2025.db.gz"
REPO = "jlneuhauser/mpfs-comment-tracker"
ORGPAT = re.compile(r"(?i)\b(on behalf of|undersigned|we represent|our member|association|society of|college of|academy of|coalition|alliance|institute|federation|chamber of|medical center|health system|hospital|university|,\s*(inc|llc|corp)\b)")


def fmt_eastern(ts):
    """regs.gov date filters need 'yyyy-MM-dd HH:mm:ss' EASTERN (no overlap here;
    windows dedupe by id)."""
    from zoneinfo import ZoneInfo
    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    c = sqlite3.connect(DB_PATH)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS comments (
      id TEXT PRIMARY KEY, docket_id TEXT, title TEXT,
      posted_date TEXT, last_modified_date TEXT,
      submitter_name TEXT, organization TEXT, category TEXT, state_province TEXT,
      comment_text TEXT, has_attachments INTEGER DEFAULT 0,
      attachment_count INTEGER DEFAULT 0, withdrawn INTEGER DEFAULT 0,
      themes TEXT, theme_hits TEXT, wh_flag INTEGER DEFAULT 0, wh_relevance INTEGER,
      priority TEXT, rfi_hits TEXT,
      detail_fetched INTEGER DEFAULT 0, org_candidate INTEGER DEFAULT 0,
      ingested_at TEXT
    );
    CREATE TABLE IF NOT EXISTS attachments (
      id TEXT PRIMARY KEY, comment_id TEXT, file_name TEXT, file_format TEXT,
      source_url TEXT, size_bytes INTEGER, extracted_text TEXT
    );
    CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS comments_fts USING fts5(
      id UNINDEXED, title, organization, comment_text
    );
    CREATE INDEX IF NOT EXISTS idx25_fetched ON comments(detail_fetched);
    """)
    c.commit(); return c


# ---------- snapshot to / restore from the GitHub release ----------
def _gh(url, tok, method="GET", data=None, ctype="application/json"):
    import urllib.request
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
        **({"Content-Type": ctype} if data else {})})
    with op.open(req, timeout=300) as r:
        b = r.read()
    return json.loads(b) if b else {}

def snapshot(tok):
    if not tok: return
    gz = DB_PATH + ".gz"
    with open(DB_PATH, "rb") as f, gzip.open(gz, "wb", compresslevel=6) as out:
        shutil.copyfileobj(f, out)
    try:
        rel = _gh(f"https://api.github.com/repos/{REPO}/releases/tags/corpus-latest", tok)
        for a in rel.get("assets", []):
            if a["name"] == ASSET:
                _gh(f"https://api.github.com/repos/{REPO}/releases/assets/{a['id']}", tok, "DELETE")
        with open(gz, "rb") as f:
            _gh(f"https://uploads.github.com/repos/{REPO}/releases/{rel['id']}/assets?name={ASSET}",
                tok, "POST", f.read(), "application/gzip")
        print(f"  [snapshot] corpus_2025 uploaded ({os.path.getsize(gz)/1e6:.0f} MB gz)", flush=True)
    except Exception as e:
        print(f"  [snapshot] upload failed ({type(e).__name__}: {e}) — continuing", flush=True)
    finally:
        if os.path.exists(gz): os.remove(gz)

def restore():
    if os.path.exists(DB_PATH): return
    import urllib.request
    url = f"https://github.com/{REPO}/releases/download/corpus-latest/{ASSET}"
    try:
        op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with op.open(url, timeout=600) as r, open(DB_PATH + ".gz", "wb") as f:
            shutil.copyfileobj(r, f)
        with gzip.open(DB_PATH + ".gz", "rb") as f, open(DB_PATH, "wb") as out:
            shutil.copyfileobj(f, out)
        os.remove(DB_PATH + ".gz")
        print("restored corpus_2025.db from release snapshot")
    except Exception:
        print("no snapshot to restore — starting fresh")


# ---------- phase 0: find the docket ----------
def discover_docket(db):
    row = db.execute("SELECT v FROM meta WHERE k='docket'").fetchone()
    if row: return row[0]
    data = M.api_get(f"{API}/documents", {"filter[searchTerm]": FILECODE, "page[size]": 25})
    cands = {}
    for d in data.get("data", []):
        a = d.get("attributes", {})
        if a.get("docketId", "").startswith("CMS") and "physician fee" in (a.get("title") or "").lower():
            cands[a["docketId"]] = a.get("title")
    if not cands:  # fall back to any CMS docket the search returned
        for d in data.get("data", []):
            a = d.get("attributes", {})
            if a.get("docketId", "").startswith("CMS"):
                cands[a["docketId"]] = a.get("title")
    if not cands:
        sys.exit(f"could not discover docket for {FILECODE} — pass --docket explicitly")
    docket = sorted(cands)[0]
    print(f"docket for {FILECODE}: {docket}  ({list(cands.values())[0][:90]})")
    db.execute("INSERT OR REPLACE INTO meta VALUES('docket',?)", (docket,)); db.commit()
    return docket


# ---------- phase 1: windowed listing ----------
def phase_list(db, docket, deadline):
    if db.execute("SELECT v FROM meta WHERE k='list_done'").fetchone():
        print("phase 1 (listing): already complete"); return
    seen = {r[0] for r in db.execute("SELECT id FROM comments")}
    ceiling = db.execute("SELECT v FROM meta WHERE k='list_ceiling'").fetchone()
    ceiling = ceiling[0] if ceiling else None
    total_new = 0
    while True:
        if deadline and time.monotonic() > deadline:
            print("  listing: budget reached — resumes next run"); return
        params = {"filter[docketId]": docket, "page[size]": 250, "sort": "-lastModifiedDate"}
        if ceiling: params["filter[lastModifiedDate][le]"] = fmt_eastern(ceiling)
        window_new, oldest = 0, None
        for page in range(1, 21):
            p = dict(params); p["page[number]"] = page
            data = M.api_get(f"{API}/comments", p)
            batch = data.get("data", [])
            if not batch: break
            for d in batch:
                a = d["attributes"]; oldest = a.get("lastModifiedDate") or oldest
                if d["id"] in seen: continue
                seen.add(d["id"]); window_new += 1
                db.execute("""INSERT OR IGNORE INTO comments(id,docket_id,title,posted_date,
                    last_modified_date,withdrawn,ingested_at) VALUES(?,?,?,?,?,?,?)""",
                    (d["id"], docket, a.get("title"), a.get("postedDate"),
                     a.get("lastModifiedDate"), 1 if a.get("withdrawn") else 0,
                     datetime.now(timezone.utc).isoformat()))
            if page >= min(20, data.get("meta", {}).get("totalPages", 1)): break
            time.sleep(0.4)
        db.commit(); total_new += window_new
        print(f"  listing window ceiling={ceiling}: +{window_new} (total {len(seen)})", flush=True)
        if window_new == 0 or oldest is None or oldest == ceiling:
            db.execute("INSERT OR REPLACE INTO meta VALUES('list_done','1')"); db.commit()
            print(f"phase 1 complete: {len(seen)} comments listed"); return
        ceiling = oldest
        db.execute("INSERT OR REPLACE INTO meta VALUES('list_ceiling',?)", (ceiling,)); db.commit()


# ---------- phase 2: detail fetch ----------
def phase_detail(db, tok, deadline, snap_every):
    todo = [r[0] for r in db.execute(
        "SELECT id FROM comments WHERE detail_fetched=0 AND withdrawn=0 ORDER BY id")]
    print(f"phase 2 (detail): {len(todo)} remaining")
    last_snap = time.monotonic()
    for i, cid in enumerate(todo):
        if deadline and time.monotonic() > deadline:
            print("  detail: budget reached — resumes next run"); return False
        try:
            detail = M.api_get(f"{API}/comments/{cid}", {"include": "attachments"})
        except Exception as e:
            print(f"  {cid}: {type(e).__name__} — skipping this run"); continue
        d = detail["data"]; a = d["attributes"]
        text = M.strip_html(a.get("comment"))
        org = a.get("organization") or ""
        name = " ".join(x for x in [a.get("firstName"), a.get("lastName")] if x) or None
        cls = M.classify(text, org, a.get("title") or "")
        atts = [x for x in detail.get("included", []) if x["type"] == "attachments"]
        n_att = 0
        for att in atts:
            for f in (att["attributes"].get("fileFormats") or []):
                n_att += 1
                db.execute("""INSERT OR IGNORE INTO attachments(id,comment_id,file_name,
                    file_format,source_url,size_bytes) VALUES(?,?,?,?,?,?)""",
                    (f'{att["id"]}:{f.get("format")}', cid,
                     att["attributes"].get("title") or "", (f.get("format") or "").lower(),
                     f.get("fileUrl"), f.get("size")))
        cand = 1 if (n_att and (org.strip() or ORGPAT.search(text[:1200]) or ORGPAT.search(text[-900:])
                     or len(text) < 200)) else 0
        db.execute("""UPDATE comments SET submitter_name=?, organization=?, category=?,
            state_province=?, comment_text=?, has_attachments=?, attachment_count=?,
            themes=?, theme_hits=?, wh_flag=?, wh_relevance=?, priority=?, rfi_hits=?,
            detail_fetched=1, org_candidate=? WHERE id=?""",
            (name, org, a.get("category"), a.get("stateProvinceRegion"), text,
             1 if n_att else 0, n_att, json.dumps(cls["themes"]), json.dumps(cls["hits"]),
             1 if cls["wh_flag"] else 0, cls["wh_relevance"], cls["priority"],
             json.dumps(cls["rfi_hits"]), cand, cid))
        db.execute("INSERT INTO comments_fts(id,title,organization,comment_text) VALUES(?,?,?,?)",
                   (cid, a.get("title") or "", org, text))
        if i % 25 == 24:
            db.commit(); print(f"  ...{i+1}/{len(todo)} details fetched", flush=True)
        if snap_every and time.monotonic() - last_snap > snap_every * 60:
            db.commit(); snapshot(tok); last_snap = time.monotonic()
        time.sleep(0.15)
    db.commit()
    print("phase 2 complete")
    return True


# ---------- phase 3: PDFs for org candidates ----------
def phase_pdfs(db, deadline):
    rows = db.execute("""SELECT a.rowid, a.* FROM attachments a JOIN comments c ON c.id=a.comment_id
        WHERE c.org_candidate=1 AND a.file_format='pdf'
          AND (a.extracted_text IS NULL OR length(a.extracted_text)<50)""").fetchall()
    print(f"phase 3 (org-candidate PDFs): {len(rows)} to extract")
    pdfdir = os.path.join(BASE, "pdfs_2025"); os.makedirs(pdfdir, exist_ok=True)
    done = 0
    for r in rows:
        if deadline and time.monotonic() > deadline:
            print("  pdfs: budget reached — resumes next run"); return
        rowid, aid, cid, _fn, _fmt, url = r[0], r[1], r[2], r[3], r[4], r[5]
        dest = os.path.join(pdfdir, re.sub(r"[^A-Za-z0-9_.-]", "_", f"{cid}_{aid}.pdf"))
        if not (os.path.exists(dest) and os.path.getsize(dest) > 1000):
            code = download(url, dest); time.sleep(0.3)
            if code != "200" or not os.path.exists(dest) or os.path.getsize(dest) < 200:
                continue
        text, _m = extract_text(dest)
        if text:
            db.execute("UPDATE attachments SET extracted_text=? WHERE rowid=?", (text[:60000], rowid))
            done += 1
            if done % 20 == 0: db.commit(); print(f"  ...{done} extracted", flush=True)
    db.commit(); print(f"phase 3 complete ({done} extracted)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docket", default=None)
    ap.add_argument("--max-minutes", type=float, default=None)
    ap.add_argument("--snapshot-every", type=float, default=30)
    args = ap.parse_args()
    if M.KEY == "DEMO_KEY":
        sys.exit("REGS_API_KEY not set (DEMO_KEY rate-limits immediately)")
    tok = os.environ.get("CORPUS_GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    deadline = (time.monotonic() + args.max_minutes * 60) if args.max_minutes else None
    restore()
    db = init_db()
    docket = args.docket or discover_docket(db)
    if args.docket:
        db.execute("INSERT OR REPLACE INTO meta VALUES('docket',?)", (args.docket,)); db.commit()
    phase_list(db, docket, deadline)
    if db.execute("SELECT v FROM meta WHERE k='list_done'").fetchone():
        if phase_detail(db, tok, deadline, args.snapshot_every):
            phase_pdfs(db, deadline)
    snapshot(tok)
    n = db.execute("SELECT count(*), sum(detail_fetched), sum(wh_flag) FROM comments").fetchone()
    print(f"state: {n[0]} listed · {n[1] or 0} detailed · {n[2] or 0} wh_flag")


if __name__ == "__main__":
    main()
