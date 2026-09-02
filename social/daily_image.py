#!/usr/bin/env python3
"""Daily LinkedIn image generator for 51&'s 13-day comment-period push.
Reads the freshest tracker corpus, computes the day's stat, renders a branded
1200x1500 PNG via headless Chromium. Brand: 51& guide (Anchor Teal, Tre display,
Uncut Sans, no em dashes, one idea per image, problems pivot to action).

Usage: python3 daily_image.py [--date YYYY-MM-DD] [--angle KEY] [--out PATH]
Requires corpus.db (2026) and optionally corpus_2025.db in ../mpfs-comment-tracker.
"""
import sqlite3, json, os, re, sys, argparse, base64, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
# works from repo/social/ (REPO = parent) or a sibling dir of the repo checkout
_parent = os.path.dirname(HERE)
REPO = _parent if os.path.exists(os.path.join(_parent, "corpus_store.py")) \
       else os.path.join(_parent, "mpfs-comment-tracker")

INK = "#003336"; TEAL = "#06918B"; SOFT = "#64BEB5"; VGREEN = "#B1E7AE"
SGREEN = "#D1F1AF"; YGREEN = "#E8FA9E"; WHITE = "#F8FBF3"; BERRY = "#EE63A0"

KEYWORDS = [("menopaus","Menopause"),("maternal","Maternal health"),("pregnan","Pregnancy"),
    ("postpartum","Postpartum"),("obstetric","Obstetrics"),("gynecolog","Gynecology"),
    ("fertility","Fertility"),("breast","Breast health"),("cervical","Cervical screening"),
    ("contracept","Contraception"),("lactation","Lactation"),("endometriosis","Endometriosis")]


def db26():
    return sqlite3.connect(os.path.join(REPO, "corpus.db"))


def stats_keywords():
    db = db26()
    total = db.execute("SELECT count(*) FROM comments").fetchone()[0]
    rows = []
    for sub, label in KEYWORDS:
        n = db.execute("SELECT count(*) FROM comments WHERE lower(comment_text) LIKE ?",
                       (f"%{sub}%",)).fetchone()[0]
        rows.append((label, n))
    rows.sort(key=lambda x: -x[1])
    return {"total": total, "rows": rows[:8]}


def stats_meta():
    db = db26()
    r = {}
    r["total"] = db.execute("SELECT count(*) FROM comments").fetchone()[0]
    r["wh"] = db.execute("SELECT count(*) FROM comments WHERE llm_tier IN ('core','stakes')").fetchone()[0]
    r["core"] = db.execute("SELECT count(*) FROM comments WHERE llm_tier='core'").fetchone()[0]
    g = dict(db.execute("SELECT gcode_stance, count(*) FROM comments WHERE gcode_stance IS NOT NULL GROUP BY gcode_stance").fetchall())
    r["g_for"], r["g_keep"] = g.get("adopt_cpt", 0), g.get("keep_gcodes", 0)
    r["m25"] = db.execute("SELECT count(*) FROM comments WHERE llm_provisions LIKE '%modifier_25%'").fetchone()[0]
    r["m25wh"] = db.execute("SELECT count(*) FROM comments WHERE llm_provisions LIKE '%modifier_25%' AND llm_wh_relevant=1").fetchone()[0]
    try:
        wl = json.load(open(os.path.join(REPO, "watchlist.json")))
        socs = [o for gp in wl["groups"] if gp["key"] == "wh_society" for o in gp["orgs"]]
        ver = {row[0] for row in db.execute("SELECT watch_name FROM watch_hits WHERE verified=1")}
        r["soc_total"] = len(socs)
        r["soc_filed"] = sum(1 for o in socs if o["name"] in ver)
    except Exception:
        r["soc_total"], r["soc_filed"] = 18, 0
    return r


def days_left(date):
    return max(0, (datetime.date(2026, 9, 14) - date).days)


