#!/usr/bin/env python3
"""Export corpus.db into an aggregated data.json for the authoritative-monitor
dashboard. Two layers: the whole docket (neutral context) and the 51& women's-health
lens (proprietary cut). Uses both keyword themes and the LLM tags."""
import sqlite3, json, os, re
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, "corpus.db")
TAX  = json.load(open(os.path.join(BASE, "taxonomy.json")))

THEME_META = {}
for k, v in TAX["priority_watch"].items():
    THEME_META[k] = {"label": v["label"], "wh": True, "rfi": False, "priority": v["priority"], "watch": True}
for k, v in TAX["themes"].items():
    THEME_META[k] = {"label": v["label"], "wh": v.get("womens_health", False),
                     "rfi": v.get("is_rfi", False), "priority": v.get("priority", "low"), "watch": False}

PLAIN = {
    "restorative_reproductive_medicine": "Restorative reproductive medicine", "root_cause_medicine": "Root-cause medicine",
    "maternity_labor_delivery": "Maternity & childbirth care", "lactation": "Breastfeeding & lactation support",
    "menopause_midlife": "Menopause & midlife care", "fertility_reproductive": "Fertility care",
    "gyn_surgery": "Gynecologic surgery", "maternity_access": "Access to maternity care",
    "chronic_conditions_women": "Chronic conditions in women", "em_modifier25": "Same-day exam + procedure pay",
    "valuation_misvalued": "How services get priced", "remote_monitoring": "Remote patient monitoring",
    "telehealth": "Telehealth & virtual care", "cpt_rfi": "How medical codes are set",
    "primary_care_redesign_rfi": "Rethinking primary care", "awv_wellwoman_rfi": "The annual well-woman visit",
    "specialty_attribution_rfi": "Who 'owns' a patient's care", "quality_data_rfi": "Measuring care quality",
    "primary_care_rfi_generic": "Overall doctor pay rates", "workforce_access_general": "Who can provide care, and where",
}
# LLM-vocab plain labels
PROV_PLAIN = {"modifier_25":"Same-day exam + procedure pay","conversion_factor_budget_neutrality":"Overall pay rates",
    "rvu_valuation_misvalued":"How services get priced","em_office_visit":"Office-visit (E/M) coding",
    "practice_expense_mei":"Practice-cost inputs","global_surgery":"Global surgery bundles",
    "remote_monitoring":"Remote patient monitoring","site_of_service":"Where care is delivered",
    "quality_mips_mvp":"Quality reporting","drugs_part_b":"Part B drugs","scope_of_practice":"Scope of practice",
    "telehealth":"Telehealth","prior_auth":"Prior authorization","other":"Other"}
FRAME_PLAIN = {"independent_practice_viability":"Independent-practice survival","access_equity_disparities":"Access & equity",
    "workforce_scope_access":"Workforce & who can provide care","fiscal_budget_neutrality":"Overall payment levels",
    "evidence_valuation_methodology":"Pricing accuracy & evidence","consolidation_market_structure":"Consolidation & competition",
    "administrative_burden":"Administrative burden","prevention_wellness":"Prevention & wellness",
    "patient_autonomy_choice":"Patient choice","maternal_health_outcomes":"Maternal health outcomes",
    "integrative_nonpharmacologic":"Integrative / non-drug care","restorative_root_cause":"Restorative & root-cause medicine"}
RFI_PLAIN = {"cpt_coding_valuation":"How medical codes are set & priced","primary_care_redesign":"Rethinking primary care",
    "awv_well_woman":"The annual well-woman visit","specialty_attribution_aco":"Who 'owns' a patient's care (ACOs)",
    "quality_data_infrastructure":"Measuring care quality"}
RFI_TECH = {"cpt_coding_valuation":"CPT / RUC valuation RFI","primary_care_redesign":"Advanced Primary Care (APCM) RFI",
    "awv_well_woman":"AWV / Well-Woman Visit RFI","specialty_attribution_aco":"Specialty Attribution / ACO RFI",
    "quality_data_infrastructure":"Quality Measurement / MVP RFI"}
