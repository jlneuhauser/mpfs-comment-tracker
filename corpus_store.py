#!/usr/bin/env python3
"""Keep corpus.db out of git (it passed GitHub's 100MB file limit on 8/31 and
every push was silently rejected). Instead it lives gzipped as an asset on a
rolling GitHub Release tagged `corpus-latest`.

  fetch: if corpus.db is missing, download + gunzip it from the release.
  store: gzip corpus.db and replace the release asset.

Token (store only): $CORPUS_GH_TOKEN or $GITHUB_TOKEN, else the token
actions/checkout persisted into git config (the extraheader). Downloads need
no token (public repo)."""
import gzip, json, os, shutil, subprocess, sys, time, urllib.request, urllib.error

REPO = "jlneuhauser/mpfs-comment-tracker"
TAG = "corpus-latest"
ASSET = "corpus.db.gz"
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "corpus.db")
GZ = DB + ".gz"

# never route through a session proxy; GitHub is directly reachable in CI
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def token():
    t = os.environ.get("CORPUS_GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    try:  # actions/checkout persists "AUTHORIZATION: basic base64(x-access-token:TOKEN)"
        import base64
        hdr = subprocess.run(["git", "config", "--get", "http.https://github.com/.extraheader"],
                             capture_output=True, text=True, cwd=BASE).stdout.strip()
        b64 = hdr.split()[-1]
        return base64.b64decode(b64).decode().split(":", 1)[1]
    except Exception:
        return None


def api(url, tok, method="GET", data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", **({"Content-Type": ctype} if data else {})})
    with OPENER.open(req, timeout=300) as r:
        body = r.read()
    return json.loads(body) if body else {}


def fetch():
    if os.path.exists(DB):
        print(f"corpus.db present ({os.path.getsize(DB)/1e6:.0f} MB) — using it, not downloading")
        return
    url = f"https://github.com/{REPO}/releases/download/{TAG}/{ASSET}"
    print(f"downloading {url} ...")
    try:
        with OPENER.open(url, timeout=600) as r, open(GZ, "wb") as f:
            shutil.copyfileobj(r, f)
    except urllib.error.HTTPError as e:
        print(f"FATAL: no local corpus.db and release download failed (HTTP {e.code}). "
              "Refusing to start from an empty corpus — that would re-ingest the whole docket.")
        sys.exit(1)
    with gzip.open(GZ, "rb") as f, open(DB, "wb") as out:
        shutil.copyfileobj(f, out)
    os.remove(GZ)
    print(f"corpus.db restored ({os.path.getsize(DB)/1e6:.0f} MB)")


def store():
    tok = token()
    if not tok:
        print("!! no GitHub token available — corpus NOT uploaded"); sys.exit(1)
    print(f"gzipping corpus.db ({os.path.getsize(DB)/1e6:.0f} MB) ...")
    with open(DB, "rb") as f, gzip.open(GZ, "wb", compresslevel=6) as out:
        shutil.copyfileobj(f, out)
    size = os.path.getsize(GZ)
    print(f"  -> {size/1e6:.0f} MB compressed")
    try:
        rel = api(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}", tok)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        rel = api(f"https://api.github.com/repos/{REPO}/releases", tok, "POST", json.dumps({
            "tag_name": TAG, "name": "Corpus snapshot (rolling)", "make_latest": "false",
            "body": "Rolling snapshot of corpus.db (gzipped). Replaced by every pipeline run. "
                    "Too large for a git tree (GitHub hard-caps files at 100MB)."}).encode())
    for a in rel.get("assets", []):
        if a["name"] == ASSET:
            api(f"https://api.github.com/repos/{REPO}/releases/assets/{a['id']}", tok, "DELETE")
    up = f"https://uploads.github.com/repos/{REPO}/releases/{rel['id']}/assets?name={ASSET}"
    with open(GZ, "rb") as f:
        data = f.read()
    for attempt in range(3):
        try:
            api(up, tok, "POST", data, "application/gzip")
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  upload retry after {type(e).__name__}: {e}"); time.sleep(10)
    os.remove(GZ)
    print("corpus uploaded to release", TAG)


if __name__ == "__main__":
    {"fetch": fetch, "store": store}[sys.argv[1]]()
