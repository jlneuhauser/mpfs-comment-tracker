#!/usr/bin/env python3
"""Second-pass tagging for the women's-health-first tracker (added 2026-09-01).
Backfilled in-session for the first 7,516 comments; this script keeps the four
dimensions current for newly ingested comments:

  1. org extraction   — who filed (letterhead/signature), org type, co-signers
  2. G-code stance    — position on the maternity G-code "snap-back" question
  3. RFI asks         — per-RFI: what the commenter wants CMS to do + theme
  4. watch-hit verify — confirm watchlist scoreboard candidates are REAL filers
                        (export_data.py inserts candidates into watch_hits;
                        nothing shows as "Filed" until verified here)

Idempotent; only rows missing a dimension are processed. Uses the same API
plumbing as tag_llm.py. Env: ANTHROPIC_API_KEY, optional MODEL."""
import sqlite3, json, os, re, sys, time, argparse
from tag_llm import call as llm_call, BASE  # same batched API caller

DB = os.path.join(BASE, "corpus.db")
GPAT = r"G-?codes?|GMAT|snap.?back|maternity (?:code|bundle|global)|global (?:maternity|obstetric)|obstetric package|unbundl"
ORGPAT = re.compile(r"(?i)\b(on behalf of|undersigned|we represent|our member|association|society of|college of|academy of|coalition|alliance|institute|federation|chamber of|medical center|health system|hospital|university|,\s*(inc|llc|corp)\b)")

SYS_GCODE = ("CMS proposed replacing the global maternity bundle with new unbundled CPT 2027 maternity codes, but asked "
    "whether to instead keep the old bundle via ~15 HCPCS G-codes (GMAT1-15, the 'snap-back'). For each comment, classify "
    "gcode_stance: adopt_cpt (supports new CPT codes / opposes G-codes), keep_gcodes (keep the bundle/G-codes), mixed, "
    "other_gcode (their G-code mention is a different topic entirely: telehealth/care-management G-codes etc.), unclear. "
    "Also note: <=120 chars, their reason in their terms ('' if other_gcode/unclear). "
    "Return ONLY a JSON array, one object per comment, same order: {\"id\",\"gcode_stance\",\"note\"}.")
SYS_ORG = ("Identify WHO filed each public comment from letterhead/signature. org_name: canonical filing organization, "
    "null for private individuals (a person mentioning an employer is an individual UNLESS explicitly writing on the org's "
    "behalf; a named practice whose owner writes for it counts). org_type: medical_society|advocacy_nonprofit|company|"
    "health_system_or_practice|government|academic|coalition|union|individual|unknown. co_signers: OTHER orgs explicitly "
    "co-signing this SAME letter (cited orgs do NOT count; usually []). signer_title: signer's role for org letters else ''. "
    "Return ONLY a JSON array, same order: {\"id\",\"org_name\",\"org_type\",\"co_signers\",\"signer_title\"}.")
SYS_RFI = ("The CY2027 PFS rule contains five RFIs: primary_care_redesign (team-based primary care pay), "
    "specialty_attribution_aco (attributing patients to specialists), awv_well_woman (Annual Wellness Visit redesign), "
    "quality_data_infrastructure (quality measurement/MVPs), cpt_coding_valuation (how CPT codes get valued/RUC). "
    "For each comment and EACH key in its rfi list: ask = <=140 chars, imperative, what they want CMS to DO on that topic; "
    "theme = 2-5 word category label; wh_angle = true only if explicitly about women's health. "
    "Return ONLY a JSON array, same order: {\"id\",\"asks\":{\"<key>\":{\"ask\",\"theme\",\"wh_angle\"}}}.")