STANCE_PLAIN = {"oppose":"Oppose","support":"Support","mixed":"Mixed","neutral_informational":"Neutral / informational"}
TOPIC_PLAIN = {"maternity_obstetrics":"Maternity & obstetrics","menopause_midlife":"Menopause & midlife",
    "fertility_reproductive":"Fertility & reproduction","gyn_surgery":"Gynecologic surgery","contraception":"Contraception",
    "breast_health":"Breast health","lactation":"Lactation","cervical_screening":"Cervical screening",
    "pelvic_health":"Pelvic health","general_womens_health":"General women's health"}

KEYWORDS = [("women's health","Women's health"),("menopaus","Menopause"),("maternal","Maternal health"),
    ("fertility","Fertility / infertility"),("pregnan","Pregnancy"),("postpartum","Postpartum"),("prenatal","Prenatal"),
    ("breast","Breast health"),("cervical","Cervical"),("ovarian","Ovarian"),("endometriosis","Endometriosis"),
    ("contracept","Contraception"),("lactation","Lactation / breastfeeding"),("hormone","Hormone therapy"),
    ("gynecolog","Gynecology"),("obstetric","Obstetrics"),("reproductive","Reproductive health")]
def match_keywords(text):
    t=(text or "").lower().replace("’","'")
    return [lab for sub,lab in KEYWORDS if sub in t]

def submitter_type(cat):
    c=(cat or "").lower().strip()
    if not c: return "Unspecified"
    if "individual" in c: return "Individual"
    if any(x in c for x in ["congress","government","federal"]): return "Government / Congressional"
    if "academic" in c: return "Academic"
    if any(x in c for x in ["industry","device","drug","laborator","private industry","health plan","employer","manufactur"]): return "Industry / health plan"
    if "physician" in c: return "Physician / association"
    if any(x in c for x in ["nurse","physician assistant","speech","therapist","social worker","dietitian","nutrition","chiropractor","radiologist","practitioner","midwif","pharmacist","psycholog","other health care professional"]): return "Other health professional"
    if any(x in c for x in ["hospital","provider","clinic","facility","surgical center","long-term care","rural health","home health","critical access","renal","ambulatory"]): return "Provider / facility"
    if any(x in c for x in ["consumer","association","patient","advocacy"]): return "Advocacy / association"
    return "Other"

REG_URL="https://www.regulations.gov/comment/{}"
def jl(s):
    try: return json.loads(s) if s else []
    except: return []
def jd(s):
    try: return json.loads(s) if s else {}
    except: return {}

# --- RFI opportunity-map copy (what CMS asked + why it matters for women's health)
RFI_ASKED = {
    "cpt_coding_valuation": "CMS asked: how should we decide what a medical service is worth — and what evidence should count?",
    "primary_care_redesign": "CMS asked: how should Medicare pay for continuous, team-based primary care instead of visit-by-visit?",
    "awv_well_woman": "CMS asked: should the Annual Wellness Visit be redesigned — and what should a modern one include?",
    "specialty_attribution_aco": "CMS asked: how should patients be attributed to specialists and ACOs — who counts as your doctor?",
    "quality_data_infrastructure": "CMS asked: what should Medicare measure, and how should quality data flow?",
}
RFI_WHY_WH = {
    "cpt_coding_valuation": "This is where gynecologic undervaluation gets fixed: decades of research show female-coded procedures priced ~30% below male-coded equivalents. Evidence standards set here decide whether that record can move CMS.",
    "primary_care_redesign": "Menopause, midlife and preventive women's care are longitudinal, team-based medicine — exactly what visit-by-visit payment fails. Whatever model CMS builds here is the future home of that care.",
    "awv_well_woman": "The opening to build a real well-woman visit into Medicare — screening, menopause, bone and heart health in one covered visit. Almost nobody is answering this question.",
    "specialty_attribution_aco": "For many women, the OB/GYN is the principal doctor. Attribution rules decide whether Medicare's payment models recognize that or route women's care through someone else.",
    "quality_data_infrastructure": "What isn't measured is invisible. No women's-health measures in MVPs means no accountability for menopause care, maternal outcomes, or screening rates.",
}

