#!/usr/bin/env python3
"""Build the 51&-branded 'authoritative monitor' dashboard from data.json.
Two layers: the whole docket (neutral context) and the 51& women's-health lens.
Self-contained; embeds UncutSans. Regenerate after each ingest/tag run."""
import json, os, base64, datetime
BASE=os.path.dirname(os.path.abspath(__file__))
DATA=json.load(open(os.path.join(BASE,"data.json")))
GEN=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
def fb(fn):
    p=os.path.join(BASE,"fonts",fn)
    return base64.b64encode(open(p,"rb").read()).decode() if os.path.exists(p) else ""
FONT_REG=fb("68f026f80cae49183f869d80_UncutSans-Regular.woff2")
FONT_SEMI=fb("68f026f80cae49183f869d82_UncutSans-Semibold.woff2")

HTML=r"""<!DOCTYPE html><html lang="en" data-theme="light"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Getting Women's Health on the Record: CY2027 Medicare Comment Tracker | 51&amp;</title>
<meta name="description" content="51& reads and tags every public comment on Medicare's proposed CY2027 Physician Fee Schedule: who showed up, what they said, and where women's health appears. Updated daily through September 14, 2026.">
<link rel="icon" href="https://cdn.prod.website-files.com/68f026f80cae49183f869cc9/68f026f80cae49183f869dad_asset-icon-asterix-pink.svg">
<meta property="og:title" content="Getting women's health on the record: the CY2027 Medicare comment tracker">
<meta property="og:description" content="51& reads and tags every public comment on Medicare's proposed 2027 payment rule: who's commenting, what they say, and where women's health shows up. Updated daily through September 14.">
<meta property="og:type" content="website">
<meta property="og:site_name" content="51&">
<meta property="og:url" content="https://tracker.51and.com/">
<meta property="og:image" content="https://medicarefeeschedule.51and.com/og-comments.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Medicare is deciding how women's health gets paid for in 2027. You have until Sept 14 to shape it.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Getting women's health on the record: the CY2027 Medicare comment tracker">
<meta name="twitter:description" content="Every public comment on Medicare's proposed 2027 rule, read and tagged daily, through a women's-health lens.">
<meta name="twitter:image" content="https://medicarefeeschedule.51and.com/og-comments.png">
<style>
@font-face{font-family:UncutSans;font-weight:400;font-display:swap;src:url(data:font/woff2;base64,__FONT_REG__) format('woff2');}
@font-face{font-family:UncutSans;font-weight:600;font-display:swap;src:url(data:font/woff2;base64,__FONT_SEMI__) format('woff2');}
:root{--page:#f8fbf3;--card:#fff;--ink:#003336;--text-2:#2d4a4b;--muted:#5a726f;--grid:#dbe6dc;--baseline:#b9c4c2;
--border:rgba(0,51,54,.13);--teal:#06918b;--magenta:#c2185b;--pink:#ff85b3;--green:#4a7c1b;--gold:#c98a00;--violet:#8a5cc4;
--other:#b9c4c2;--crit:#c2185b;--good:#06918b;--warn:#c98a00;--wh:#06918b;
--shadow:0 1px 2px rgba(0,51,54,.05),0 4px 16px rgba(0,51,54,.05);--serif:Georgia,"Times New Roman",serif;
--sans:UncutSans,system-ui,-apple-system,"Segoe UI",sans-serif;}
:root[data-theme="dark"]{--page:#04242a;--card:#0a2f33;--ink:#f8fbf3;--text-2:#c3d3cf;--muted:#8ba39f;--grid:#153f3f;
--baseline:#2d4a4b;--border:rgba(248,251,243,.14);--teal:#22b3ab;--magenta:#ff5f97;--green:#7bb93f;--gold:#e0a419;
--other:#46605f;--crit:#ff5f97;--good:#22b3ab;--warn:#e0a419;--wh:#22b3ab;--shadow:none;}
*{box-sizing:border-box}html,body{margin:0}
body{background:var(--page);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:var(--teal);text-decoration:none}a:hover{text-decoration:underline}
.inner{max-width:1120px;margin:0 auto;padding:0 24px}
.deadline{background:linear-gradient(90deg,#06918b,#4a7c1b 26%,#d1f1af 50%,#f4c79c 72%,#ff85b3);color:#08312f;text-align:center;font-size:13.5px;font-weight:600;padding:8px 16px}
.nav{background:var(--ink);color:#f8fbf3}.nav .inner{display:flex;align-items:center;justify-content:space-between;height:64px}
.wordmark{font-family:var(--sans);font-weight:600;font-size:26px;letter-spacing:-.02em;color:#f8fbf3;line-height:1}
.nav a.navlink{color:#cfe0dc;font-size:14px}.nav a.navlink:hover{color:#fff}
.toggle{background:transparent;border:1px solid rgba(248,251,243,.28);color:#e7efec;border-radius:100px;padding:7px 15px;cursor:pointer;font-family:var(--sans);font-size:13px;margin-left:16px}
.hero{background:var(--ink);color:#f8fbf3;padding:50px 0 20px}
.eyebrow{font-family:var(--sans);font-size:12px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:#8fd14f;margin:0 0 16px}
.hero h1{font-family:var(--serif);font-weight:400;font-size:50px;line-height:1.05;letter-spacing:-.015em;margin:0 0 18px;max-width:19ch}
.hero h1 .accent{color:var(--pink)}
.hero p.lede{font-size:19px;color:#dce7e3;max-width:62ch;margin:0 0 24px}.hero p.lede b{color:#fff;font-weight:600}
.cta-row{display:flex;gap:12px;flex-wrap:wrap}
.btn{font-family:var(--sans);font-size:15px;font-weight:600;border-radius:100px;padding:14px 26px;cursor:pointer;border:1.5px solid transparent;display:inline-flex;align-items:center;gap:8px}
.btn-pink{background:var(--pink);color:#08312f}.btn-pink:hover{background:#ff9cc2;text-decoration:none}
.btn-ghost{background:transparent;color:#f8fbf3;border-color:rgba(248,251,243,.4)}.btn-ghost:hover{border-color:#fff;text-decoration:none}
.kpiband{background:var(--ink);padding:26px 0 46px}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}
@media(max-width:1020px){.kpis{grid-template-columns:repeat(3,1fr)}}
@media(max-width:820px){.kpis{grid-template-columns:repeat(2,1fr)}.hero h1{font-size:36px}}
.kpi{background:rgba(248,251,243,.06);border:1px solid rgba(248,251,243,.12);border-radius:16px;padding:18px}
.kpi.click{cursor:pointer}.kpi.click:hover{border-color:var(--pink)}
.kpi .v{font-size:29px;font-weight:600;letter-spacing:-.02em;line-height:1;color:#f8fbf3}
.kpi .l{color:#bcd0cb;font-size:12.5px;margin-top:8px;font-weight:600}.kpi .x{color:#8ba39f;font-size:11.5px;margin-top:4px}
.kpi.wh .v{color:#5fd3c9}.kpi.crit .v{color:var(--pink)}
main{padding:8px 0 40px}
.layer{border-top:2px solid var(--ink);margin:46px 0 26px;padding-top:16px}
.layer .tag{font-family:var(--sans);font-size:12px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--teal)}
.layer h2{font-family:var(--serif);font-weight:400;font-size:34px;line-height:1.08;margin:6px 0 8px;color:var(--ink)}
.layer p.intro{color:var(--text-2);font-size:15px;max-width:76ch;margin:0}
section{margin:0 0 26px}
.sec-head{margin:0 0 16px}.sec-head .eyebrow{color:var(--teal)}
.sec-h{font-family:var(--serif);font-weight:400;font-size:24px;line-height:1.12;color:var(--ink);margin:0 0 4px}
.hint{color:var(--text-2);font-size:13.5px;margin:0 0 16px;max-width:74ch}
.panel{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:24px 26px;box-shadow:var(--shadow)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:22px}@media(max-width:820px){.grid2{grid-template-columns:1fr}}
.method{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--teal);border-radius:12px;padding:16px 20px;margin:22px 0 0}
.method b{color:var(--ink)}.method p{margin:0;color:var(--text-2);font-size:13px;line-height:1.6}
.legend{display:flex;gap:16px;font-size:12.5px;color:var(--text-2);margin:0 0 14px;flex-wrap:wrap}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:7px;vertical-align:middle}
.bars{display:flex;flex-direction:column;gap:10px}
.bar{display:grid;grid-template-columns:200px 1fr 46px;align-items:center;gap:12px}
@media(max-width:560px){.bar{grid-template-columns:130px 1fr 38px}}
.bar.clk{cursor:pointer;border-radius:8px;padding:3px 8px;margin:0 -8px;transition:background .12s}.bar.clk .val{position:relative;padding-right:15px}.bar.clk .val::after{content:"\203A";position:absolute;right:2px;top:50%;transform:translateY(-50%);color:var(--baseline);font-weight:700}.bar.clk:hover{background:rgba(6,145,139,.08)}.bar.clk:hover .fill{filter:brightness(1.08)}.bar.clk:hover .lab{color:var(--ink)}.bar.clk:hover .val::after{color:var(--teal)}
.bar .lab{font-size:13px;color:var(--text-2);text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar .track{background:linear-gradient(var(--grid),var(--grid)) left center/100% 2px no-repeat;height:22px;position:relative}
.bar .fill{height:22px;border-radius:5px;min-width:3px;transition:width .5s cubic-bezier(.2,.7,.2,1)}
.bar .val{font-size:13px;color:var(--ink);font-variant-numeric:tabular-nums;font-weight:600}
/* stacked stance bar */
.stack{display:flex;height:34px;border-radius:8px;overflow:hidden;border:1px solid var(--border)}
.stack .seg{display:flex;align-items:center;justify-content:center;color:#fff;font-size:12.5px;font-weight:600;min-width:2px}
.stackleg{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px;font-size:13px;color:var(--text-2)}
.stackleg i{width:11px;height:11px;border-radius:3px;display:inline-block;margin-right:6px;vertical-align:middle}
/* tier */
.tierrow{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}
.tierstat{flex:1;min-width:200px}
.tierstat .big{font-family:var(--serif);font-size:40px;color:var(--teal);line-height:1}
.tierstat .sub{color:var(--text-2);font-size:13.5px;margin-top:6px}
/* rfi two-tone */
.rfibar{display:grid;grid-template-columns:220px 1fr 92px;align-items:center;gap:12px;margin-bottom:11px}
@media(max-width:560px){.rfibar{grid-template-columns:130px 1fr 76px}}
.rfibar.clk{cursor:pointer}.rfibar.clk:hover .whb{filter:brightness(1.12)}.rfibar.clk:hover .pl{color:var(--ink)}
.rfibar .lab{font-size:13px;color:var(--text-2);text-align:right;line-height:1.2;overflow:hidden}
.rfibar .lab .pl{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rfibar .lab .sub{display:block;font-size:10.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;letter-spacing:.02em;margin-top:1px}
.rfibar.hot .lab .pl{color:var(--magenta);font-weight:600}
.activef{display:inline-flex;align-items:center;gap:8px;background:rgba(6,145,139,.12);color:var(--teal);border:1px solid var(--teal);border-radius:100px;padding:6px 13px;font-size:12.5px;font-weight:600;cursor:pointer}
:root[data-theme=dark] .activef{background:rgba(34,179,171,.16)}
.rfitrack{background:var(--grid);height:24px;border-radius:5px;position:relative;overflow:hidden}
.rfitrack .tot{position:absolute;left:0;top:0;bottom:0;background:var(--other);border-radius:5px}
.rfitrack .whb{position:absolute;left:0;top:0;bottom:0;background:var(--teal);border-radius:5px}
.rfibar .rval{font-size:12.5px;color:var(--ink);font-variant-numeric:tabular-nums;text-align:right}
.rfibar .rval b{color:var(--teal)}
/* stakes cards */
.stakes{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:760px){.stakes{grid-template-columns:1fr}}
/* G-code verdict */
.verdict{display:flex;gap:34px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
.vnum{font-family:var(--serif);font-size:58px;line-height:1;letter-spacing:-.02em}
.vnum.for{color:var(--teal)}.vnum.against{color:var(--magenta)}
.vs{font-size:20px;color:var(--muted)}
.vlab{font-size:12.5px;color:var(--text-2);margin-top:6px;max-width:24ch}
.meter{display:flex;height:30px;border-radius:8px;overflow:hidden;gap:2px;margin:6px 0 8px}
.meter .seg{min-width:4px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;font-weight:600}
.quotes{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:16px}
@media(max-width:820px){.quotes{grid-template-columns:1fr}}
/* who's-speaking-up board */
.board{display:flex;flex-wrap:wrap;gap:9px;margin:6px 0 2px}
.borg{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--border);border-radius:100px;padding:8px 14px;font-size:13px;color:var(--text-2);background:var(--page)}
.borg .dot{width:9px;height:9px;border-radius:50%;background:var(--baseline);flex:none}
.borg.on{border-color:var(--teal);color:var(--ink);font-weight:600}.borg.on .dot{background:var(--teal)}
.bhead{font-size:12px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:18px 0 8px}
.bhead:first-child{margin-top:0}
.bnote{color:var(--text-2);font-size:13px;margin-top:12px;max-width:76ch}
.voices{display:flex;flex-direction:column;gap:8px;margin-top:4px}
.vrow{display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:center;border:1px solid var(--border);border-radius:12px;padding:9px 14px;background:var(--page);font-size:13.5px}
.vrow .nm{color:var(--ink);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vrow .ty{color:var(--muted);font-size:12px;white-space:nowrap}
/* push cards */
.push{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-top:16px}@media(max-width:760px){.push{grid-template-columns:1fr}}
.pcard{border:1px solid var(--border);border-left:3px solid var(--magenta);border-radius:14px;padding:15px 17px;background:var(--page)}
.pcard .big{font-family:var(--serif);font-size:30px;color:var(--magenta);line-height:1}
.pcard .p{font-size:13px;color:var(--text-2);margin-top:6px;line-height:1.5}.pcard b{color:var(--ink)}
/* RFI cards v2 */
.rficard{border:1px solid var(--border);border-radius:14px;background:var(--page);margin-bottom:12px;overflow:hidden}
.rficard summary{list-style:none;cursor:pointer;padding:14px 18px}
.rficard summary::-webkit-details-marker{display:none}
.rficard .rline{display:grid;grid-template-columns:230px 1fr 96px auto;gap:12px;align-items:center}
@media(max-width:640px){.rficard .rline{grid-template-columns:1fr 84px auto}.rficard .rline .rtrackwrap{display:none}}
.digbtn{display:inline-flex;align-items:center;gap:6px;background:var(--pink);color:#08312f;border-radius:100px;padding:8px 16px;font-size:12.5px;font-weight:600;white-space:nowrap}
.rficard summary:hover .digbtn{background:#ff9cc2}
details[open] .digbtn span:first-child{display:none}
details[open] .digbtn::before{content:"Close"}
details[open] .digbtn{background:transparent;border:1px solid var(--border);color:var(--text-2)}
.rficard .body{padding:4px 18px 18px;border-top:1px solid var(--border)}
.rfth{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 2px}
.rfth .chip b{color:var(--teal)}
.asklist{margin:8px 0 0;padding:0;list-style:none}
.asklist li{font-size:13.5px;color:var(--text-2);padding:8px 0;border-top:1px dashed var(--border);line-height:1.5}
.asklist li b.who{color:var(--ink)}
.wtag{font-size:10.5px;color:var(--teal);border:1px solid var(--teal);border-radius:100px;padding:1px 8px;font-weight:600;margin-left:6px;white-space:nowrap}
.asked{font-size:13.5px;color:var(--ink);font-weight:600;margin:10px 0 2px}
.decoder{display:flex;flex-direction:column;gap:5px;margin:10px 0 2px}
.decoder .dt{font-size:12.5px;color:var(--text-2);line-height:1.5}
.decoder .dt b{color:var(--ink)}
.consider{margin:4px 0 0;padding:0;list-style:none}
.consider li{font-size:13.5px;color:var(--text-2);padding:2px 0 2px 12px;border-left:2px solid var(--teal);margin:8px 0;line-height:1.5}
.whywh{font-size:13px;color:var(--text-2);line-height:1.55;margin:4px 0 0}
.caret{color:var(--muted);transition:transform .15s}
details[open] .caret{transform:rotate(90deg)}
.scard{border:1px solid var(--border);border-radius:14px;padding:16px 18px;background:var(--page)}
.scard .note{font-weight:600;color:var(--ink);font-size:14px;line-height:1.4}
.scard .q{color:var(--text-2);font-size:13px;font-style:italic;margin:8px 0;line-height:1.5;border-left:2px solid var(--teal);padding-left:10px}
.scard .meta{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted);margin-top:8px;gap:8px}
.scard .meta a{white-space:nowrap}
.feature{border:1px solid var(--teal);box-shadow:0 2px 22px rgba(6,145,139,.13)}.camp-split{margin-bottom:16px}.camp-list{display:flex;flex-direction:column;gap:9px;margin-top:4px}.camprow{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;cursor:pointer;border:1px solid var(--border);border-radius:12px;padding:11px 14px;background:var(--page);transition:border-color .12s,background .12s}.camprow:hover{border-color:var(--teal);background:rgba(6,145,139,.05)}.camprow .txt{font-size:13.5px;color:var(--text-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}.camprow .txt b{color:var(--ink);font-weight:600}.camprow .n{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;color:var(--muted);white-space:nowrap}.camprow .n .cnt{font-weight:700;color:var(--teal);font-variant-numeric:tabular-nums}.camprow .whtag{font-size:10.5px;color:var(--magenta);border:1px solid var(--magenta);border-radius:100px;padding:1px 8px;font-weight:600}.camplead{display:flex;gap:22px;flex-wrap:wrap;margin-bottom:4px}.camplead .cell .big{font-family:var(--serif);font-size:34px;line-height:1;color:var(--ink)}.camplead .cell .big.mag{color:var(--magenta)}.camplead .cell .sub{color:var(--text-2);font-size:12.5px;margin-top:5px}.kwrap{display:flex;flex-wrap:wrap;gap:9px}
.kw{cursor:pointer;border:1px solid var(--border);background:var(--page);border-radius:100px;padding:8px 15px;font-size:13.5px;color:var(--text-2);display:inline-flex;gap:8px;align-items:center}
.kw:hover{border-color:var(--teal);color:var(--ink)}.kw b{color:var(--teal)}
.suggest{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.suggest input{background:var(--page);border:1px solid var(--border);color:var(--ink);border-radius:100px;padding:11px 16px;font-size:14px;font-family:var(--sans);flex:1;min-width:190px}
.tt{position:fixed;pointer-events:none;background:var(--ink);color:var(--page);padding:7px 10px;border-radius:9px;font-size:12.5px;opacity:0;transition:opacity .1s;z-index:60;box-shadow:var(--shadow);max-width:280px}
:root[data-theme=dark] .tt{background:#0a2f33;border:1px solid var(--border);color:var(--ink)}
svg{display:block;width:100%;height:auto;overflow:visible}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:16px}
.filters input,.filters select{background:var(--page);border:1px solid var(--border);color:var(--ink);border-radius:100px;padding:9px 14px;font-size:13.5px;font-family:var(--sans)}
.filters input[type=search]{min-width:200px;flex:1}
.chk{display:flex;align-items:center;gap:7px;color:var(--text-2);font-size:13.5px;cursor:pointer}
.clearbtn{background:transparent;border:1px solid var(--border);color:var(--text-2);border-radius:100px;padding:9px 16px;cursor:pointer;font-size:13.5px;font-family:var(--sans)}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:11px 12px;border-bottom:1px solid var(--border);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.05em;cursor:pointer;white-space:nowrap}
td.date{color:var(--text-2);font-variant-numeric:tabular-nums;white-space:nowrap}
.tt-org{color:var(--text-2);font-size:12.5px}
.summ{color:var(--text-2);font-size:12.5px;margin-top:3px;line-height:1.4}
.chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:5px}
.chip{font-size:11.5px;padding:2px 9px;border-radius:100px;background:var(--page);border:1px solid var(--border);color:var(--text-2)}
.chip.core{border-color:var(--teal);color:var(--teal);font-weight:600}
.chip.stakes{border-color:var(--gold);color:#8a6100;font-weight:600}
.chip.att{border-color:var(--violet);color:var(--violet)}
.pill{font-size:11.5px;padding:2px 10px;border-radius:100px;font-weight:600;white-space:nowrap}
.pill.oppose{background:rgba(194,24,91,.13);color:var(--crit)}
.pill.support{background:rgba(6,145,139,.14);color:#046b66}
.pill.mixed{background:rgba(201,138,0,.16);color:#8a6100}
.pill.neutral_informational{background:var(--page);color:var(--muted)}
:root[data-theme=dark] .pill.support{color:var(--good)}:root[data-theme=dark] .pill.mixed{color:var(--gold)}
.more{margin:18px auto 0;display:block;background:var(--pink);border:none;color:#08312f;border-radius:100px;padding:11px 24px;cursor:pointer;font-size:14px;font-weight:600;font-family:var(--sans)}
.count{color:var(--text-2);font-size:12.5px;margin-left:auto}
footer{background:var(--ink);color:#cfe0dc;padding:40px 0 48px;margin-top:20px}
footer .wordmark{margin-bottom:12px}footer .fnote{font-size:13px;color:#9fb8b3;max-width:76ch}footer a{color:#7fd3c9}
</style></head><body>
<div class="deadline">Federal comments on the CY2027 Medicare rule close September 14, 2026. <span id="deadlineDays"></span></div>
<nav class="nav"><div class="inner">
  <a href="https://51and.com" target="_blank" rel="noopener" class="wordmark" aria-label="51&amp;"><svg viewBox="0 0 228 106" style="height:30px;width:auto;display:block" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M138.507 73.4236C140.119 84.9335 151.872 92.8166 164.757 91.0323C168.994 90.4458 172.821 88.8823 175.998 86.6449C172.591 96.4587 163.639 104.132 152.259 105.709C136.333 107.915 121.692 97.3435 119.557 82.098C117.422 66.8525 128.602 52.7049 144.527 50.4997C146.678 50.2015 148.803 50.1455 150.879 50.2958C142.241 38.0905 138.235 30.1499 138.235 22.5336C138.235 7.28118 152.931 0 169.49 0C186.05 0 198.653 9.04243 198.653 17.8073C198.653 26.5721 189.38 35.1039 175.407 37.4609C175.407 37.4609 181.587 27.7399 181.587 17.2805C181.587 6.82112 174.611 3.61605 169.389 3.61605C164.312 3.61605 157.533 6.82112 157.533 17.2805C157.533 27.7399 165.187 33.8242 173.57 42.8459C181.953 51.8676 228 103.844 228 103.844H191.464C173.434 79.8261 160.37 63.5654 151.698 51.4459C142.813 55.4868 137.219 64.2179 138.508 73.4244L138.507 73.4236ZM31.6715 39.0305H29.2667V27.687H63.7585V2.09173H0V63.172C8.03988 59.9723 15.2903 58.6635 20.9655 58.6635C30.7386 58.6635 36.4138 62.4451 36.4138 68.843C36.4138 75.3873 30.5813 79.4596 21.1236 79.4596C14.187 79.4596 7.88259 77.4238 0.000770989 72.7696V98.8012C8.81934 103.601 18.2462 105.927 28.2807 105.927C52.913 105.927 68.8779 91.6756 68.8779 70.7338C68.8779 51.2466 54.3193 39.0297 31.6722 39.0297L31.6715 39.0305ZM73.0443 27.3964H83.8983V103.892H113.144V2.09173H73.0451L73.0443 27.3964ZM203.478 54.3619C204.868 54.3619 207.008 54.9738 209.446 58.3307C211.884 61.6883 213.989 63.2809 216.93 63.2809C222.943 63.2809 226.714 58.678 226.714 53.8551C226.714 49.0322 222.938 40.8822 210.51 40.8822C198.082 40.8822 194.743 51.4467 194.237 60.7444C197.648 56.472 200.757 54.3619 203.478 54.3619Z" fill="#f8fbf3"/></svg></a>
  <div style="display:flex;align-items:center">
    <a class="navlink" href="https://medicarefeeschedule.51and.com/" target="_blank" rel="noopener">Learn more about 51&amp; &rarr;</a>
    <button class="toggle" id="themeBtn">Dark mode</button></div>
</div></nav>
<header class="hero"><div class="inner">
  <p class="eyebrow">Live comment tracker &middot; Docket CMS-2026-2377 &middot; Updated daily</p>
  <h1>Getting women's health <span class="accent">on the record.</span></h1>
  <p class="lede">Public comment shapes Medicare's 2027 physician-payment rule, which will be felt well beyond Medicare. We're reading every comment as it lands (<b id="heroCount"></b> so far, letters and attachments in full) and tracking whether women's health is being heard.</p>
  <div class="cta-row">
    <a class="btn btn-pink" href="https://medicarefeeschedule.51and.com/file" target="_blank" rel="noopener">File a comment &rarr;</a>
    <a class="btn btn-ghost" href="https://medicarefeeschedule.51and.com/" target="_blank" rel="noopener">Read 51&amp;'s full analysis &darr;</a></div>
</div></header>
<div class="kpiband"><div class="inner"><div class="kpis" id="kpis"></div></div></div>
<main class="inner">
  <div class="method"><p><b>How to read this.</b> A census of every comment on docket CMS-2026-2377: who showed up, not a poll. Full text read, including <span id="attachN"></span> attached letters. Tags are descriptive, not political. Updated daily.</p></div>

  <div class="layer"><div class="tag">The 51&amp; scorecard</div>
    <h2>Is women's health getting on the record?</h2></div>

  <section><div class="sec-head"><p class="eyebrow">The women's-health signal</p><h2 class="sec-h">How many comments touch women's health</h2></div>
    <div class="panel"><div class="tierrow">
      <div class="tierstat"><div class="big" id="tierBig"></div><div class="sub" id="tierSub"></div></div>
      <div style="flex:2;min-width:260px"><div class="stack" id="tierStack"></div><div class="stackleg" id="tierLeg"></div></div>
    </div>
    <div class="push" id="pushGrid"></div></div></section>

  <section><div class="sec-head"><p class="eyebrow">Keyword tracker</p><h2 class="sec-h">Women's-health terms in the comments</h2>
    <p class="hint">How often each term appears across the comments submitted so far. Click a keyword to read those comments.</p></div>
    <div class="panel"><div class="kwrap" id="kwrap"></div></div></section>

  <section id="gcode"><div class="sec-head"><p class="eyebrow">The maternity-codes verdict</p><h2 class="sec-h">The G-code question: the docket has answered</h2>
    <p class="hint">CMS asked whether to adopt the new 2027 maternity CPT codes or keep the old bundle alive through &ldquo;GMAT&rdquo; G-codes. Every comment that engages the question, counted. Click a number to read them.</p></div>
    <div class="panel feature">
      <div class="verdict" id="gcodeVerdict"></div>
      <div class="meter" id="gcodeMeter"></div><div class="stackleg" id="gcodeLeg"></div>
      <div class="quotes" id="gcodeQuotes"></div>
    </div></section>

  <section id="whoSpeaks"><div class="sec-head"><p class="eyebrow">Who's speaking up</p><h2 class="sec-h">Organizations on the record</h2>
    <p class="hint">Filers identified from each letter's letterhead and signature. Most societies file in the final days. This board updates daily.</p></div>
    <div class="panel" id="watchPanel"></div></section>

  <section id="mod25"><div class="sec-head"><p class="eyebrow">The same-day cut</p><h2 class="sec-h">The biggest fight in the comments, told almost entirely without women</h2>
    <p class="hint">CMS proposes paying half for an exam billed the same day as a procedure, including the well-woman visit that becomes a biopsy, an IUD insertion, or a colposcopy. Who's commenting on it:</p></div>
    <div class="panel"><div class="verdict" id="m25Lead"></div><div class="bars" id="m25Bars"></div></div></section>

  <section><div class="sec-head"><p class="eyebrow">The opportunity map</p><h2 class="sec-h">The five RFIs: what's on the record, what's missing</h2>
    <p class="hint">An RFI (&ldquo;request for information&rdquo;) is CMS thinking out loud: no policy is proposed yet, and the answers shape what lands in future rules. CMS includes a few in every fee-schedule proposal. This year's five are below. What CMS asked, what commenters are saying, and what women's health should bring. Click a question to open it.</p></div>
    <div id="rfiWrap"></div></section>

  <section><div class="sec-head"><p class="eyebrow">The hidden stakes</p><h2 class="sec-h">General fights with a women's-health consequence</h2>
    <p class="hint">These comments never mention women's health as their topic, but each carries a specific, nameable consequence for women's care. This is the connective tissue most readers miss.</p></div>
    <div class="panel"><div class="stakes" id="stakesGrid"></div><button class="more" id="stakesMore" style="display:none">Show all <span id="stakesN"></span> &darr;</button></div></section>

  <section><div class="sec-head"><p class="eyebrow">Directly about women's health</p><h2 class="sec-h">What the core comments cover</h2><p class="hint">Click any bar to filter the browser below.</p></div>
    <div class="panel"><div class="bars" id="topicBars"></div></div></section>

  <div class="layer"><div class="tag">The whole record, in context</div>
    <h2>Who showed up, and what they said</h2>
    <p class="intro">The neutral backdrop behind the scorecard: every comment, characterized without a women's-health filter.</p></div>

  <section><div class="sec-head"><p class="eyebrow">Overall sentiment</p><h2 class="sec-h">The docket is an opposition document</h2>
    <p class="hint">Each comment's stance toward the proposed rule or the provisions it addresses.</p></div>
    <div class="panel"><div class="stack" id="stanceStack"></div><div class="stackleg" id="stanceLeg"></div></div></section>

  <div class="grid2">
    <section><div class="sec-head"><p class="eyebrow">Who's commenting</p><h2 class="sec-h">By specialty</h2>
      <p class="hint">Inferred from each letter. Click any bar to filter the browser below.</p></div>
      <div class="panel"><div class="bars" id="specBars"></div></div></section>
    <section><div class="sec-head"><p class="eyebrow">Who's commenting</p><h2 class="sec-h">By submitter type</h2><p class="hint">Who filed each comment. Click any bar to filter the browser below.</p></div>
      <div class="panel"><div class="bars" id="typeBars"></div></div></section>
  </div>

  <section id="campaigns"><div class="sec-head"><p class="eyebrow">How organic is the docket</p><h2 class="sec-h">Original comments vs. organized campaigns</h2><p class="hint">Many comments are near-identical templates from an organized campaign, sometimes with a single sentence changed. We group them by text similarity, applied evenly to every campaign and every viewpoint. Agencies weigh unique, substantive comments differently from mass submissions, so this separates the two. Click any campaign to read it.</p></div>
    <div class="panel">
      <div class="camplead"><div class="cell"><div class="big" id="origBig"></div><div class="sub">original / individual comments</div></div><div class="cell"><div class="big mag" id="campBig"></div><div class="sub" id="campSub">in organized template campaigns</div></div></div>
      <div class="camp-split"><div class="stack" id="campStack"></div><div class="stackleg" id="campLeg"></div></div>
      <div class="camp-list" id="campList"></div>
    </div></section>

  <section><div class="sec-head"><p class="eyebrow">What the rule fight is about</p><h2 class="sec-h">The provisions drawing fire</h2>
    <p class="hint">Which parts of the proposed rule each comment addresses. Click any bar to filter the browser below.</p></div>
    <div class="panel"><div class="bars" id="provBars"></div></div></section>

  <section><div class="sec-head"><p class="eyebrow">Submissions over time</p><h2 class="sec-h">The run-up to September 14</h2></div>
    <div class="panel"><div id="timeline"></div></div></section>

  <section><div class="sec-head"><p class="eyebrow">Help shape the tracker</p><h2 class="sec-h">Suggest a topic to track</h2>
    <p class="hint">See something we're missing, from any point of view? Tell us and we'll consider adding it to the watch-list.</p></div>
    <div class="panel"><div class="suggest">
      <input id="sgTopic" placeholder="Topic or keyword (e.g. pelvic floor therapy)"><input id="sgWhy" placeholder="Why it matters (optional)">
      <input id="sgEmail" type="email" placeholder="Your email (optional)"><button class="btn btn-pink" id="sgBtn" style="padding:11px 22px;font-size:14px">Send suggestion &rarr;</button></div>
      <div id="sgMsg" class="hint" style="margin:12px 0 0"></div></div></section>

  <section><div class="sec-head"><p class="eyebrow">Framings across the debate</p><h2 class="sec-h">How commenters argue, from every side</h2>
    <p class="hint">Descriptive lenses applied evenly to every comment, never labeled political. Restorative/root-cause (the RRM/MAHA framing) sits here as one row among many. Click any bar to filter.</p></div>
    <div class="panel"><div class="bars" id="frameBars"></div></div></section>

  <section id="browser"><div class="sec-head"><p class="eyebrow">Comment browser</p><h2 class="sec-h">Search every comment</h2>
    <p class="hint">Full-text search plus specialty, stance, and women's-health tier. Click a title to open it on Regulations.gov.</p></div>
    <div class="panel"><div class="filters">
      <input type="search" id="q" placeholder="Search title, organization, summary&hellip;">
      <select id="fSpec"><option value="">All specialties</option></select>
      <select id="fStance"><option value="">All stances</option><option value="oppose">Oppose</option><option value="support">Support</option><option value="mixed">Mixed</option><option value="neutral_informational">Neutral</option></select>
      <select id="fTier"><option value="">All comments</option><option value="core">Women's health · core</option><option value="stakes">Women's health · stakes</option><option value="general">General</option></select>
      <select id="fForm"><option value="">All comments</option><option value="orig">Original only</option><option value="camp">Campaigns only</option></select>
      <select id="fTheme"><option value="">All themes</option></select>
      <select id="fKw"><option value="">All keywords</option></select>
      <button class="clearbtn" id="clearBtn">Clear</button>
      <span id="activeFilter"></span>
      <span class="count" id="rowCount"></span></div>
      <table><thead><tr><th data-k="posted">Posted</th><th data-k="title">Comment / organization</th><th data-k="specialty">Specialty</th><th data-k="stance">Stance</th></tr></thead><tbody id="tbody"></tbody></table>
      <button class="more" id="moreBtn">Show more</button></div></section>

</main>
<footer><div class="inner"><div class="wordmark"><svg viewBox="0 0 228 106" style="height:34px;width:auto;display:block" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M138.507 73.4236C140.119 84.9335 151.872 92.8166 164.757 91.0323C168.994 90.4458 172.821 88.8823 175.998 86.6449C172.591 96.4587 163.639 104.132 152.259 105.709C136.333 107.915 121.692 97.3435 119.557 82.098C117.422 66.8525 128.602 52.7049 144.527 50.4997C146.678 50.2015 148.803 50.1455 150.879 50.2958C142.241 38.0905 138.235 30.1499 138.235 22.5336C138.235 7.28118 152.931 0 169.49 0C186.05 0 198.653 9.04243 198.653 17.8073C198.653 26.5721 189.38 35.1039 175.407 37.4609C175.407 37.4609 181.587 27.7399 181.587 17.2805C181.587 6.82112 174.611 3.61605 169.389 3.61605C164.312 3.61605 157.533 6.82112 157.533 17.2805C157.533 27.7399 165.187 33.8242 173.57 42.8459C181.953 51.8676 228 103.844 228 103.844H191.464C173.434 79.8261 160.37 63.5654 151.698 51.4459C142.813 55.4868 137.219 64.2179 138.508 73.4244L138.507 73.4236ZM31.6715 39.0305H29.2667V27.687H63.7585V2.09173H0V63.172C8.03988 59.9723 15.2903 58.6635 20.9655 58.6635C30.7386 58.6635 36.4138 62.4451 36.4138 68.843C36.4138 75.3873 30.5813 79.4596 21.1236 79.4596C14.187 79.4596 7.88259 77.4238 0.000770989 72.7696V98.8012C8.81934 103.601 18.2462 105.927 28.2807 105.927C52.913 105.927 68.8779 91.6756 68.8779 70.7338C68.8779 51.2466 54.3193 39.0297 31.6722 39.0297L31.6715 39.0305ZM73.0443 27.3964H83.8983V103.892H113.144V2.09173H73.0451L73.0443 27.3964ZM203.478 54.3619C204.868 54.3619 207.008 54.9738 209.446 58.3307C211.884 61.6883 213.989 63.2809 216.93 63.2809C222.943 63.2809 226.714 58.678 226.714 53.8551C226.714 49.0322 222.938 40.8822 210.51 40.8822C198.082 40.8822 194.743 51.4467 194.237 60.7444C197.648 56.472 200.757 54.3619 203.478 54.3619Z" fill="#f8fbf3"/></svg></div><div class="fnote" id="foot"></div></div></footer>
<div class="tt" id="tip"></div>
<script>
const DATA=/*__DATA__*/;const $=s=>document.querySelector(s);
const esc=s=>(s||"").replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt=n=>n.toLocaleString();const PLAIN=DATA.plain_map||{};const tip=$("#tip");
function showTip(e,h){tip.innerHTML=h;tip.style.opacity=1;mv(e);}
function mv(e){let x=e.clientX+14,y=e.clientY+14;if(x+tip.offsetWidth>innerWidth)x=e.clientX-tip.offsetWidth-14;if(y+tip.offsetHeight>innerHeight)y=e.clientY-tip.offsetHeight-14;tip.style.left=x+"px";tip.style.top=y+"px";}
function hideTip(){tip.style.opacity=0;}
const themeBtn=$("#themeBtn");function setThemeLabel(){themeBtn.textContent=document.documentElement.dataset.theme==="dark"?"☀ Light mode":"☾ Dark mode";}setThemeLabel();themeBtn.onclick=()=>{const r=document.documentElement;r.dataset.theme=r.dataset.theme==="dark"?"light":"dark";setThemeLabel();renderTimeline();};
const M=DATA.meta,D=DATA.docket,W=DATA.wh;
const days=Math.max(0,Math.ceil((new Date(M.deadline+"T23:59:59Z")-new Date())/864e5));
$("#deadlineDays").textContent=days+" days left.";$("#heroCount").textContent=fmt(M.total)+" comments";
$("#attachN").textContent=fmt(M.attach_comments);
const oppose=(D.stance.find(s=>s.key==='oppose')||{}).count||0;
const GC=DATA.gcode||{counts:{},samples:[]};const gFor=GC.counts.adopt_cpt||0,gKeep=GC.counts.keep_gcodes||0,gMix=GC.counts.mixed||0;
const WLIST=DATA.watchlist||[];const socAll=WLIST.filter(w=>w.group==='wh_society'),socOn=socAll.filter(w=>w.filed);
const M25=DATA.mod25||{total:0,wh:0,by_spec:[]};
const kpis=[
 {v:fmt(M.total),l:"Comments read: every one, in full",x:(M.docket_total&&M.docket_total>M.total)?("of "+fmt(M.docket_total)+" filed so far; catching up as the surge lands"):("Docket "+M.docket+", updated daily"),f:{}},
 {v:fmt(M.wh_relevant),l:"Women's-health–relevant comments",x:M.tier.core+" directly about it · "+M.tier.stakes+" hidden stakes",cls:"wh",f:{tier:"wh"}},
 {v:fmt(gFor)+"–"+fmt(gKeep),l:"New maternity codes vs. G-code snap-back",x:"the verdict in the comments so far",cls:"wh",go:"#gcode"},
 {v:socOn.length+" of "+socAll.length,l:"Women's-health societies on the record",x:"major letters land near the deadline",cls:"crit",go:"#whoSpeaks"},
 {v:Math.round(oppose/M.total*100)+"%",l:"Oppose the rule",x:fmt(oppose)+" of "+fmt(M.total)+" comments read",f:{stance:"oppose"}},
 {v:days,l:"Days to deadline",x:"Comments due Sep 14, 2026"}];
$("#kpis").innerHTML=kpis.map((k,i)=>`<div class="kpi ${k.cls||''} ${(k.f||k.go)?'click':''}" data-i="${i}"><div class="v">${k.v}</div><div class="l">${k.l}</div><div class="x">${k.x}</div></div>`).join("");
document.querySelectorAll(".kpi.click").forEach(el=>el.onclick=()=>{const k=kpis[+el.dataset.i];if(k.go)document.querySelector(k.go).scrollIntoView({behavior:"smooth"});else applyFilter(k.f);});

function bars(el,items,{color,max,tipf,onClick}){const mx=max||Math.max(...items.map(i=>i.count),1);
 el.innerHTML=items.map((i,x)=>{const w=(i.count/mx*100).toFixed(1);const c=typeof color=="function"?color(i):color;
  return `<div class="bar ${onClick?'clk':''}" data-x="${x}"><div class="lab" title="${esc(i.full||i.label)}">${esc(i.label)}</div><div class="track"><div class="fill" data-t="${esc(tipf?tipf(i):i.label+': '+i.count)}" style="width:${w}%;background:${c}"></div></div><div class="val">${fmt(i.count)}</div></div>`;}).join("");
 el.querySelectorAll(".fill").forEach(f=>{f.onmousemove=e=>showTip(e,f.dataset.t);f.onmouseleave=hideTip;});
 if(onClick)el.querySelectorAll(".bar").forEach(b=>b.onclick=()=>onClick(items[+b.dataset.x]));}

// stance stacked
const SCOL={oppose:"var(--magenta)",support:"var(--teal)",mixed:"var(--gold)",neutral_informational:"var(--baseline)"};
function stack(el,leg,items,total,cmap,onClick){
 el.innerHTML=items.map(i=>{const pct=i.count/total*100;return `<div class="seg" data-k="${i.key}" title="${esc(i.label)}: ${i.count}" style="width:${pct}%;background:${cmap[i.key]}">${pct>7?Math.round(pct)+'%':''}</div>`;}).join("");
 leg.innerHTML=items.map(i=>`<span><i style="background:${cmap[i.key]}"></i>${esc(i.label)} ${fmt(i.count)}</span>`).join("");
 if(onClick)el.querySelectorAll(".seg").forEach(s=>{s.style.cursor="pointer";s.onclick=()=>onClick(s.dataset.k);});}
stack($("#stanceStack"),$("#stanceLeg"),D.stance,M.total,SCOL,k=>applyFilter({stance:k}));

bars($("#specBars"),D.specialties.map(s=>({label:s.label,count:s.count})),{color:"var(--teal)",onClick:i=>applyFilter({spec:i.label})});
bars($("#typeBars"),D.submitter_types.map(t=>({label:t.type,count:t.count})),{color:"var(--green)",onClick:i=>applyFilter({list:{field:'type',value:i.label,label:i.label+' · submitter type',scalar:true}})});
bars($("#provBars"),D.provisions.map(p=>({label:p.label,count:p.count,key:p.key})),{color:"var(--magenta)",onClick:i=>applyFilter({list:{field:'provisions',value:i.key,label:i.label}})});
// campaigns: original vs organized template submissions
$("#origBig").textContent=fmt(M.original);$("#campBig").textContent=fmt(M.campaign_submissions);
$("#campSub").innerHTML="in <b>"+M.n_campaigns+"</b> organized template campaigns";
stack($("#campStack"),$("#campLeg"),[{key:"orig",label:"Original / individual comments",count:M.original},{key:"camp",label:"Organized template campaigns",count:M.campaign_submissions}],M.total,{orig:"var(--teal)",camp:"var(--magenta)"},k=>applyFilter({list:{field:"form",value:(k==="camp"),label:(k==="camp"?"Organized campaign submissions":"Original comments"),scalar:true}}));
$("#campList").innerHTML=(DATA.campaigns||[]).map((c,x)=>`<div class="camprow" data-x="${x}"><div class="txt">&ldquo;<b>${esc(c.sample)}</b>&rdquo;</div><div class="n">${c.wh_any?'<span class="whtag">women\'s health</span>':''}<span class="pill ${c.stance}">${c.stance==='neutral_informational'?'neutral':c.stance}</span><span class="cnt">${fmt(c.size)}</span> submissions</div></div>`).join("");
$("#campList").querySelectorAll(".camprow").forEach(el=>el.onclick=()=>{const c=DATA.campaigns[+el.dataset.x];applyFilter({list:{field:"cluster",value:c.id,label:"Template campaign · "+c.size+" submissions",scalar:true}});});

// tier
const T=W.tier,rel=T.core+T.stakes;
$("#tierBig").textContent=fmt(rel);
$("#tierSub").innerHTML="of "+fmt(M.total)+" comments touch women's health: <b>"+T.core+"</b> directly, <b>"+T.stakes+"</b> through hidden stakes. The rest ("+fmt(T.general)+") are general payment policy.";
const TCOL={core:"var(--teal)",stakes:"var(--gold)",general:"var(--other)"};
stack($("#tierStack"),$("#tierLeg"),[{key:"core",label:"Directly about women's health",count:T.core},{key:"stakes",label:"General, with women's-health stakes",count:T.stakes},{key:"general",label:"General policy",count:T.general}],M.total,TCOL,k=>applyFilter({tier:k}));

// push cards: where women's health needs more voices, computed from the data
const socOff=socAll.filter(w=>!w.filed);
const thinRfis=(DATA.rfi_map||[]).filter(r=>r.wh<=1);
$("#pushGrid").innerHTML=[
 {big:fmt(M25.wh)+" of "+fmt(M25.total),p:"comments on the <b>same-day cut</b> connect it to women's care."},
 {big:fmt(socOn.length)+" of "+fmt(socAll.length),p:"watched women's-health societies have <b>filed so far</b>. Most major letters land in the final week."},
 {big:thinRfis.length+" of 5 RFIs",p:"have almost <b>no women's-health comments</b> yet. RFIs shape what CMS takes up next."}
].map(c=>`<div class="pcard"><div class="big">${c.big}</div><div class="p">${c.p} <a href="https://medicarefeeschedule.51and.com/file" target="_blank" rel="noopener">Add your voice &rarr;</a></div></div>`).join("");

// G-code verdict
$("#gcodeVerdict").innerHTML=`
 <div class="clkv" data-g="adopt_cpt" style="cursor:pointer"><div class="vnum for">${fmt(gFor)}</div><div class="vlab">say adopt the new CPT maternity codes: a clean break</div></div>
 <div class="vs">vs</div>
 <div class="clkv" data-g="keep_gcodes" style="cursor:pointer"><div class="vnum against">${fmt(gKeep)}</div><div class="vlab">say keep the old bundle alive through G-codes</div></div>
 <div style="flex:1;min-width:230px"><div class="vlab" style="max-width:none;color:var(--muted)">${gMix?fmt(gMix)+" mixed (mostly: adopt the CPT codes, with a transition bridge)":""}${GC.counts.unclear?" &middot; "+fmt(GC.counts.unclear)+" unclear":""}</div></div>`;
document.querySelectorAll("#gcodeVerdict .clkv").forEach(el=>el.onclick=()=>applyFilter({list:{field:"gcode",value:el.dataset.g,label:(el.dataset.g==="adopt_cpt"?"For the new maternity codes":"For keeping the G-codes"),scalar:true}}));
const gtot=gFor+gKeep+gMix||1;
$("#gcodeMeter").innerHTML=[["adopt_cpt",gFor,"var(--teal)","adopt the new codes"],["mixed",gMix,"var(--gold)","mixed"],["keep_gcodes",gKeep,"var(--magenta)","keep the G-codes"]]
 .filter(s=>s[1]>0).map(s=>`<div class="seg" style="width:${(s[1]/gtot*100).toFixed(1)}%;background:${s[2]}" title="${s[3]}: ${s[1]}">${s[1]/gtot>.12?Math.round(s[1]/gtot*100)+"%":""}</div>`).join("");
$("#gcodeLeg").innerHTML=`<span><i style="background:var(--teal)"></i>Adopt the new CPT codes ${fmt(gFor)}</span><span><i style="background:var(--gold)"></i>Mixed ${fmt(gMix)}</span><span><i style="background:var(--magenta)"></i>Keep the G-codes ${fmt(gKeep)}</span>`;
$("#gcodeQuotes").innerHTML=(GC.samples||[]).filter(s=>s.note).slice(0,3).map(s=>`<div class="scard"><div class="q" style="margin-top:0">&ldquo;${esc(s.note)}&rdquo;</div><div class="meta"><span>${esc(s.org||s.spec)}</span><a href="${s.url}" target="_blank" rel="noopener">Read &rarr;</a></div></div>`).join("");

// who's-speaking-up board
const chip=w=>w.filed
 ?`<a class="borg on" href="${w.url}" target="_blank" rel="noopener" title="${esc(w.name)}: read their letter"><span class="dot"></span>${esc(w.short)}${w.via==="cosigner"?" <span style='font-weight:400;color:var(--muted)'>(co-signer)</span>":""} &#10003;</a>`
 :`<span class="borg" title="${esc(w.name)}: no letter found in the docket yet"><span class="dot"></span>${esc(w.short)}</span>`;
const comps=DATA.filed_companies||[];
const voices=(DATA.wh_voices||[]).filter(v=>v.wh>0);
const coal=(DATA.coalitions||[]).filter(c=>(c.co||[]).length>=3);
$("#watchPanel").innerHTML=
 `<div class="bhead">Women's-health societies &amp; advocacy · <span style="color:var(--teal)">${socOn.length} of ${socAll.length}</span> in the docket so far</div>`
 +`<div class="board">${WLIST.filter(w=>w.group==="wh_society").map(chip).join("")}</div>`
 +`<div class="bhead">Large health care associations</div>`
 +`<div class="board">${WLIST.filter(w=>w.group==="big_medicine").map(chip).join("")}</div>`
 +`<div class="bhead">Women's-health companies on the record</div>`
 +(comps.length?`<div class="board">${comps.map(chip).join("")}</div>`
   :`<div class="bnote">No women's-health company letters in the docket yet.</div>`)
 +(voices.length?`<div class="bhead">Organizational voices for women's health so far</div><div class="voices">${voices.slice(0,8).map(v=>`<div class="vrow"><span class="nm">${esc(v.name)}</span><span class="ty">${esc((v.type||"").replace(/_/g," "))}</span><a href="${v.url}" target="_blank" rel="noopener">${v.wh>1?v.wh+" letters":"Read"} &rarr;</a></div>`).join("")}</div>`:"")
 +(coal.length?`<div class="bhead">Coalition letters (multiple organizations, one filing)</div><div class="voices">${coal.slice(0,5).map(c=>`<div class="vrow"><span class="nm">${esc(c.org)}</span><span class="ty">+ ${c.co.length} co-signers</span><a href="${c.url}" target="_blank" rel="noopener">Read &rarr;</a></div>`).join("")}</div>`:"")
 +`<div class="bnote">&ldquo;Not yet&rdquo; means no letter found in this docket. Some groups engage CMS through other channels. Spot a letter we missed? <a href="mailto:jodi@inwomenshealth.com?subject=MPFS tracker: org letter">Tell us.</a></div>`;

// same-day (modifier 25) cut: who tells the story
$("#m25Lead").innerHTML=`<div><div class="vnum" style="color:var(--ink)">${fmt(M25.total)}</div><div class="vlab">comments fight the same-day cut, the biggest battle in the comments${M25.camp?` (${fmt(M25.camp)} from organized campaigns)`:""}</div></div><div class="vs">but only</div><div><div class="vnum against">${fmt(M25.wh)}</div><div class="vlab">connect it to women's health</div></div>`;
const m25items=(M25.by_spec||[]).filter(s=>s.label!=="Other/Unclear").slice(0,8).map(s=>({label:s.label,count:s.count,neutral:true}));
m25items.push({label:"Women's-health voices",count:M25.wh,neutral:false});
bars($("#m25Bars"),m25items,{color:i=>i.neutral?"var(--other)":"var(--teal)",onClick:i=>i.neutral?applyFilter({spec:i.label,list:{field:"provisions",value:"modifier_25",label:"Same-day cut · "+i.label}}):applyFilter({tier:"wh",list:{field:"provisions",value:"modifier_25",label:"Same-day cut · women's-health voices"}})});

// stakes cards
const STK=W.stakes;let stakesShown=4;
const scard=s=>`<div class="scard"><div class="note">${esc(s.note)}</div>${s.quote?`<div class="q">&ldquo;${esc(s.quote)}&rdquo;</div>`:""}<div class="meta"><span>${esc(s.specialty)}${s.provisions.length?' &middot; '+esc(s.provisions[0]):''}</span><a href="${s.url}" target="_blank" rel="noopener">Read &rarr;</a></div></div>`;
function renderStakes(){$("#stakesGrid").innerHTML=STK.slice(0,stakesShown).map(scard).join("");$("#stakesMore").style.display=STK.length>stakesShown?"block":"none";$("#stakesN").textContent=STK.length;}
renderStakes();$("#stakesMore").onclick=()=>{stakesShown=STK.length;renderStakes();};

bars($("#topicBars"),W.topics.map(t=>({label:t.label,count:t.count,key:t.key})),{color:"var(--teal)",onClick:i=>applyFilter({list:{field:'topics',value:i.key,label:i.label}})});
$("#kwrap").innerHTML=(DATA.keywords||[]).map((k,x)=>`<span class="kw" data-x="${x}">${esc(k.label)} <b>${k.count}</b></span>`).join("");
$("#kwrap").querySelectorAll(".kw").forEach(el=>el.onclick=()=>applyFilter({kw:DATA.keywords[+el.dataset.x].label}));

// RFI opportunity map v2: expandable cards with what CMS asked + the asks on record
const RM=DATA.rfi_map||[];
const rmx=Math.max(...RM.map(r=>r.total),1);
$("#rfiWrap").innerHTML=RM.map((r,x)=>{
 const tw=Math.max(r.total/rmx*100,1.5).toFixed(1),ww=(r.wh/rmx*100).toFixed(1);
 const hot=r.wh<=1;
 const themes=(r.themes||[]).filter(t=>t.t!=="Other asks").slice(0,5);
 const asks=(r.asks||[]).slice(0,4);
 return `<details class="rficard ${hot?'':''}" data-x="${x}"><summary><div class="rline">
   <div class="lab" style="text-align:left"><span class="pl" style="display:block;font-size:14px;color:${hot?'var(--magenta)':'var(--ink)'};font-weight:600">${esc(r.label)}</span><span class="sub" style="display:block;font-size:10.5px;color:var(--muted)">${esc(r.tech)}</span></div>
   <div class="rtrackwrap"><div class="rfitrack"><div class="tot" style="width:${tw}%"></div><div class="whb" style="width:${ww}%"></div></div></div>
   <div class="rval"><b>${r.wh}</b> WH / ${r.total}</div><span class="digbtn"><span>Dig in deeper</span> <span class="caret">&#9656;</span></span></div></summary>
  <div class="body">
   <div class="asked">${esc(r.asked)}</div>
   ${(r.decoder||[]).length?`<div class="decoder">${r.decoder.map(d=>`<div class="dt"><b>${esc(d.t)}</b>: ${esc(d.d)}.</div>`).join("")}</div>`:""}
   <div class="whywh"><b style="color:var(--teal)">Why it matters for women's health:</b> ${esc(r.why_wh)}</div>
   ${(r.consider||[]).length?`<div class="bhead">For women's health to consider</div><ul class="consider">${r.consider.map(c=>`<li>${esc(c)}</li>`).join("")}</ul>`:""}
   <div class="bhead">${fmt(r.total)} comments · ${fmt(r.total-(r.form||0))} original · ${fmt(r.form||0)} from template campaigns${r.wh?` &middot; <span style="color:var(--teal)">${fmt(r.wh)} women's-health</span> (${fmt(r.wh-(r.wh_form||0))} original)`:""}</div>
   ${r.questions?r.questions.map(qq=>`<div class="asked" style="margin-top:12px">${esc(qq.label)} <span style="color:var(--muted);font-weight:400">&middot; ${qq.n} answer${qq.n===1?"":"s"}${qq.wh?` &middot; <span style='color:var(--teal)'>${qq.wh} women's-health</span>`:""}</span></div>
     <ul class="asklist" style="margin-top:2px">${qq.samples.map(s=>`<li>&ldquo;${esc(s.text)}&rdquo;${s.wh?'<span class="wtag">women\'s health</span>':''} &nbsp;<a href="${s.url}" target="_blank" rel="noopener">Read &rarr;</a></li>`).join("")}</ul>`).join(""):""}
   ${r.spillover?`<div class="bnote" style="margin-top:12px">${fmt(r.spillover)} more comments were filed near this RFI but address specific rule provisions (the same-day cut, the maternity codes, individual code values). They're counted in those sections instead.</div>`:""}
   ${!r.questions&&themes.length?`<div class="rfth">${themes.map(t=>`<span class="chip">${esc(t.t)} <b>${t.n}</b></span>`).join("")}</div>`:""}
   ${!r.questions&&asks.length?`<div class="bhead">From the record</div><ul class="asklist">${asks.map(a=>`<li>&ldquo;${esc(a.ask)}&rdquo;${a.wh?'<span class="wtag">women\'s health</span>':''} &nbsp;<a href="${a.url}" target="_blank" rel="noopener">Read &rarr;</a></li>`).join("")}</ul>`:""}
   ${hot?`<div class="bnote" style="border-left:3px solid var(--magenta);padding-left:10px">Almost no women's-health comments on this question yet.</div>`:""}
   <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:14px">
    <button class="activef rfiall" data-x="${x}">Read ${r.questions?"the "+fmt(r.total)+" answers":"all "+fmt(r.total)+" comments"} &rarr;</button>
    <a class="btn btn-pink" style="padding:8px 18px;font-size:13px" href="https://medicarefeeschedule.51and.com/file" target="_blank" rel="noopener">Answer this RFI &rarr;</a>
   </div></div></details>`;}).join("")
 +`<div class="stackleg" style="margin-top:14px"><span><i style="background:var(--teal)"></i>Women's-health&ndash;relevant</span><span><i style="background:var(--other)"></i>All comments on that RFI</span> &middot; <span style="color:var(--muted)">bar lengths are comparable across the five questions</span></div>`;
document.querySelectorAll("#rfiWrap .rfiall").forEach(b=>b.onclick=e=>{e.preventDefault();const r=RM[+b.dataset.x];
 applyFilter({list:r.questions?{field:'cptq',value:true,label:r.label+" · RFI answers",scalar:true}:{field:'rfi',value:r.key,label:r.label}});});

bars($("#frameBars"),DATA.framings.map(f=>({label:f.label,count:f.count,key:f.key})),{color:"var(--teal)",onClick:i=>applyFilter({list:{field:'framings',value:i.key,label:i.label}})});

function renderTimeline(){const A=D.timeline;if(!A.length){return;}const W2=1040,H=220,pad={l:38,r:12,t:14,b:26};
 const iw=W2-pad.l-pad.r,ih=H-pad.t-pad.b,mx=Math.max(...A.map(d=>d.count));
 const x=i=>pad.l+(A.length<2?iw/2:i/(A.length-1)*iw),y=v=>pad.t+ih-v/mx*ih;
 const cs=getComputedStyle(document.documentElement),s1=cs.getPropertyValue("--teal").trim(),g=cs.getPropertyValue("--grid").trim(),mu=cs.getPropertyValue("--muted").trim(),bl=cs.getPropertyValue("--baseline").trim();
 let ln=A.map((d,i)=>(i?"L":"M")+x(i).toFixed(1)+" "+y(d.count).toFixed(1)).join(" ");
 let ar=ln+` L${x(A.length-1).toFixed(1)} ${pad.t+ih} L${pad.l} ${pad.t+ih} Z`;
 let gl=[0,Math.round(mx/2),mx].map(t=>`<line x1="${pad.l}" x2="${W2-pad.r}" y1="${y(t)}" y2="${y(t)}" stroke="${g}"/><text x="${pad.l-6}" y="${y(t)+3}" text-anchor="end" fill="${mu}" font-size="10">${t}</text>`).join("");
 const st=Math.ceil(A.length/6);let xl=A.map((d,i)=>i%st===0?`<text x="${x(i)}" y="${H-8}" text-anchor="middle" fill="${mu}" font-size="10">${d.date.slice(5)}</text>`:"").join("");
 $("#timeline").innerHTML=`<svg viewBox="0 0 ${W2} ${H}"><defs><linearGradient id="ag" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${s1}" stop-opacity=".26"/><stop offset="1" stop-color="${s1}" stop-opacity="0"/></linearGradient></defs>${gl}<path d="${ar}" fill="url(#ag)"/><path d="${ln}" fill="none" stroke="${s1}" stroke-width="2.5" stroke-linejoin="round"/><line x1="${pad.l}" x2="${W2-pad.r}" y1="${pad.t+ih}" y2="${pad.t+ih}" stroke="${bl}"/>${xl}${A.map((d,i)=>`<circle cx="${x(i)}" cy="${y(d.count)}" r="9" fill="transparent" data-t="${esc(d.date+': '+d.count+' comments')}"></circle>`).join("")}</svg>`;
 $("#timeline").querySelectorAll("circle").forEach(c=>{c.onmousemove=e=>showTip(e,c.dataset.t);c.onmouseleave=hideTip;});}
renderTimeline();addEventListener("resize",()=>{clearTimeout(window._r);window._r=setTimeout(renderTimeline,150);});

// browser
const rows=DATA.rows.slice().sort((a,b)=>b.posted.localeCompare(a.posted));
const fSpec=$("#fSpec"),fTheme=$("#fTheme"),fKw=$("#fKw");
[...new Set(rows.map(r=>r.specialty))].sort().forEach(s=>fSpec.add(new Option(s,s)));
DATA.themes.filter(t=>t.count>0).forEach(t=>fTheme.add(new Option((t.plain||t.label)+" ("+t.count+")",t.label)));
(DATA.keywords||[]).forEach(k=>fKw.add(new Option(k.label+" ("+k.count+")",k.label)));
let shown=40,sortK="posted",sortDir=-1,whOnly=false,listFilter=null;
function passes(r){if(whOnly&&!(r.tier==='core'||r.tier==='stakes'))return false;
 if(listFilter){if(listFilter.scalar){if(r[listFilter.field]!==listFilter.value)return false;}else if(!(r[listFilter.field]||[]).includes(listFilter.value))return false;}
 const q=$("#q").value.trim().toLowerCase();
 if(q&&!((r.title+" "+r.org+" "+r.summary+" "+r.snippet).toLowerCase().includes(q)))return false;
 if(fSpec.value&&r.specialty!==fSpec.value)return false;
 if($("#fStance").value&&r.stance!==$("#fStance").value)return false;
 const tv=$("#fTier").value;if(tv==="core"&&r.tier!=="core")return false;if(tv==="stakes"&&r.tier!=="stakes")return false;if(tv==="general"&&r.tier!=="general")return false;
 const fv=$("#fForm").value;if(fv==="orig"&&r.form)return false;if(fv==="camp"&&!r.form)return false;
 if(fTheme.value&&!r.themes.includes(fTheme.value))return false;
 if(fKw.value&&!(r.kw||[]).includes(fKw.value))return false;return true;}
function render(){let f=rows.filter(passes);f.sort((a,b)=>{let av=a[sortK]||"",bv=b[sortK]||"";return(av<bv?-1:av>bv?1:0)*sortDir;});
 $("#rowCount").textContent=fmt(f.length)+" of "+fmt(rows.length)+" comments";
 $("#activeFilter").innerHTML=listFilter?'<span class="activef">&#9656; '+esc(listFilter.label)+' &#10005;</span>':"";
 if(listFilter&&$("#activeFilter").firstChild)$("#activeFilter").firstChild.onclick=()=>applyFilter({});
 $("#tbody").innerHTML=f.slice(0,shown).map(r=>`<tr><td class="date">${r.posted||"&ndash;"}</td>
  <td><a href="${r.url}" target="_blank" rel="noopener">${esc(r.title||"(untitled comment)")}</a>${r.org?`<div class="tt-org">${esc(r.org)}</div>`:""}${r.summary?`<div class="summ">${esc(r.summary)}</div>`:""}
   <div class="chips">${r.tier==='core'?'<span class="chip core">women\'s health</span>':r.tier==='stakes'?'<span class="chip stakes">WH stakes</span>':''}${r.has_attach?'<span class="chip att">attachment read</span>':''}${r.themes.slice(0,3).map(t=>`<span class="chip" title="${esc(t)}">${esc(PLAIN[t]||t)}</span>`).join("")}</div></td>
  <td class="tt-org">${esc(r.specialty)}</td><td><span class="pill ${r.stance}">${r.stance==='neutral_informational'?'neutral':r.stance}</span></td></tr>`).join("")||`<tr><td colspan="4" style="color:var(--muted);padding:26px;text-align:center">No comments match these filters.</td></tr>`;
 $("#moreBtn").style.display=f.length>shown?"block":"none";}
function applyFilter(f){f=f||{};whOnly=(f.tier==="wh");listFilter=f.list||null;$("#q").value=f.q||"";fSpec.value=f.spec||"";$("#fStance").value=f.stance||"";
 $("#fTier").value=(f.tier&&f.tier!=="wh")?f.tier:"";fTheme.value=f.theme||"";fKw.value=f.kw||"";$("#fForm").value="";
 shown=40;render();$("#browser").scrollIntoView({behavior:"smooth",block:"start"});}
["#q","#fSpec","#fStance","#fTier","#fForm","#fTheme","#fKw"].forEach(s=>$(s).addEventListener("input",()=>{whOnly=false;listFilter=null;shown=40;render();}));
$("#clearBtn").onclick=()=>applyFilter({});
$("#moreBtn").onclick=()=>{shown+=100;render();};
document.querySelectorAll("th[data-k]").forEach(th=>th.onclick=()=>{const k=th.dataset.k;sortDir=(sortK===k)?-sortDir:(k==="posted"?-1:1);sortK=k;render();});
render();
$("#sgBtn").onclick=()=>{const t=$("#sgTopic").value.trim();if(!t){$("#sgMsg").textContent="Please enter a topic first.";return;}
 const body="Suggested topic to track: "+t+"\n\nWhy it matters: "+($("#sgWhy").value.trim()||"(none given)")+"\n\nFrom: "+($("#sgEmail").value.trim()||"(anonymous)")+"\n\n- Submitted from the CY2027 MPFS Comment Tracker";
 window.location.href="mailto:jodi@inwomenshealth.com?subject="+encodeURIComponent("MPFS tracker: topic suggestion: "+t)+"&body="+encodeURIComponent(body);
 $("#sgMsg").innerHTML="Thanks! Your email app should open with the suggestion ready to send to 51&amp;.";$("#sgTopic").value="";$("#sgWhy").value="";$("#sgEmail").value="";};
$("#foot").innerHTML="Generated __GEN__ &middot; classification by 51&amp;'s watch-list taxonomy + LLM tagging on full comment text (inline + attachments) &middot; "+fmt(rows.length)+" comments &middot; source: <a href='https://www.regulations.gov/docket/CMS-2026-2377' target='_blank' rel='noopener'>Regulations.gov docket "+M.docket+"</a>";
</script></body></html>"""
out=(HTML.replace("/*__DATA__*/",json.dumps(DATA,separators=(",",":"))).replace("__FONT_REG__",FONT_REG).replace("__FONT_SEMI__",FONT_SEMI).replace("__GEN__",GEN))
open(os.path.join(BASE,"dashboard.html"),"w").write(out)
print(f"dashboard.html written ({os.path.getsize(os.path.join(BASE,'dashboard.html'))//1024} KB)")
