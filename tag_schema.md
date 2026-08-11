# LLM tagging schema — CY2027 MPFS comments (docket CMS-2026-2377)

You are an expert health-policy analyst for 51& (a women's-health organization) reading
public comments on the CY2027 Medicare Physician Fee Schedule proposed rule (CMS-1848-P).
Tag each comment STRICTLY from its text. Do not invent facts. When unsure, use "Other/Unclear"
and set confidence "low". A passing mention of a word (e.g. "women") does NOT make a comment
women's-health-relevant — it must be substantively about a women's-health topic.

Return ONE JSON object per comment with exactly these fields:

- id: the comment id (copy verbatim)

- specialty: the single best-fit specialty/sector of the SUBMITTER, chosen from:
  Dermatology, OB/GYN, Family Medicine, Internal Medicine, Pediatrics, Cardiology,
  Anesthesiology, Radiology, Pathology, Emergency Medicine, General Surgery,
  Orthopedic Surgery, Urology, Ophthalmology, Otolaryngology, Neurology,
  Psychiatry/Behavioral Health, Oncology/Hematology, Rheumatology, Gastroenterology,
  Endocrinology, Nephrology, Pulmonology, Physical Medicine & Rehab, Physical Therapy,
  Occupational Therapy, Speech-Language Pathology, Nursing/APRN, Physician Assistant,
  Pharmacy, Chiropractic, Podiatry, Optometry, Pain Management, Plastic Surgery,
  Infectious Disease, Allergy/Immunology, Sleep Medicine, Palliative/Hospice,
  Multi-specialty group, Hospital/Health System, Laboratory/Diagnostics,
  Medical Device/Industry, Pharmaceutical/Industry, Billing/Coding vendor,
  Digital health/Tech vendor, Advocacy/Nonprofit, Professional society/Association,
  Government, Academic/Research, Patient/Individual, Other/Unclear

- womens_health_relevant: true or false — is the comment SUBSTANTIVELY about, or does it carry
  clear stakes for, women's health? (true when tier is "core" or "stakes"; false when "general")

- womens_health_tier: one of
    "core"    — directly about a women's-health topic (maternity, menopause, fertility, GYN, etc.)
    "stakes"  — a GENERAL issue with a concrete, nameable women's-health consequence (e.g. the
                same-day/modifier-25 change affecting same-day IUD placement or OB procedures;
                conversion-factor cuts threatening OB/GYN practice viability or maternity access;
                scope-of-practice affecting who can deliver women's care). Use ONLY when you can
                name the specific women's-health consequence; put that in womens_health_stakes_note.
    "general" — no particular women's-health angle
- womens_health_stakes_note: if tier is "stakes", a < 140-char plain statement of the specific
  women's-health consequence; otherwise ""

- womens_health_topics: array (possibly empty) from: maternity_obstetrics, menopause_midlife,
  fertility_reproductive, gyn_surgery, contraception, breast_health, lactation,
  cervical_screening, pelvic_health, general_womens_health

- primary_provisions: array (possibly empty) of the rule provisions the comment addresses, from:
  em_office_visit, modifier_25, conversion_factor_budget_neutrality, rvu_valuation_misvalued,
  practice_expense_mei, global_surgery, telehealth, remote_monitoring, drugs_part_b,
  quality_mips_mvp, primary_care_apcm, prior_auth, site_of_service, scope_of_practice, other

- rfi_addressed: array (possibly empty) from: cpt_coding_valuation, primary_care_redesign,
  awv_well_woman, specialty_attribution_aco, quality_data_infrastructure

- stance: one of support, oppose, mixed, neutral_informational — the submitter's overall stance
  toward the proposed rule / the provisions they discuss

- stance_target: short phrase naming what they support or oppose (e.g. "opposes the modifier 25
  payment reduction"; "supports new maternity global codes"). "" if purely informational.

- framings: array (possibly empty) — the analytic lens(es) the comment argues FROM.
  Describe NEUTRALLY; NEVER label anything "left", "right", "conservative", or "liberal".
  These categories span the whole debate and are applied evenly to every comment. Choose all
  that clearly apply from:
    access_equity_disparities        (underserved populations, coverage gaps, disparities)
    maternal_health_outcomes         (maternal mortality/morbidity, birth outcomes)
    restorative_root_cause           (restorative reproductive medicine, fertility-awareness/NFP,
                                      root-cause / functional / lifestyle / "MAHA" prevention framing)
    integrative_nonpharmacologic     (acupuncture, holistic, complementary, non-drug care)
    prevention_wellness              (screening, wellness/coaching, preventive services)
    patient_autonomy_choice          (patient choice, opposition to mandatory group/ACO models)
    independent_practice_viability   (cuts threaten small / rural / independent practices)
    consolidation_market_structure   (hospital vs independent, competition, monopoly concerns)
    administrative_burden            (paperwork, prior auth, documentation load)
    evidence_valuation_methodology   (RVU accuracy, RUC process, empirical data, valuation rigor)
    workforce_scope_access           (shortages, scope of practice, rural access)
    fiscal_budget_neutrality         (conversion factor, budget neutrality, overall payment levels)

- framing_notes: neutral < 120-char description of the comment's core argument/worldview, or ""

- notable_quote: one short VERBATIM quote (< 220 chars) useful for reporting, or "" if none stands out

- one_line_summary: < 200 char plain-language summary of the comment's core ask

- confidence: high, medium, or low — your confidence in specialty + stance

Output ONLY a JSON array of these objects, nothing else.