# --- normalize freeform ask-themes into canonical clusters for the RFI map
import re as _re
_THEME_RULES = [
    (r"modifier.?25|same.?day|e/m cut|em cut|50% (payment )?(cut|reduction)", "Stop the same-day (Mod-25) cut"),
    (r"maternit|g.?code|obstetric cod|ob cod|unbundl", "Adopt the new maternity codes"),
    (r"dose|allerg|immunotherapy|95165|mue", "Fix the allergy-dose definition"),
    (r"ruc\b|ruc process|deference", "Reform how codes get valued (RUC)"),
    (r"empiric|evidence|real.?world|time data", "Require real evidence in valuation"),
    (r"practice expense|\bpe\b|mei\b|indirect", "Update practice-expense inputs"),
    (r"rvu|valuation increase|preserve|arthroplasty|joint|undervalu|work value|revalu", "Protect / raise specific code values"),
    (r"sex.?equity|gender|disparit", "Audit sex-based payment gaps"),
    (r"primary care|team.?based|apcm|longitudinal", "Fund team-based primary care"),
    (r"awv|wellness visit|well.?woman|clinician.?led", "Modernize the wellness visit"),
    (r"speech|slp|pediatric", "Value pediatric speech therapy"),
    (r"caregiver", "Support family caregivers"),
    (r"\bai\b|artificial intelligence|algorithm", "Guardrails for AI in care"),
    (r"attribut|aco\b", "Fix specialist attribution"),
    (r"quality|measure|mvp|reporting", "Measure what matters, cut burden"),
    (r"telehealth|virtual", "Keep telehealth flexible"),
    (r"midwif|workforce|who can bill|billing pathway", "Open billing to the full workforce"),
]
def norm_theme(t):
    tl = (t or "").lower()
    for pat, lab in _THEME_RULES:
        if _re.search(pat, tl): return lab
    return "Other asks"

_ORGISH = _re.compile(r"(?i)\b(assoc|societ|college|academ|center|centre|coalition|alliance|institute|hospital|health|medical|clinic|group|foundation|federation|network|partners|solutions|services|inc\b|llc|corp|pllc|pc\b)\b")
def _dedupe_coalitions(letters):
    """Keep letters whose co-signers are organizations (not individual clinicians
    at the same practice), and collapse near-identical repeat filings."""
    out, seen = [], set()
    for c in sorted(letters, key=lambda c: -len(c["co"])):
        co = [x for x in c["co"] if _ORGISH.search(x or "")]
        if not co: continue
        key = ((c["org"] or "").strip().lower(), tuple(sorted(x.strip().lower() for x in co)))
        if key in seen: continue
        seen.add(key)
        out.append({**c, "co": co})
    return out[:10]

def top(counter, n, plain=None, key_is_plain=False):
    out=[]
    for k,c in counter.most_common(n):
        out.append({"key":k,"label":(plain.get(k,k) if plain else k),"count":c})
    return out

