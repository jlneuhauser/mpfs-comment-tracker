#!/usr/bin/env python3
"""Near-duplicate / template-campaign detection for the MPFS comment corpus.

Public dockets attract organized "form-letter" campaigns: many people submit the
same template, sometimes with one sentence changed. This pass groups comments whose
inline text is near-identical, so the dashboard can separate ORIGINAL comments from
ORGANIZED (template) campaigns — applied evenly to every campaign, described neutrally.

Pure standard library. Deterministic (stable hashing), so re-runs are reproducible.
Writes per-comment: dup_cluster (int, -1 if none), dup_cluster_size, is_form_letter.
"""
import sqlite3, re, os, sys, hashlib
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, os.environ.get("DEDUPE_DB", "corpus.db"))

MIN_WORDS   = 25     # shorter comments aren't eligible as "templates" (too little signal)
SHINGLE_N   = 5      # word n-gram size
NUM_HASHES  = 100    # MinHash permutations
BANDS       = 25     # LSH bands (rows per band = NUM_HASHES/BANDS = 4)
JACCARD_MIN = 0.55   # estimated Jaccard to accept a near-duplicate pair
CLUSTER_MIN = 3      # >=3 near-identical submissions = a shared template
CAMPAIGN_MIN= 5      # >=5 = flagged as an organized campaign (is_form_letter)

# boilerplate that is NOT a template campaign (people just uploaded a letter)
BOILER = re.compile(r"^(see|please see|comments? )?\s*(the )?attached( file| document| letter| comment)?s?\.?$", re.I)

_PRIME = (1 << 61) - 1
def _mk_hashes(k):
    # deterministic (a,b) coefficients from a fixed seed
    rng = []
    seed = 0x9E3779B97F4A7C15
    x = seed
    for _ in range(k):
        x = (x * 6364136223846793005 + 1442695040888963407) & ((1<<64)-1)
        a = (x | 1) % _PRIME
        x = (x * 6364136223846793005 + 1442695040888963407) & ((1<<64)-1)
        b = x % _PRIME
        rng.append((a, b))
    return rng
HASHES = _mk_hashes(NUM_HASHES)

def norm(t):
    t = (t or "").lower().replace("’","'")
    t = re.sub(r"http\S+"," ",t)
    t = re.sub(r"[^a-z0-9 ]+"," ",t)
    return re.sub(r"\s+"," ",t).strip()

def shingles(words):
    if len(words) < SHINGLE_N:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i+SHINGLE_N]) for i in range(len(words)-SHINGLE_N+1)}

def base_hash(s):
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "big") % _PRIME

def minhash(shs):
    sig = [ _PRIME+1 ] * NUM_HASHES
    for s in shs:
        h = base_hash(s)
        for i,(a,b) in enumerate(HASHES):
            v = (a*h + b) % _PRIME
            if v < sig[i]: sig[i] = v
    return sig

class UF:
    def __init__(s): s.p={}
    def find(s,x):
        s.p.setdefault(x,x)
        while s.p[x]!=x:
            s.p[x]=s.p[s.p[x]]; x=s.p[x]
        return x
    def union(s,a,b):
        ra,rb=s.find(a),s.find(b)
        if ra!=rb: s.p[ra]=rb

def est_jaccard(s1,s2):
    return sum(1 for a,b in zip(s1,s2) if a==b)/len(s1)

def main():
    db=sqlite3.connect(DB); db.row_factory=sqlite3.Row
    cols=[r[1] for r in db.execute("PRAGMA table_info(comments)")]
    for col,typ in [("dup_cluster","INTEGER"),("dup_cluster_size","INTEGER"),("is_form_letter","INTEGER")]:
        if col not in cols:
            db.execute(f"ALTER TABLE comments ADD COLUMN {col} {typ}")
    db.commit()

    rows=db.execute("select id, comment_text from comments").fetchall()
    sigs={}; eligible=[]
    for r in rows:
        n=norm(r["comment_text"])
        w=n.split()
        if len(w) < MIN_WORDS or BOILER.match(n):
            continue
        eligible.append(r["id"])
        sigs[r["id"]]=minhash(shingles(w))
    print(f"{len(rows)} comments; {len(eligible)} eligible for template matching (>= {MIN_WORDS} words)", flush=True)

    # LSH banding -> candidate buckets
    rows_per_band = NUM_HASHES // BANDS
    uf=UF()
    for cid in eligible: uf.find(cid)
    cand_checked=0; pairs=0
    for band in range(BANDS):
        buckets=defaultdict(list)
        lo=band*rows_per_band; hi=lo+rows_per_band
        for cid in eligible:
            key=tuple(sigs[cid][lo:hi])
            buckets[key].append(cid)
        for key,members in buckets.items():
            if len(members)<2: continue
            # verify within bucket, union near-dups
            for i in range(len(members)):
                for j in range(i+1,len(members)):
                    a,b=members[i],members[j]
                    if uf.find(a)==uf.find(b): continue
                    cand_checked+=1
                    if est_jaccard(sigs[a],sigs[b])>=JACCARD_MIN:
                        uf.union(a,b); pairs+=1

    # assemble clusters
    comp=defaultdict(list)
    for cid in eligible: comp[uf.find(cid)].append(cid)
    clusters=[m for m in comp.values() if len(m)>=CLUSTER_MIN]
    clusters.sort(key=len, reverse=True)

    # write back
    db.execute("update comments set dup_cluster=-1, dup_cluster_size=1, is_form_letter=0")
    cid_map={}
    for idx,members in enumerate(clusters,1):
        size=len(members); form=1 if size>=CAMPAIGN_MIN else 0
        for m in members:
            db.execute("update comments set dup_cluster=?, dup_cluster_size=?, is_form_letter=? where id=?",
                       (idx,size,form,m))
    db.commit()

    in_clusters=sum(len(m) for m in clusters)
    campaigns=[m for m in clusters if len(m)>=CAMPAIGN_MIN]
    in_campaigns=sum(len(m) for m in campaigns)
    print(f"clusters(>= {CLUSTER_MIN}): {len(clusters)} covering {in_clusters} comments", flush=True)
    print(f"campaigns(>= {CAMPAIGN_MIN}): {len(campaigns)} covering {in_campaigns} comments ({in_campaigns*100//len(rows)}% of docket)", flush=True)
    # show top clusters with a sample line + dominant org
    for idx,members in enumerate(clusters[:12],1):
        ex=db.execute("select organization, substr(comment_text,1,110) t from comments where id=? ",(members[0],)).fetchone()
        orgs=defaultdict(int)
        for m in members:
            o=db.execute("select organization from comments where id=?",(m,)).fetchone()[0]
            orgs[(o or "").strip() or "(no org)"]+=1
        dom=max(orgs.items(), key=lambda x:x[1])
        samp=re.sub(r"\s+"," ",(ex["t"] or "")).strip()
        print(f"  #{idx} n={len(members)} dom_org={dom[0][:30]!r}({dom[1]}) :: {samp[:80]!r}", flush=True)

if __name__=="__main__":
    main()
