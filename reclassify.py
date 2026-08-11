#!/usr/bin/env python3
"""Re-run classification over already-stored comments using the current
taxonomy.json — no Regulations.gov API calls. Use after editing the taxonomy
(e.g. adding a new theme) to backfill the new labels onto existing comments."""
import sqlite3, json, os
from datetime import datetime, timezone
from mpfs_ingest import classify, DB_PATH

def main():
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.execute("PRAGMA busy_timeout=30000")
    rows = db.execute("SELECT id,title,organization,comment_text FROM comments").fetchall()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for cid, title, org, text in rows:
        cls = classify(text or "", org or "", title or "")
        db.execute("""UPDATE comments SET themes=?, theme_hits=?, wh_flag=?, wh_relevance=?,
            priority=?, priority_hits=?, rfi_hits=?, classified_at=? WHERE id=?""", (
            json.dumps(cls["themes"]), json.dumps(cls["hits"]),
            1 if cls["wh_flag"] else 0, cls["wh_relevance"], cls["priority"],
            json.dumps(cls["priority_hits"]), json.dumps(cls["rfi_hits"]), now, cid))
        n += 1
        if n % 500 == 0: db.commit()
    db.commit()
    db.close()
    print(f"reclassified {n} comments")

if __name__ == "__main__":
    main()
