#!/usr/bin/env python3
"""Download comment attachment PDFs, extract text (OCR fallback for scanned),
store in attachments.extracted_text. Regulations.gov's CloudFront blocks the
default agent, so we send a browser UA. Idempotent: skips rows already extracted."""
import sqlite3, subprocess, os, time, tempfile, glob, argparse

BASE = os.path.dirname(os.path.abspath(__file__))
PDFDIR = os.path.join(BASE, "pdfs"); os.makedirs(PDFDIR, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

def download(url, dest):
    r = subprocess.run(["curl", "-sSL", "-m", "60", "-A", UA, "-o", dest, url,
                        "-w", "%{http_code}"], capture_output=True, text=True)
    return r.stdout.strip()

def extract_text(pdf):
    # 1) direct text layer
    try:
        txt = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                             capture_output=True, text=True, timeout=120).stdout
    except Exception:
        txt = ""
    if len((txt or "").strip()) >= 200:
        return txt.strip(), "text"
    # 2) OCR fallback (scanned) — render pages to images, tesseract each
    try:
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["pdftoppm", "-r", "200", "-png", pdf, os.path.join(td, "p")],
                           timeout=300, capture_output=True)
            out = []
            for img in sorted(glob.glob(os.path.join(td, "p*.png")))[:30]:
                out.append(subprocess.run(["tesseract", img, "-", "--psm", "6"],
                           capture_output=True, text=True, timeout=120).stdout)
            ocr = "\n".join(out).strip()
            if len(ocr) >= 100:
                return ocr, "ocr"
    except Exception:
        pass
    return (txt or "").strip(), "text_thin"

def main(max_minutes=None):
    deadline = (time.monotonic() + max_minutes * 60) if max_minutes is not None else None
    db = sqlite3.connect(os.path.join(BASE, "corpus.db")); db.row_factory = sqlite3.Row
    rows = db.execute("SELECT rowid,* FROM attachments WHERE file_format='pdf'").fetchall()
    done = skipped = ocr_n = fail = 0
    stats = {}
    for r in rows:
        if r["extracted_text"] and len(r["extracted_text"]) > 50:
            skipped += 1; continue
        if deadline and time.monotonic() > deadline:
            print(f"  time budget ({max_minutes} min) reached — stopping; remaining PDFs "
                  f"extract on the next run (idempotent)", flush=True)
            break
        dest = os.path.join(PDFDIR, f"{r['comment_id']}_{r['id']}.pdf")
        if not (os.path.exists(dest) and os.path.getsize(dest) > 1000):
            code = download(r["source_url"], dest)
            time.sleep(0.3)
            if code != "200" or not os.path.exists(dest) or os.path.getsize(dest) < 200:
                fail += 1; continue
        text, method = extract_text(dest)
        if not text:
            fail += 1; continue
        stats[method] = stats.get(method, 0) + 1
        if method == "ocr": ocr_n += 1
        db.execute("UPDATE attachments SET extracted_text=? WHERE rowid=?",
                   (text[:60000], r["rowid"]))
        done += 1
        if done % 20 == 0:
            db.commit(); print(f"  ...{done} extracted")
    db.commit()
    tot_chars = db.execute("SELECT sum(length(extracted_text)) FROM attachments").fetchone()[0] or 0
    print(f"extracted={done} skipped(existing)={skipped} ocr={ocr_n} failed={fail}")
    print(f"methods: {stats}")
    print(f"comments now with attachment text: "
          f"{db.execute('SELECT count(distinct comment_id) FROM attachments WHERE length(extracted_text)>50').fetchone()[0]}")
    print(f"total attachment chars stored: {tot_chars:,}")
    db.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutes", type=float, default=None,
                    help="stop after this many minutes; remaining PDFs carry to the next run")
    main(ap.parse_args().max_minutes)
