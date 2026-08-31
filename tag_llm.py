#!/usr/bin/env python3
"""Headless LLM tagging via the Anthropic API for any comments not yet tagged.
Reuses tag_schema.md (same schema the interactive tagging used). Tags on full
text (inline + attachment). Env: ANTHROPIC_API_KEY, optional MODEL."""
import sqlite3, json, os, sys, time, urllib.request, urllib.error, argparse
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
KEY  = os.environ.get("ANTHROPIC_API_KEY")
MODEL = os.environ.get("MODEL") or "claude-haiku-4-5"   # blank/unset -> default; override via MODEL repo var
SCHEMA = open(os.path.join(BASE, "tag_schema.md")).read()
BATCH = 12

SYS = ("You are tagging public comments on the CY2027 Medicare Physician Fee Schedule for 51&, a "
       "women's-health policy organization. Follow this schema EXACTLY and return ONLY a JSON array "
       "(one object per comment, in the same order), with no prose or markdown:\n\n" + SCHEMA)

def call(comments):
    user = "Tag these comments. Return ONLY a JSON array.\n\n" + json.dumps(comments, ensure_ascii=False)
    body = json.dumps({"model": MODEL, "max_tokens": 8000, "system": SYS,
                       "messages": [{"role": "user", "content": user}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read())
            txt = data["content"][0]["text"].strip()
            if txt.startswith("```"):
                txt = txt.split("```")[1]
                if txt.lstrip().startswith("json"): txt = txt.lstrip()[4:]
            i, j = txt.find("["), txt.rfind("]")
            return json.loads(txt[i:j+1])
        except urllib.error.HTTPError as e:
            detail = ""
            try: detail = e.read().decode()[:300]
            except Exception: pass
            if e.code in (429, 500, 502, 503, 529) and attempt < 4:
                time.sleep(min(60, 5 * (attempt + 1))); continue
            print(f"  API HTTPError {e.code} {detail} - skipping this batch", flush=True)
            return []
        except Exception as e:
            # timeouts, dropped connections, malformed responses: all transient.
            # Retry with backoff, then skip this batch (stays untagged for next run)
            # rather than crashing the whole pipeline.
            if attempt < 4:
                print(f"  transient error ({type(e).__name__}: {e}); retry {attempt+1}/5", flush=True)
                time.sleep(min(60, 5 * (attempt + 1))); continue
            print(f"  giving up on this batch after retries ({type(e).__name__}) - will retry next run", flush=True)
            return []
    return []

def eff_text(db, cid, ctext):
    att = db.execute("select group_concat(extracted_text, char(10)||char(10)) a from attachments "
                     "where comment_id=? and length(extracted_text)>50", (cid,)).fetchone()[0]
    t = (ctext or "").strip()
    if att: t += "\n\n=== ATTACHED LETTER ===\n" + att
    return t[:9000]

def main(max_minutes=None):
    if not KEY: sys.exit("ANTHROPIC_API_KEY not set")
    deadline = (time.monotonic() + max_minutes * 60) if max_minutes is not None else None
    db = sqlite3.connect(os.path.join(BASE, "corpus.db")); db.row_factory = sqlite3.Row
    rows = db.execute("select id,organization,category,comment_text from comments where llm_stance is null").fetchall()
    print(f"comments to tag: {len(rows)}")
    now = datetime.now(timezone.utc).isoformat()
    for i in range(0, len(rows), BATCH):
        if deadline and time.monotonic() > deadline:
            print(f"  time budget ({max_minutes} min) reached — stopping; {len(rows)-i} comments "
                  f"stay untagged and are picked up next run", flush=True)
            break
        chunk = rows[i:i+BATCH]
        payload = [{"id": r["id"], "organization": r["organization"] or "", "category": r["category"] or "",
                    "text": eff_text(db, r["id"], r["comment_text"])} for r in chunk]
        tags = call(payload)
        by = {t["id"]: t for t in tags if isinstance(t, dict) and "id" in t}
        for r in chunk:
            t = by.get(r["id"])
            if not t: continue
            has_att = db.execute("select 1 from attachments where comment_id=? and length(extracted_text)>50 limit 1",(r["id"],)).fetchone()
            db.execute("""update comments set llm_specialty=?,llm_wh_relevant=?,llm_tier=?,llm_stakes_note=?,
                llm_stance=?,llm_stance_target=?,llm_framings=?,llm_provisions=?,llm_rfi=?,llm_topics=?,
                llm_quote=?,llm_summary=?,llm_confidence=?,llm_enriched=? where id=?""", (
                t.get("specialty"), 1 if t.get("womens_health_relevant") else 0, t.get("womens_health_tier"),
                t.get("womens_health_stakes_note",""), t.get("stance"), t.get("stance_target",""),
                json.dumps(t.get("framings",[])), json.dumps(t.get("primary_provisions",[])),
                json.dumps(t.get("rfi_addressed",[])), json.dumps(t.get("womens_health_topics",[])),
                t.get("notable_quote",""), t.get("one_line_summary",""), t.get("confidence",""),
                1 if has_att else 0, r["id"]))
        db.commit(); print(f"  tagged {min(i+BATCH,len(rows))}/{len(rows)}")
    db.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutes", type=float, default=None,
                    help="stop after this many minutes; untagged comments carry to the next run")
    main(ap.parse_args().max_minutes)