SYS_CPTQA = ("The CY2027 PFS rule contains a Request for Information (Section II.H) on the CPT coding and valuation SYSTEM, "
    "posing five questions: q1 where has the coding/valuation process created challenges for patient care; q2 does code "
    "creation follow medical necessity (what lacks proper codes); q3 what alternatives/complements to the CPT/RUC standard "
    "(governance, process reform); q4 what more objective, empirical valuation approaches (registry/EHR time data, claims, "
    "operative logs, audits); q5 should procedures be grouped/bundled differently. "
    "engages=false when the comment is really about separate rule provisions: the same-day/modifier-25 cut, adopting the "
    "2027 maternity CPT codes vs G-codes, the conversion factor, or a specific code's proposed value without arguing for "
    "system/process reform. engages=true when it addresses the SYSTEM: RUC/CPT process flaws, valuation governance, "
    "evidence standards, sex- or specialty-based valuation disparities/audits, missing codes for conditions, bundling "
    "policy in general, or explicitly answers this RFI. "
    "Return ONLY a JSON array, same order: {\"id\",\"engages\":true|false,\"qs\":{\"q1..q5\": \"<=130-char statement of the "
    "commenter's answer, only for questions actually addressed\"}} (qs omitted when engages=false).")
CPAT = r"RFI|request for information|RUC\b|valuation|coding system|CPT process|undervalu|misvalu|relative value|RVU|empiric|objective data|sex.?based|sex.?equit|bundl|code creation|new codes? for"

SYS_WATCH = ("You verify whether an organization ITSELF FILED a public comment, from the letter text. This feeds a "
    "public scoreboard, so a false yes is far worse than a false no. verified=true ONLY when the letter is the org's "
    "own official filing: the org's letterhead, or an explicit 'I write on behalf of [the org]' as the FILER, or a "
    "signature block naming an officer of the org. ALL of these are false: the letter cites/quotes/praises the org or "
    "codes it developed ('the AMA, in collaboration with ACOG, designed...'); the writer is a MEMBER or Fellow of the "
    "org writing personally; an old document from the org is attached to someone else's comment; anonymous submissions. "
    "Also return \"evidence\": the EXACT phrase (copied verbatim from the letter) proving the org is the filer — "
    "required when verified=true. Return ONLY a JSON array, same order: {\"id\",\"org\",\"verified\":true|false,\"evidence\":\"...\"}.")


def _zone_text(db, cid, ctext):
    """Letterhead + signature zones where a real filer's name must appear."""
    body = (ctext or "").strip()
    att = db.execute("select substr(extracted_text,1,600) from attachments where comment_id=? "
                     "and length(extracted_text)>50 limit 1", (cid,)).fetchone()
    return (body[:600] + " \n " + body[-600:] + " \n " + ((att[0] if att else "") or "")).lower()


def _org_in_zone(db, cid, ctext, regs_org, name):
    if not name: return False
    n = name.lower()
    hay = _zone_text(db, cid, ctext) + " " + (regs_org or "").lower()
    return n in hay or (len(n) >= 14 and n[:14] in hay)


def eff(db, cid, ctext, limit=9000):
    att = db.execute("select group_concat(extracted_text, char(10)||char(10)) from attachments "
                     "where comment_id=? and length(extracted_text)>50", (cid,)).fetchone()[0]
    t = (ctext or "").strip()
    if att: t += "\n\n=== ATTACHED LETTER ===\n" + att
    return t[:limit]


def windows(text, pats, w=420, maxlen=1600):
    spans, out = [], []
    for m in re.finditer(pats, text, re.I):
        s, e = max(0, m.start()-w), min(len(text), m.end()+w)
        if spans and s <= spans[-1][1]: spans[-1] = (spans[-1][0], e)
        else: spans.append((s, e))
    for s, e in spans:
        out.append(text[s:e])
        if sum(len(x) for x in out) > maxlen: break
    return " […] ".join(out)[:maxlen] or text[:1200]


