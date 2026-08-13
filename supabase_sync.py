#!/usr/bin/env python3
"""Upsert the tagged corpus into Supabase Postgres. Uses the SERVICE key (bypasses
row-level security). Env: SUPABASE_URL, SUPABASE_SERVICE_KEY."""
import sqlite3, json, os, urllib.request, urllib.error
from export_data import submitter_type

URL = os.environ["SUPABASE_URL"].rstrip("/"); KEY = os.environ["SUPABASE_SERVICE_KEY"]
REG = "https://www.regulations.gov/comment/{}"
def jl(s):
    try: v = json.loads(s) if s else []
    except: v = []
    return v if isinstance(v, list) else []

def post(table, rows):
    body = json.dumps(rows).encode()
    req = urllib.request.Request(f"{URL}/rest/v1/{table}?on_conflict=id", data=body, method="POST",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"})
    urllib.request.urlopen(req, timeout=120)

def main():
    db = sqlite3.connect("corpus.db"); db.row_factory = sqlite3.Row
    att = {}
    for a in db.execute("select * from attachments"): att.setdefault(a["comment_id"], []).append(a)
    crows = []
    for r in db.execute("select * from comments"):
        crows.append({"id": r["id"], "title": (r["title"] or None), "organization": (r["organization"] or None),
            "category": r["category"], "submitter_type": submitter_type(r["category"]),
            "posted_date": ((r["posted_date"] or "")[:10] or None), "comment_excerpt": (r["comment_text"] or "")[:600],
            "regs_url": REG.format(r["id"]), "wh_flag": bool(r["wh_flag"]), "priority": r["priority"],
            "themes": jl(r["themes"]), "specialty": r["llm_specialty"], "wh_relevant": bool(r["llm_wh_relevant"]),
            "wh_tier": r["llm_tier"], "wh_stakes_note": (r["llm_stakes_note"] or None), "stance": r["llm_stance"],
            "stance_target": (r["llm_stance_target"] or None), "framings": jl(r["llm_framings"]),
            "provisions": jl(r["llm_provisions"]), "rfi": jl(r["llm_rfi"]), "wh_topics": jl(r["llm_topics"]),
            "quote": (r["llm_quote"] or None), "summary": (r["llm_summary"] or None), "confidence": r["llm_confidence"],
            "attachment_read": bool(r["llm_enriched"]), "has_attachment": r["id"] in att,
            "is_form_letter": (bool(r["is_form_letter"]) if ("is_form_letter" in r.keys() and r["is_form_letter"] is not None) else False),
            "dup_cluster": (r["dup_cluster"] if ("dup_cluster" in r.keys() and r["dup_cluster"] is not None) else None),
            "dup_cluster_size": (r["dup_cluster_size"] if ("dup_cluster_size" in r.keys() and r["dup_cluster_size"] is not None) else 1)})
    for i in range(0, len(crows), 400):
        post("comments", crows[i:i+400]); print(f"  upserted comments {min(i+400,len(crows))}/{len(crows)}")
    arows = [{"id": a["id"], "comment_id": cid, "file_name": a["file_name"], "source_url": a["source_url"],
              "size_bytes": a["size_bytes"], "extracted_chars": len(a["extracted_text"] or "")}
             for cid, lst in att.items() for a in lst]
    for i in range(0, len(arows), 400):
        post("attachments", arows[i:i+400])
    print(f"synced comments={len(crows)} attachments={len(arows)}")

if __name__ == "__main__":
    main()
