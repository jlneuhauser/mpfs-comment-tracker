#!/usr/bin/env python3
"""
MPFS CY2027 comment ingestion + classification engine.
Pulls public comments on docket CMS-2026-2377 from the Regulations.gov API,
classifies each against 51&'s women's-health watch-list taxonomy, and stores
them in a portable SQLite corpus (with FTS5 full-text search).

Usage:
  REGS_API_KEY=xxxx python3 mpfs_ingest.py --mode backfill        # all comments
  REGS_API_KEY=xxxx python3 mpfs_ingest.py --mode daily           # only new/updated
  REGS_API_KEY=xxxx python3 mpfs_ingest.py --mode backfill --limit 40   # sample
"""
import requests, sqlite3, json, time, re, html, sys, os, argparse
from datetime import datetime, timezone, timedelta

API      = "https://api.regulations.gov/v4"
KEY      = os.environ.get("REGS_API_KEY", "DEMO_KEY")
DOCKET   = "CMS-2026-2377"
BASE     = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE, "corpus.db")
TAX_PATH = os.path.join(BASE, "taxonomy.json")
TAX      = json.load(open(TAX_PATH))

session = requests.Session()

# ---------- rate-limited request ----------
def _secs_to_next_hour():
    now = datetime.now(timezone.utc)
    nxt = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return max(15, int((nxt - now).total_seconds()) + 15)

def api_get(url, params=None, tries=6):
    """GET with hourly-rate-limit + 5xx handling. A 429 waits out the full
    window reset (api.data.gov caps at 1000/hr and does not always send
    Retry-After) and does NOT consume the 5xx error budget."""
    params = dict(params or {}); params["api_key"] = KEY
    err = 0
    while True:
        r = session.get(url, params=params, timeout=60)
        if r.status_code == 429:
            ra = int(r.headers.get("Retry-After", 0) or 0)
            wait = ra if ra > 0 else _secs_to_next_hour()
            print(f"  [{datetime.now(timezone.utc):%H:%M:%SZ}] rate limit reached — "
                  f"sleeping {wait}s for the hourly window to reset", flush=True)
            time.sleep(wait); continue
        if r.status_code >= 500:
            err += 1
            if err >= tries:
                raise RuntimeError(f"5xx after {tries} tries: {url}")
            time.sleep(2 ** err); continue
        r.raise_for_status()
        return r.json()

# ---------- text + classification ----------
_TAGS = re.compile(r"<[^>]+>")
def strip_html(t):
    if not t: return ""
    t = t.replace("<br/>", "\n").replace("<br>", "\n").replace("<br />", "\n")
    return html.unescape(_TAGS.sub(" ", t)).strip()

# Precompile every term to a word-boundary regex (case-insensitive).
def _compile(terms):
    return [(re.compile(r"\b" + re.escape(t) + r"\b", re.I), t) for t in terms]

_PRIORITY = {k: {"label": v["label"], "pats": _compile(v["terms"])}
             for k, v in TAX["priority_watch"].items()}
_THEMES   = {k: {"label": v["label"], "wh": v.get("womens_health", False),
                 "rfi": v.get("is_rfi", False), "prio": v.get("priority", "low"),
                 "req": v.get("requires_wh_topic", False),
                 "pats": _compile(v["terms"])}
             for k, v in TAX["themes"].items()}
# Curated women's-health TOPIC lexicon — the anchor that gates WH relevance.
_WH_TOPIC = _compile(TAX.get("wh_topic_terms", TAX.get("womens_health_signal_terms", [])))