def run_batches(db, items, sys_prompt, apply, deadline, label, batch=10):
    import tag_llm
    tag_llm.SYS = sys_prompt  # reuse caller with our schema
    done = 0
    for i in range(0, len(items), batch):
        if deadline and time.monotonic() > deadline:
            print(f"  {label}: budget reached, {len(items)-i} left for next run"); break
        out = llm_call(items[i:i+batch])
        by = {o.get("id"): o for o in out if isinstance(o, dict)}
        for it in items[i:i+batch]:
            o = by.get(it["id"])
            if o: apply(db, o); done += 1
        db.commit()
    print(f"  {label}: {done}/{len(items)}")


def main(max_minutes=None):
    deadline = (time.monotonic() + max_minutes*60) if max_minutes else None
    db = sqlite3.connect(DB); db.row_factory = sqlite3.Row
    for col in ("org_name TEXT","org_type TEXT","co_signers TEXT","signer_title TEXT",
                "gcode_stance TEXT","gcode_note TEXT","rfi_asks TEXT"):
        try: db.execute(f"ALTER TABLE comments ADD COLUMN {col}")
        except sqlite3.OperationalError: pass

    # 1. G-code stance for untagged candidates
    g_items = []
    for r in db.execute("SELECT id, comment_text, llm_summary FROM comments WHERE gcode_stance IS NULL"):
        full = eff(db, r["id"], r["comment_text"], 30000)
        if re.search(GPAT, full, re.I):
            g_items.append({"id": r["id"], "summary": r["llm_summary"] or "", "snippet": windows(full, GPAT)})
    run_batches(db, g_items, SYS_GCODE,
        lambda db,o: db.execute("UPDATE comments SET gcode_stance=?, gcode_note=? WHERE id=?",
            (o.get("gcode_stance") or "unclear", o.get("note") or "", o["id"])), deadline, "gcode")

    # 2. org extraction for untyped candidates
    o_items = []
    for r in db.execute("""SELECT id, organization, category, submitter_name, comment_text, has_attachments
                           FROM comments WHERE org_type IS NULL"""):
        t = eff(db, r["id"], r["comment_text"], 30000)
        if r["has_attachments"] or (r["organization"] or "").strip() or ORGPAT.search(t[:1200]) or ORGPAT.search(t[-900:]):
            o_items.append({"id": r["id"], "regs_org_field": r["organization"] or "", "category": r["category"] or "",
                "submitter": r["submitter_name"] or "", "opening": t[:1300], "closing": t[-800:] if len(t) > 2100 else ""})
    by_id = {it["id"]: it for it in o_items}
    def _apply_org(db, o):
        it = by_id.get(o["id"], {})
        name = o.get("org_name")
        # mechanical guard: an extracted org must appear in the letterhead/signature
        # zones (or the regs org field) — otherwise it's a citation, not the filer
        # (this is exactly how ACOG got mis-credited on 2026-09-02)
        row = db.execute("SELECT comment_text, organization FROM comments WHERE id=?", (o["id"],)).fetchone()
        if name and row and not _org_in_zone(db, o["id"], row[0], row[1], name):
            name = None
        db.execute("UPDATE comments SET org_name=?, org_type=?, co_signers=?, signer_title=? WHERE id=?",
            (name, (o.get("org_type") or "unknown") if name else "individual",
             json.dumps(o.get("co_signers") or []) if name else "[]",
             o.get("signer_title") or "" if name else "", o["id"]))
    run_batches(db, o_items, SYS_ORG, _apply_org, deadline, "org")

    # 3. RFI asks for RFI-tagged comments missing them
    r_items = []
    for r in db.execute("""SELECT id, llm_rfi, llm_summary, comment_text FROM comments
                           WHERE llm_rfi IS NOT NULL AND llm_rfi NOT IN ('','[]') AND rfi_asks IS NULL"""):
        try: keys = json.loads(r["llm_rfi"])
        except Exception: keys = []
        if not keys: continue
        r_items.append({"id": r["id"], "rfi": keys, "summary": r["llm_summary"] or "",
                        "text": eff(db, r["id"], r["comment_text"], 2800)})
    run_batches(db, r_items, SYS_RFI,
        lambda db,o: db.execute("UPDATE comments SET rfi_asks=? WHERE id=?",
            (json.dumps(o.get("asks") or {}), o["id"])), deadline, "rfi_asks", batch=8)

    # 3b. strict CPT/RUC RFI engagement + five-question mapping
    try: db.execute("ALTER TABLE comments ADD COLUMN cpt_rfi_qa TEXT")
    except sqlite3.OperationalError: pass
    c_items = []
    for r in db.execute("""SELECT id, comment_text, llm_summary, org_name FROM comments
                           WHERE cpt_rfi_qa IS NULL AND (llm_rfi LIKE '%cpt_coding_valuation%'
                              OR llm_rfi LIKE '%evidence_valuation_methodology%'
                              OR llm_rfi LIKE '%rvu_valuation_methodology%')"""):
        full = eff(db, r["id"], r["comment_text"], 30000)
        c_items.append({"id": r["id"], "org": r["org_name"] or "", "summary": r["llm_summary"] or "",
                        "snippet": windows(full, CPAT, w=380, maxlen=2400)})
    run_batches(db, c_items, SYS_CPTQA,
        lambda db,o: db.execute("UPDATE comments SET cpt_rfi_qa=? WHERE id=?",
            (json.dumps({"engages": bool(o.get("engages")), "qs": o.get("qs") or {}}, ensure_ascii=False), o["id"])),
        deadline, "cpt_rfi_qa", batch=8)

    # 4. verify watchlist scoreboard candidates (export_data.py inserts them)
    try:
        w_items = []
        for r in db.execute("""SELECT w.watch_name, w.comment_id, c.comment_text, c.organization,
                                      c.submitter_name, c.has_attachments FROM watch_hits w
                               JOIN comments c ON c.id=w.comment_id WHERE w.verified IS NULL"""):
            # mechanical pre-filter: a real society filing shows its name in the
            # letterhead/signature zones. Anonymous + no attachment + name only
            # mid-text = citation; reject without asking the LLM.
            if not _org_in_zone(db, r["comment_id"], r["comment_text"], r["organization"], r["watch_name"]):
                db.execute("UPDATE watch_hits SET verified=0 WHERE watch_name=? AND comment_id=?",
                           (r["watch_name"], r["comment_id"]))
                continue
            w_items.append({"id": r["comment_id"], "org": r["watch_name"],
                            "opening": eff(db, r["comment_id"], r["comment_text"], 30000)[:900],
                            "closing": (r["comment_text"] or "")[-500:],
                            "anonymous_submitter": not (r["submitter_name"] or "").strip()
                                                   or "anonymous" in (r["submitter_name"] or "").lower(),
                            "has_attachment": bool(r["has_attachments"])})
        db.commit()
        def _apply_watch(db, o):
            ok = bool(o.get("verified"))
            if ok:
                it = next((x for x in w_items if x["id"] == o["id"]), None)
                # a genuine society filing is never an anonymous, attachment-less
                # inline comment (the 5108 ACOG false positive was exactly that)
                if it and it.get("anonymous_submitter") and not it.get("has_attachment"):
                    ok = False
                # evidence must be a real quote from the letter, or the yes is void
                ev = (o.get("evidence") or "").strip().lower()
                hay = ((it or {}).get("opening", "") + " " + (it or {}).get("closing", "")).lower()
                if len(ev) < 10 or ev[:60] not in hay:
                    ok = False
            db.execute("UPDATE watch_hits SET verified=? WHERE watch_name=? AND comment_id=?",
                       (1 if ok else 0, o.get("org"), o["id"]))
        run_batches(db, w_items, SYS_WATCH, _apply_watch, deadline, "watch_verify", batch=6)
    except sqlite3.OperationalError:
        print("  watch_verify: no watch_hits table yet (export_data.py creates it)")
    db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutes", type=float, default=None)
    main(ap.parse_args().max_minutes)
