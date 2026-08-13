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
        if tier=="stakes" and (r["llm_stakes_note"] or "").strip():
            stakes_list.append({"id":r["id"],"org":(r["organization"] or "").strip(),"specialty":spec,
                "note":r["llm_stakes_note"].strip(),"quote":(r["llm_quote"] or "").strip(),
                "provisions":[PROV_PLAIN.get(p,p) for p in jl(r["llm_provisions"])][:3],"url":REG_URL.format(r["id"])})
        snippet=re.sub(r"\s+"," ",(r["comment_text"] or "")).strip()[:280]
        out_rows.append({"id":r["id"],"title":(r["title"] or "").strip(),"org":(r["organization"] or "").strip(),
            "type":st,"category":r["category"] or "","themes":[THEME_META[t]["label"] for t in themes if t in THEME_META],
            "kw":kws,"wh":bool(r["wh_flag"]),"whx":whx,"tier":tier,"specialty":spec,"stance":stance,
            "stance_target":(r["llm_stance_target"] or "").strip(),"quote":(r["llm_quote"] or "").strip(),
            "summary":(r["llm_summary"] or "").strip(),"has_attach":bool(r["llm_enriched"]),
            "rfi":jl(r["llm_rfi"]),"topics":jl(r["llm_topics"]),"framings":jl(r["llm_framings"]),"provisions":jl(r["llm_provisions"]),
            "priority":r["priority"] or "low","posted":d,"snippet":snippet,"url":REG_URL.format(r["id"],),
            "form":is_form,"cluster":(clu if is_form else -1)})

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