FONT = lambda fn: base64.b64encode(open(os.path.join(HERE, fn), "rb").read()).decode()

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Tre;src:url(data:font/otf;base64,{tre}) format('opentype');font-weight:400;}}
@font-face{{font-family:Uncut;src:url(data:font/woff2;base64,{ur}) format('woff2');font-weight:400;}}
@font-face{{font-family:Uncut;src:url(data:font/woff2;base64,{us}) format('woff2');font-weight:600;}}
*{{margin:0;box-sizing:border-box}}
body{{width:1200px;height:1500px;background:{INK};color:{WHITE};font-family:Uncut,sans-serif;
  display:flex;flex-direction:column;padding:96px 96px 72px;}}
.label{{font-size:26px;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:{VGREEN};margin-bottom:36px;}}
h1{{font-family:Tre,Georgia,serif;font-weight:400;font-size:{hsize}px;line-height:1.04;letter-spacing:-.01em;
  color:{WHITE};margin-bottom:20px;max-width:980px;}}
h1 .acc{{color:{BERRY};}}
.sub{{font-size:29px;line-height:1.45;color:{SOFT};max-width:920px;margin-bottom:44px;}}
.viz{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
.foot{{display:flex;justify-content:space-between;align-items:flex-end;border-top:2px solid rgba(248,251,243,.18);padding-top:30px;margin-top:48px;}}
.foot .src{{font-size:21px;color:{SOFT};line-height:1.5;max-width:760px;}}
.foot .src b{{color:{WHITE};font-weight:600;}}
.wordmark{{padding-left:74px;}}
/* bar list */
.bars{{display:flex;flex-direction:column;gap:22px;}}
.brow{{display:grid;grid-template-columns:330px 1fr 130px;align-items:center;gap:24px;}}
.blab{{font-size:30px;color:{WHITE};text-align:right;}}
.btrack{{height:40px;position:relative;}}
.bfill{{height:40px;border-radius:6px;background:{SOFT};min-width:6px;}}
.bfill.hot{{background:{VGREEN};}}
.bval{{font-size:32px;font-weight:600;color:{WHITE};font-variant-numeric:tabular-nums;}}
/* verdict pair */
.pair{{display:flex;align-items:center;gap:70px;justify-content:center;}}
.pnum{{font-family:Tre,Georgia,serif;font-size:230px;line-height:1;}}
.pnum.for{{color:{VGREEN};}}.pnum.against{{color:{BERRY};}}
.pvs{{font-size:44px;color:{SOFT};}}
.plab{{font-size:28px;color:{SOFT};max-width:330px;line-height:1.4;margin-top:18px;text-align:center;}}
.pcol{{display:flex;flex-direction:column;align-items:center;}}
/* hero number */
.hero{{text-align:center;}}
.hnum{{font-family:Tre,Georgia,serif;font-size:300px;line-height:1;color:{VGREEN};}}
.hlab{{font-size:34px;color:{SOFT};margin-top:24px;line-height:1.45;max-width:850px;margin-left:auto;margin-right:auto;}}
.cta{{font-size:29px;color:{WHITE};margin-top:44px;}}
.cta b{{color:{BERRY};font-weight:600;}}
</style></head><body>
<div class="label">{label}</div>
<h1>{headline}</h1>
<div class="sub">{sub}</div>
<div class="viz">{viz}</div>
<div class="cta">{cta}</div>
<div class="foot"><div class="src">{source}</div><div class="wordmark"><svg viewBox="0 0 228 106" style="height:74px;width:auto;display:block" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M138.507 73.4236C140.119 84.9335 151.872 92.8166 164.757 91.0323C168.994 90.4458 172.821 88.8823 175.998 86.6449C172.591 96.4587 163.639 104.132 152.259 105.709C136.333 107.915 121.692 97.3435 119.557 82.098C117.422 66.8525 128.602 52.7049 144.527 50.4997C146.678 50.2015 148.803 50.1455 150.879 50.2958C142.241 38.0905 138.235 30.1499 138.235 22.5336C138.235 7.28118 152.931 0 169.49 0C186.05 0 198.653 9.04243 198.653 17.8073C198.653 26.5721 189.38 35.1039 175.407 37.4609C175.407 37.4609 181.587 27.7399 181.587 17.2805C181.587 6.82112 174.611 3.61605 169.389 3.61605C164.312 3.61605 157.533 6.82112 157.533 17.2805C157.533 27.7399 165.187 33.8242 173.57 42.8459C181.953 51.8676 228 103.844 228 103.844H191.464C173.434 79.8261 160.37 63.5654 151.698 51.4459C142.813 55.4868 137.219 64.2179 138.508 73.4244L138.507 73.4236ZM31.6715 39.0305H29.2667V27.687H63.7585V2.09173H0V63.172C8.03988 59.9723 15.2903 58.6635 20.9655 58.6635C30.7386 58.6635 36.4138 62.4451 36.4138 68.843C36.4138 75.3873 30.5813 79.4596 21.1236 79.4596C14.187 79.4596 7.88259 77.4238 0.000770989 72.7696V98.8012C8.81934 103.601 18.2462 105.927 28.2807 105.927C52.913 105.927 68.8779 91.6756 68.8779 70.7338C68.8779 51.2466 54.3193 39.0297 31.6722 39.0297L31.6715 39.0305ZM73.0443 27.3964H83.8983V103.892H113.144V2.09173H73.0451L73.0443 27.3964ZM203.478 54.3619C204.868 54.3619 207.008 54.9738 209.446 58.3307C211.884 61.6883 213.989 63.2809 216.93 63.2809C222.943 63.2809 226.714 58.678 226.714 53.8551C226.714 49.0322 222.938 40.8822 210.51 40.8822C198.082 40.8822 194.743 51.4467 194.237 60.7444C197.648 56.472 200.757 54.3619 203.478 54.3619Z" fill="#F8FBF3"/></svg></div></div>
</body></html>"""


def render(html, out):
    tmp = os.path.join(HERE, "_tmp_card.html")
    open(tmp, "w").write(html)
    js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch({{executablePath:'/opt/pw-browsers/chromium', args:['--no-sandbox']}});
  const pg = await b.newPage({{viewport:{{width:1200,height:1500}}, deviceScaleFactor:2}});
  await pg.goto('file://{tmp}');
  await pg.waitForTimeout(700);
  await pg.screenshot({{path:'{out}'}});
  await b.close();
}})();"""
    open(os.path.join(HERE, "_shot.js"), "w").write(js)
    subprocess.run(["node", os.path.join(HERE, "_shot.js")], check=True, timeout=120)


def build(angle, date, out):
    dl = days_left(date)
    src_base = (f"<b>Source:</b> every public comment filed on Medicare's proposed 2027 "
                f"physician payment rule (docket CMS-2026-2377), read and tagged by 51&. "
                f"{date.strftime('%B %-d, %Y')}. Live tracker: <b>tracker.51and.com</b>")
    if angle == "keywords":
        s = stats_keywords()
        mx = max(n for _, n in s["rows"]) or 1
        bars = "".join(
            f'<div class="brow"><div class="blab">{lab}</div><div class="btrack">'
            f'<div class="bfill{" hot" if i==0 else ""}" style="width:{max(n/mx*100,1):.1f}%"></div></div>'
            f'<div class="bval">{n:,}</div></div>'
            for i, (lab, n) in enumerate(s["rows"]))
        html = PAGE.format(tre=FONT("VTC-Tre.woff2"), ur=FONT("UncutSans-Regular.woff2"),
            us=FONT("UncutSans-Semibold.woff2"), INK=INK, WHITE=WHITE, VGREEN=VGREEN,
            SOFT=SOFT, BERRY=BERRY, hsize=72,
            label="The 51&amp; comment tracker",
            headline=f'{s["total"]:,} comments are shaping healthcare payment. <span class="acc">Here\'s how often women\'s health comes up.</span>',
            sub="Medicare's 2027 payment rule sets the benchmark commercial insurers follow. How many comments mention each women's health term so far.",
            viz=f'<div class="bars">{bars}</div>',
            cta=f'The record closes September 14. That leaves <b>{dl} days</b> to be counted. File at <b>medicarefeeschedule.51and.com</b>',
            source=src_base)
    elif angle == "gcode":
        m = stats_meta()
        html = PAGE.format(tre=FONT("VTC-Tre.woff2"), ur=FONT("UncutSans-Regular.woff2"),
            us=FONT("UncutSans-Semibold.woff2"), INK=INK, WHITE=WHITE, VGREEN=VGREEN,
            SOFT=SOFT, BERRY=BERRY, hsize=84,
            label="The 51&amp; comment tracker",
            headline='Medicare asked how to pay for maternity care. <span class="acc">The answer is unanimous.</span>',
            sub="Comments on whether to adopt the modern maternity billing codes or keep the 40 year old bundle alive.",
            viz=(f'<div class="pair"><div class="pcol"><div class="pnum for">{m["g_for"]:,}</div>'
                 f'<div class="plab">say adopt the new maternity codes</div></div>'
                 f'<div class="pvs">vs</div>'
                 f'<div class="pcol"><div class="pnum against">{m["g_keep"]}</div>'
                 f'<div class="plab">say keep the old bundle</div></div></div>'),
            cta=f'Your voice joins the record until September 14. <b>{dl} days left.</b> tracker.51and.com',
            source=src_base)
    elif angle == "sameday":
        m = stats_meta()
        html = PAGE.format(tre=FONT("VTC-Tre.woff2"), ur=FONT("UncutSans-Regular.woff2"),
            us=FONT("UncutSans-Semibold.woff2"), INK=INK, WHITE=WHITE, VGREEN=VGREEN,
            SOFT=SOFT, BERRY=BERRY, hsize=84,
            label="The 51&amp; comment tracker",
            headline='The biggest fight in the docket <span class="acc">is missing our story.</span>',
            sub="Medicare proposes paying half for an exam done the same day as a procedure. Think of the well woman visit that becomes a biopsy or an IUD placement.",
            viz=(f'<div class="pair"><div class="pcol"><div class="pnum" style="color:{WHITE}">{m["m25"]:,}</div>'
                 f'<div class="plab">comments fight the same day cut</div></div>'
                 f'<div class="pvs">but only</div>'
                 f'<div class="pcol"><div class="pnum against">{m["m25wh"]}</div>'
                 f'<div class="plab">connect it to women\'s care</div></div></div>'),
            cta=f'We can change that in <b>{dl} days</b>. File at <b>medicarefeeschedule.51and.com</b>',
            source=src_base)
    elif angle == "societies":
        m = stats_meta()
        html = PAGE.format(tre=FONT("VTC-Tre.woff2"), ur=FONT("UncutSans-Regular.woff2"),
            us=FONT("UncutSans-Semibold.woff2"), INK=INK, WHITE=WHITE, VGREEN=VGREEN,
            SOFT=SOFT, BERRY=BERRY, hsize=84,
            label="The 51&amp; comment tracker",
            headline='Who is speaking up for <span class="acc">women\'s health?</span>',
            sub="Women's health societies with a verified letter in the docket so far. Most file in the final days. We are watching every one.",
            viz=(f'<div class="hero"><div class="hnum">{m["soc_filed"]} of {m["soc_total"]}</div>'
                 f'<div class="hlab">national women\'s health societies on the record</div></div>'),
            cta=f'The record closes in <b>{dl} days</b>. Follow the board live at <b>tracker.51and.com</b>',
            source=src_base)
    else:
        raise SystemExit(f"unknown angle {angle}")
    render(html, out)
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--angle", default="keywords")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    d = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    out = a.out or os.path.join(HERE, f"51and_daily_{d.isoformat()}_{a.angle}.png")
    build(a.angle, d, out)
