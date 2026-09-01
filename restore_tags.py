#!/usr/bin/env python3
"""Pull already-computed LLM tags back from Supabase into corpus.db for any
local rows not yet tagged. Exists because the 8/31–9/1 runs lost their corpus
(git 100MB rejection) AFTER syncing tags to Supabase — so Supabase holds tags
for comments the rebuilt corpus will re-ingest. Restoring them saves the
tagging budget for genuinely new comments. Idempotent; cheap; safe to keep in
the pipeline forever. Env: SUPABASE_URL + SUPABASE_SERVICE_KEY (or _ANON_KEY)."""
import sqlite3, json, os, sys, urllib.request

URL = (os.environ.get("SUPABASE_URL") or "https://xmmvllscvuufwskhcdlj.supabase.co").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
BASE = os.path.dirname(os.path.abspath(__file__))
COLS = ("id,specialty,wh_relevant,wh_tier,wh_stakes_note,stance,stance_target,"
        "framings,provisions,rfi,wh_topics,quote,summary,confidence,attachment_read")


def fetch_page(offset, limit=1000):
    req = urllib.request.Request(
        f"{URL}/rest/v1/comments?select={COLS}&stance=not.is.null&order=id&offset={offset}&limit={limit}",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def main():
    if not KEY:
        print("restore_tags: no Supabase key in env — skipping"); return
    db = sqlite3.connect(os.path.join(BASE, "corpus.db"))
    untagged = {r[0] for r in db.execute(
        "SELECT id FROM comments WHERE llm_stance IS NULL")}
    if not untagged:
        print("restore_tags: nothing untagged locally"); return
    restored, offset = 0, 0
    while True:
        page = fetch_page(offset)
        if not page:
            break
        for r in page:
            if r["id"] not in untagged:
                continue
            db.execute("""UPDATE comments SET llm_specialty=?, llm_wh_relevant=?, llm_tier=?,
                llm_stakes_note=?, llm_stance=?, llm_stance_target=?, llm_framings=?,
                llm_provisions=?, llm_rfi=?, llm_topics=?, llm_quote=?, llm_summary=?,
                llm_confidence=?, llm_enriched=1 WHERE id=?""",
                (r["specialty"], 1 if r["wh_relevant"] else 0, r["wh_tier"],
                 r["wh_stakes_note"], r["stance"], r["stance_target"],
                 json.dumps(r["framings"] or []), json.dumps(r["provisions"] or []),
                 json.dumps(r["rfi"] or []), json.dumps(r["wh_topics"] or []),
                 r["quote"], r["summary"], r["confidence"], r["id"]))
            # llm_enriched tracks whether attachment text was part of tagging
            db.execute("UPDATE comments SET llm_enriched=? WHERE id=?",
                       (1 if r["attachment_read"] else 0, r["id"]))
            restored += 1
        offset += len(page)
        if len(page) < 1000:
            break
    db.commit()
    print(f"restore_tags: restored tags for {restored} of {len(untagged)} untagged local rows")


if __name__ == "__main__":
    main()