def classify(text, org="", title=""):
    hay = " ".join([title or "", org or "", text or ""])
    themes, hits, priority_hits, rfi_hits = [], {}, [], []
    max_prio = "low"; order = {"low":0,"medium":1,"high":2,"critical":3}
    # Topic anchor: does the comment genuinely mention a women's-health topic?
    wh_terms = sorted({t for p, t in _WH_TOPIC if p.search(hay)})
    has_topic = bool(wh_terms)
    # priority watches (RRM / root-cause)
    for key, cfg in _PRIORITY.items():
        m = [t for p, t in cfg["pats"] if p.search(hay)]
        if m:
            themes.append(key); hits[key] = sorted(set(m)); priority_hits.append(cfg["label"])
            max_prio = "critical"
    # theme clusters
    wh_flag = False
    for key, cfg in _THEMES.items():
        m = [t for p, t in cfg["pats"] if p.search(hay)]
        if not m:
            continue
        # requires_wh_topic themes only apply when a real WH topic anchor is present,
        # so generic payment/RFI language alone never tags a comment as women's health.
        if cfg["req"] and not has_topic:
            continue
        themes.append(key); hits[key] = sorted(set(m))
        if cfg["wh"]: wh_flag = True
        if cfg["rfi"]: rfi_hits.append(cfg["label"])
        if order[cfg["prio"]] > order[max_prio]: max_prio = cfg["prio"]
    # Women's-health flag: a genuine WH theme, OR at least two distinct WH topic
    # terms (a single stray mention — e.g. a PT noting "pelvic floor" once — doesn't count).
    if len(wh_terms) >= 2:
        wh_flag = True
    # crude relevance score: weighted by hits + priority
    score = min(100, 12*len(priority_hits) + 8*sum(1 for k in themes if _THEMES.get(k, {}).get("wh"))
                + 4*len(wh_terms))
    return {
        "themes": sorted(set(themes)), "hits": hits, "wh_flag": wh_flag,
        "wh_relevance": score, "priority": max_prio,
        "priority_hits": priority_hits, "rfi_hits": rfi_hits,
        "wh_signal_terms": wh_terms,
    }

# ---------- DB ----------
def init_db():
    c = sqlite3.connect(DB_PATH); c.executescript("""
    CREATE TABLE IF NOT EXISTS comments (
      id TEXT PRIMARY KEY, docket_id TEXT, comment_on_document_id TEXT, title TEXT,
      posted_date TEXT, received_date TEXT, last_modified_date TEXT,
      submitter_name TEXT, organization TEXT, category TEXT, state_province TEXT,
      government_agency TEXT, comment_text TEXT, has_attachments INTEGER DEFAULT 0,
      attachment_count INTEGER DEFAULT 0, withdrawn INTEGER DEFAULT 0,
      duplicate_comments INTEGER DEFAULT 0,
      themes TEXT, theme_hits TEXT, wh_flag INTEGER DEFAULT 0, wh_relevance INTEGER,
      priority TEXT, priority_hits TEXT, rfi_hits TEXT, summary TEXT,
      raw TEXT, ingested_at TEXT, classified_at TEXT
    );
    CREATE TABLE IF NOT EXISTS attachments (
      id TEXT PRIMARY KEY, comment_id TEXT, file_name TEXT, file_format TEXT,
      source_url TEXT, drive_file_id TEXT, drive_url TEXT, size_bytes INTEGER,
      extracted_text TEXT, ingested_at TEXT
    );
    CREATE TABLE IF NOT EXISTS ingestion_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT, run_at TEXT, mode TEXT,
      new_comments INTEGER DEFAULT 0, updated_comments INTEGER DEFAULT 0,
      new_attachments INTEGER DEFAULT 0, total_seen INTEGER, notes TEXT
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS comments_fts USING fts5(
      id UNINDEXED, title, organization, comment_text
    );
    CREATE INDEX IF NOT EXISTS idx_posted ON comments(posted_date);
    CREATE INDEX IF NOT EXISTS idx_whflag ON comments(wh_flag);
    """); c.commit(); return c

def last_watermark(c):
    row = c.execute("SELECT MAX(last_modified_date) FROM comments").fetchone()
    return row[0] if row and row[0] else None

# ---------- ingest ----------
def list_comment_ids(limit=None, since=None):
    """Page through the docket's comments; return list of (id, lastModified)."""
    ids, page, last_elem = [], 1, None
    params = {"filter[docketId]": DOCKET, "page[size]": 250,
              "sort": "lastModifiedDate,documentId"}
    if since: params["filter[lastModifiedDate][ge]"] = since
    while True:
        p = dict(params); p["page[number]"] = page
        data = api_get(f"{API}/comments", p)
        batch = data.get("data", [])
        if not batch: break
        for d in batch:
            ids.append((d["id"], d["attributes"].get("lastModifiedDate")))
            if limit and len(ids) >= limit: return ids[:limit]
        meta = data.get("meta", {})
        if page >= min(20, meta.get("totalPages", 1)): break   # API caps at 20 pages
        page += 1
        time.sleep(0.6)
    return ids

def fetch_detail(cid):
    data = api_get(f"{API}/comments/{cid}", {"include": "attachments"})
    return data