def main():
    db=sqlite3.connect(DB); db.row_factory=sqlite3.Row
    rows=db.execute("SELECT * FROM comments").fetchall()
    total=len(rows)
    theme_counts=Counter(); stype_counts=Counter(); timeline=Counter(); org_counts=Counter(); kw_counts=Counter()
    spec_counts=Counter(); stance_counts=Counter(); tier_counts=Counter(); frame_counts=Counter(); prov_counts=Counter(); topic_counts=Counter()
    rfi_total=Counter(); rfi_wh=Counter()
    wh=watch_rrm=watch_root=0; prio_counts=Counter(); out_rows=[]; stakes_list=[]
    camp_members=defaultdict(list); camp_stance=defaultdict(Counter); camp_wh=Counter(); camp_open=defaultdict(Counter)
    # new: org roster / G-code verdict / RFI ask map / same-day cut
    org_roster=defaultdict(lambda:{"n":0,"wh":0,"type":"unknown","ids":[],"stances":Counter()})
    coalition_letters=[]; gcode_counts=Counter(); gcode_samples=[]
    rfi_theme=defaultdict(Counter); rfi_ask_samples=defaultdict(list); rfi_wh_asks=Counter()
    rfi_form=Counter(); rfi_wh_form=Counter()
    mod25_spec=Counter(); mod25_wh=0; mod25_total=0; mod25_camp=0
    def _open(txt):
        t=re.sub(r"\s+"," ",(txt or "")).strip()
        return (t[:72]+"…") if len(t)>72 else t

    for r in rows:
        themes=jl(r["themes"])
        for t in themes: theme_counts[t]+=1
        if "restorative_reproductive_medicine" in themes: watch_rrm+=1
        if "root_cause_medicine" in themes: watch_root+=1
        if r["wh_flag"]: wh+=1
        prio_counts[r["priority"] or "low"]+=1
        st=submitter_type(r["category"]); stype_counts[st]+=1
        if r["organization"]: org_counts[r["organization"].strip()]+=1
        d=(r["posted_date"] or "")[:10]
        if d: timeline[d]+=1
        kws=match_keywords(r["comment_text"])
        for k in kws: kw_counts[k]+=1
        # LLM fields
        spec=r["llm_specialty"] or "Other/Unclear"; spec_counts[spec]+=1
        stance=r["llm_stance"] or "neutral_informational"; stance_counts[stance]+=1
        tier=r["llm_tier"] or "general"; tier_counts[tier]+=1
        whx=bool(r["llm_wh_relevant"])
        rk=r.keys()
        is_form=bool(r["is_form_letter"]) if "is_form_letter" in rk and r["is_form_letter"] is not None else False
        clu=r["dup_cluster"] if "dup_cluster" in rk and r["dup_cluster"] is not None else -1
        if is_form:
            camp_members[clu].append(r["id"]); camp_stance[clu][stance]+=1
            if whx: camp_wh[clu]+=1
            camp_open[clu][_open(r["comment_text"])]+=1
        for f in jl(r["llm_framings"]): frame_counts[f]+=1
        for p in jl(r["llm_provisions"]): prov_counts[p]+=1
        for tp in jl(r["llm_topics"]):
            if whx: topic_counts[tp]+=1
        for rf in jl(r["llm_rfi"]):
            rfi_total[rf]+=1
            if whx: rfi_wh[rf]+=1
            if is_form:
                rfi_form[rf]+=1
                if whx: rfi_wh_form[rf]+=1
        if tier=="stakes" and (r["llm_stakes_note"] or "").strip():
            stakes_list.append({"id":r["id"],"org":(r["organization"] or "").strip(),"specialty":spec,
                "note":r["llm_stakes_note"].strip(),"quote":(r["llm_quote"] or "").strip(),
                "provisions":[PROV_PLAIN.get(p,p) for p in jl(r["llm_provisions"])][:3],"url":REG_URL.format(r["id"])})
        # --- new-dimension aggregation (columns may be absent on an old corpus)
        oname=(r["org_name"] if "org_name" in rk else None)
        otype=(r["org_type"] if "org_type" in rk else None) or "unknown"
        cosign=jl(r["co_signers"]) if "co_signers" in rk else []
        gst=(r["gcode_stance"] if "gcode_stance" in rk else None)
        rasks=jd(r["rfi_asks"]) if "rfi_asks" in rk else {}
        if oname:
            key=oname.strip()
            o=org_roster[key]; o["n"]+=1; o["type"]=otype; o["ids"].append(r["id"]); o["stances"][stance]+=1
            if whx: o["wh"]+=1
        if cosign:
            coalition_letters.append({"id":r["id"],"org":oname or (r["organization"] or "").strip() or "(unnamed)",
                "co":cosign,"url":REG_URL.format(r["id"]),"wh":whx})
        if gst and gst not in ("other_gcode",):
            gcode_counts[gst]+=1
            note=(r["gcode_note"] or "").strip() if "gcode_note" in rk else ""
            if note and len(gcode_samples)<24:
                gcode_samples.append({"id":r["id"],"stance":gst,"note":note,"org":oname or "",
                    "spec":spec,"url":REG_URL.format(r["id"])})
        for rf,a in rasks.items():
            if rf not in RFI_PLAIN or not isinstance(a,dict): continue
            th=norm_theme(a.get("theme") or a.get("ask") or "")
            rfi_theme[rf][th]+=1
            if a.get("wh_angle"): rfi_wh_asks[rf]+=1
            if a.get("ask") and len(rfi_ask_samples[rf])<40 and a["ask"] not in {s["ask"] for s in rfi_ask_samples[rf]}:
                rfi_ask_samples[rf].append({"ask":a["ask"],"wh":bool(a.get("wh_angle")),"org":oname or "",
                    "id":r["id"],"url":REG_URL.format(r["id"])})
        if "modifier_25" in jl(r["llm_provisions"]):
            mod25_total+=1; mod25_spec[spec]+=1
            if whx: mod25_wh+=1
            if is_form: mod25_camp+=1
        snippet=re.sub(r"\s+"," ",(r["comment_text"] or "")).strip()[:280]
        out_rows.append({"id":r["id"],"title":(r["title"] or "").strip(),"org":(oname or r["organization"] or "").strip(),
            "type":st,"category":r["category"] or "","themes":[THEME_META[t]["label"] for t in themes if t in THEME_META],
            "kw":kws,"wh":bool(r["wh_flag"]),"whx":whx,"tier":tier,"specialty":spec,"stance":stance,
            "stance_target":(r["llm_stance_target"] or "").strip(),"quote":(r["llm_quote"] or "").strip(),
            "summary":(r["llm_summary"] or "").strip(),"has_attach":bool(r["llm_enriched"]),
            "rfi":jl(r["llm_rfi"]),"topics":jl(r["llm_topics"]),"framings":jl(r["llm_framings"]),"provisions":jl(r["llm_provisions"]),
            "priority":r["priority"] or "low","posted":d,"snippet":snippet,"url":REG_URL.format(r["id"],),
            "form":is_form,"cluster":(clu if is_form else -1),"gcode":gst or ""})

    themes_out=[{"key":k,"label":THEME_META[k]["label"],"plain":PLAIN.get(k,THEME_META[k]["label"]),
        "count":theme_counts.get(k,0),"wh":THEME_META[k]["wh"],"rfi":THEME_META[k]["rfi"],
        "priority":THEME_META[k]["priority"],"watch":THEME_META[k]["watch"]} for k in THEME_META]
    themes_out.sort(key=lambda x:x["count"],reverse=True)

    # RFI gap ordered by total
    rfi_gap=[{"key":k,"label":RFI_PLAIN.get(k,k),"tech":RFI_TECH.get(k,""),"total":rfi_total[k],"wh":rfi_wh.get(k,0)}
             for k in sorted(rfi_total,key=lambda x:rfi_total[x],reverse=True)]

    campaigns=[]
    for clu,mem in camp_members.items():
        sig=camp_open[clu].most_common(1)[0][0] if camp_open[clu] else ""
        stance_mode=camp_stance[clu].most_common(1)[0][0] if camp_stance[clu] else "neutral_informational"
        campaigns.append({"id":clu,"size":len(mem),"sample":sig,"stance":stance_mode,
            "wh":camp_wh.get(clu,0),"wh_any":camp_wh.get(clu,0)>0})
    campaigns.sort(key=lambda x:-x["size"])
    camp_submissions=sum(c["size"] for c in campaigns)

    attach_comments=db.execute("select count(distinct comment_id) from attachments where length(extracted_text)>50").fetchone()[0]

    # --- watchlist scoreboard (societies may show absence; companies celebrate-only)
    def _norm(s): return re.sub(r"[^a-z0-9& ]"," ",(s or "").lower()).strip()
    all_filed_names=[]  # (normalized, original, id, via) for org filers and co-signers
    for name,o in org_roster.items():
        all_filed_names.append((_norm(name),name,o["ids"][0],"filed"))
    for cl in coalition_letters:
        for co in cl["co"]:
            all_filed_names.append((_norm(co),co,cl["id"],"cosigner"))
    def _match(entry):
        """All candidate (comment_id, via) hits for one watchlist entry."""
        hits=[]
        for cand in [entry["name"]]+entry.get("aliases",[]):
            cn=_norm(cand); acro=(len(cand)<=8 and cand.isupper()) if cand else False
            for fn,orig,cid,via in all_filed_names:
                if not fn: continue
                ok=False
                if acro: ok=bool(re.search(r"\b"+re.escape(cn)+r"\b",fn))
                else:
                    # containment only when BOTH strings are substantial (junk like 'Health' must not match)
                    ok=(cn==fn) or (len(cn)>=9 and len(fn)>=9 and (cn in fn or fn in cn))
                if ok: hits.append((cid,via,orig))
        return hits
    # Candidates must be VERIFIED before the public scoreboard shows "Filed".
    # tag_extra.py verifies each (watch org, comment) pair by reading the letter
    # opening; verdicts live in watch_hits. Unverified candidates stay "not yet".
    db.execute("""CREATE TABLE IF NOT EXISTS watch_hits(
        watch_name TEXT, comment_id TEXT, via TEXT, verified INTEGER,
        PRIMARY KEY(watch_name, comment_id))""")
    watch_out=[]
    try:
        WL=json.load(open(os.path.join(BASE,"watchlist.json")))
        for g in WL["groups"]:
            for o in g["orgs"]:
                hits=_match(o)
                for cid,via,orig in hits:
                    db.execute("INSERT OR IGNORE INTO watch_hits(watch_name,comment_id,via,verified) VALUES(?,?,?,NULL)",
                               (o["name"],cid,via))
                ver=db.execute("SELECT comment_id,via FROM watch_hits WHERE watch_name=? AND verified=1 ORDER BY comment_id LIMIT 1",
                               (o["name"],)).fetchone()
                cid,via=(ver[0],ver[1]) if ver else (None,None)
                watch_out.append({"name":o["name"],"short":o.get("short",o["name"]),"group":g["key"],
                    "glabel":g["label"],"show_absent":g.get("show_absent",True),
                    "filed":bool(cid),"via":via or "","id":cid or "","url":REG_URL.format(cid) if cid else ""})
        db.commit()
    except FileNotFoundError:
        pass

    # top women's-health organizational voices (extracted orgs with WH-relevant comments)
    wh_voices=sorted(([{"name":n,"n":o["n"],"wh":o["wh"],"type":o["type"],"id":o["ids"][0],
        "url":REG_URL.format(o["ids"][0]),"stance":(o["stances"].most_common(1)[0][0] if o["stances"] else "")}
        for n,o in org_roster.items() if o["wh"]>0]),key=lambda x:(-x["wh"],-x["n"]))[:14]
    filed_companies=[w for w in watch_out if w["group"]=="wh_company" and w["filed"]]

    # RFI opportunity map v2
    rfi_map=[]
    for k in ["primary_care_redesign","specialty_attribution_aco","awv_well_woman","quality_data_infrastructure","cpt_coding_valuation"]:
        samples=rfi_ask_samples.get(k,[])
        samples.sort(key=lambda a:(not a["wh"],not bool(a["org"])))
        rfi_map.append({"key":k,"label":RFI_PLAIN.get(k,k),"tech":RFI_TECH.get(k,""),
            "asked":RFI_ASKED.get(k,""),"why_wh":RFI_WHY_WH.get(k,""),
            "total":rfi_total.get(k,0),"wh":rfi_wh.get(k,0),"wh_asks":rfi_wh_asks.get(k,0),
            "form":rfi_form.get(k,0),"wh_form":rfi_wh_form.get(k,0),
            "themes":[{"t":t,"n":n} for t,n in rfi_theme.get(k,Counter()).most_common(6)],
            "asks":samples[:5]})

    gcode_block={"counts":{s:gcode_counts.get(s,0) for s in ("adopt_cpt","keep_gcodes","mixed","unclear")},
        "samples":gcode_samples[:10]}
    mod25_block={"total":mod25_total,"wh":mod25_wh,"camp":mod25_camp,
        "by_spec":[{"label":s,"count":n} for s,n in mod25_spec.most_common(10)]}

    data={
        "meta":{"total":total,"wh_flagged":wh,"rrm":watch_rrm,"root_cause":watch_root,
            "docket":TAX["docket"],"rule":TAX["rule"],"deadline":TAX["comment_deadline"],
            "priority_counts":dict(prio_counts),
            "wh_relevant":sum(tier_counts[t] for t in ("core","stakes")),
            "tier":{"core":tier_counts.get("core",0),"stakes":tier_counts.get("stakes",0),"general":tier_counts.get("general",0)},
            "n_specialties":len([k for k in spec_counts if k not in("Other/Unclear",)]),
            "attach_comments":attach_comments,
            "campaign_submissions":camp_submissions,"original":total-camp_submissions,"n_campaigns":len(campaigns)},
        "docket":{
            "specialties":top(spec_counts,15),
            "stance":[{"key":k,"label":STANCE_PLAIN.get(k,k),"count":stance_counts.get(k,0)} for k in ["oppose","support","mixed","neutral_informational"]],
            "provisions":top(prov_counts,12,PROV_PLAIN),
            "submitter_types":sorted([{"type":k,"count":v} for k,v in stype_counts.items()],key=lambda x:x["count"],reverse=True),
            "timeline":[{"date":d,"count":timeline[d]} for d in sorted(timeline)],
            "top_orgs":[{"org":o,"count":n} for o,n in org_counts.most_common(15)],
        },
        "wh":{
            "tier":{"core":tier_counts.get("core",0),"stakes":tier_counts.get("stakes",0),"general":tier_counts.get("general",0)},
            "topics":top(topic_counts,12,TOPIC_PLAIN),
            "themes":[t for t in themes_out if t["wh"] and t["count"]>0],
            "stakes":stakes_list,
        },
        "rfi_gap":rfi_gap,
        "rfi_map":rfi_map,
        "watchlist":watch_out,
        "wh_voices":wh_voices,
        "filed_companies":filed_companies,
        "coalitions":_dedupe_coalitions(coalition_letters),
        "gcode":gcode_block,
        "mod25":mod25_block,
        "campaigns":campaigns[:12],
        "framings":top(frame_counts,12,FRAME_PLAIN),
        "themes":themes_out,
        "rfis":[t for t in themes_out if t["rfi"]],
        "keywords":[{"label":lab,"count":kw_counts.get(lab,0)} for _,lab in KEYWORDS if kw_counts.get(lab,0)>0],
        "plain_map":{THEME_META[k]["label"]:PLAIN.get(k,THEME_META[k]["label"]) for k in THEME_META},
        "rows":out_rows,
    }
    json.dump(data,open(os.path.join(BASE,"data.json"),"w"),separators=(",",":"))
    print(f"total={total} wh_relevant(LLM)={data['meta']['wh_relevant']} tiers={data['meta']['tier']}")
    print("stance:",dict(stance_counts))
    print("top specialties:",[f"{x['label']}={x['count']}" for x in data['docket']['specialties'][:6]])
    print("RFI gap:",[f"{x['label'][:20]}={x['wh']}/{x['total']}" for x in rfi_gap])
    print("framings:",[f"{x['key']}={x['count']}" for x in data['framings'][:5]])
    print(f"stakes comments: {len(stakes_list)} | attach_comments={attach_comments}")
    print(f"campaigns: {len(campaigns)} covering {camp_submissions} submissions ({camp_submissions*100//max(total,1)}% of docket); original={total-camp_submissions}")
    print(f"data.json written ({os.path.getsize(os.path.join(BASE,'data.json'))//1024} KB)")

if __name__=="__main__":
    main()