def upsert_comment(c, detail):
    d = detail["data"]; a = d["attributes"]; cid = d["id"]
    text = strip_html(a.get("comment"))
    org  = a.get("organization") or ""
    name = " ".join(x for x in [a.get("firstName"), a.get("lastName")] if x) or None
    title= a.get("title") or ""
    cls  = classify(text, org, title)
    atts = [x for x in detail.get("included", []) if x["type"] == "attachments"]
    now  = datetime.now(timezone.utc).isoformat()
    exists = c.execute("SELECT id FROM comments WHERE id=?", (cid,)).fetchone()
    c.execute("""INSERT OR REPLACE INTO comments (id,docket_id,comment_on_document_id,title,
        posted_date,received_date,last_modified_date,submitter_name,organization,category,
        state_province,government_agency,comment_text,has_attachments,attachment_count,
        withdrawn,duplicate_comments,themes,theme_hits,wh_flag,wh_relevance,priority,
        priority_hits,rfi_hits,raw,ingested_at,classified_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        cid, DOCKET, a.get("commentOnDocumentId"), title, a.get("postedDate"),
        a.get("receiveDate"), a.get("lastModifiedDate"), name, org, a.get("category"),
        a.get("stateProvinceRegion"), a.get("govAgency"), text,
        1 if atts else 0, len(atts), 1 if a.get("withdrawn") else 0,
        a.get("duplicateComments") or 0, json.dumps(cls["themes"]), json.dumps(cls["hits"]),
        1 if cls["wh_flag"] else 0, cls["wh_relevance"], cls["priority"],
        json.dumps(cls["priority_hits"]), json.dumps(cls["rfi_hits"]),
        json.dumps(d), now, now))
    c.execute("DELETE FROM comments_fts WHERE id=?", (cid,))
    c.execute("INSERT INTO comments_fts (id,title,organization,comment_text) VALUES (?,?,?,?)",
              (cid, title, org, text))
    for at in atts:
        aa = at["attributes"]; fmts = aa.get("fileFormats") or []
        url = fmts[0].get("fileUrl") if fmts else None
        c.execute("""INSERT OR REPLACE INTO attachments
            (id,comment_id,file_name,file_format,source_url,size_bytes,ingested_at)
            VALUES (?,?,?,?,?,?,?)""", (
            at["id"], cid, aa.get("title"),
            fmts[0].get("format") if fmts else None, url,
            fmts[0].get("size") if fmts else None, now))
    return "updated" if exists else "new"

def run(mode="daily", limit=None, sleep=1.2):
    c = init_db()
    since = last_watermark(c) if mode == "daily" else None
    print(f"Mode={mode}  since={since}  key={'REAL' if KEY!='DEMO_KEY' else 'DEMO'}", flush=True)
    ids = list_comment_ids(limit=limit, since=since)
    # Skip comments already stored with an unchanged lastModifiedDate — in BOTH modes.
    # Never re-spend the API request budget on comments we already have unchanged; only
    # genuinely new (or changed) comments get a detail fetch. This keeps daily runs tiny.
    existing = {r[0]: r[1] for r in c.execute("SELECT id, last_modified_date FROM comments").fetchall()}
    before = len(ids)
    ids = [(cid, lm) for (cid, lm) in ids if existing.get(cid) != lm]
    print(f"{before} listed; {before - len(ids)} unchanged (skipped); {len(ids)} to fetch", flush=True)
    new = upd = natt = 0
    for i, (cid, _) in enumerate(ids, 1):
        try:
            detail = fetch_detail(cid)
            status = upsert_comment(c, detail)
            natt += len([x for x in detail.get("included", []) if x["type"]=="attachments"])
            new += status == "new"; upd += status == "updated"
            if i % 10 == 0 or i == len(ids):
                c.commit(); print(f"  {i}/{len(ids)}  (+{new} new, ~{upd} updated)", flush=True)
            time.sleep(sleep)
        except Exception as e:
            print(f"  ERROR {cid}: {e}", flush=True)
    c.execute("""INSERT INTO ingestion_runs (run_at,mode,new_comments,updated_comments,
        new_attachments,total_seen,notes) VALUES (?,?,?,?,?,?,?)""",
        (datetime.now(timezone.utc).isoformat(), mode, new, upd, natt, len(ids), None))
    c.commit(); c.close()
    print(f"Done. new={new} updated={upd} attachments={natt}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="daily", choices=["daily", "backfill"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=1.2)
    a = ap.parse_args()
    run(a.mode, a.limit, a.sleep)
