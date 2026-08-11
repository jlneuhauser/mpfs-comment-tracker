# MPFS CY2027 Comment Tracker — automated daily runner

This repository keeps the comment tracker up to date on its own. Once a day it pulls any new
comments on docket **CMS-2026-2377**, downloads and reads their attached letters, classifies and
tags them, refreshes the public dashboard, and mirrors everything into your Supabase database.

It's already loaded with the full tagged corpus (`corpus.db`), so day one it's complete; each run
only processes what's new. The comment period closes **September 14, 2026**, after which it simply
stops finding new comments.

## What you need (one-time, ~20 minutes)

You'll add four **secrets** and (optionally) one **variable** to the repository, then turn on Pages.

### 1. Create the repo and upload these files
Create a new GitHub repository (private is fine) and upload everything in this folder, keeping the
structure — especially `.github/workflows/daily.yml`.

### 2. Gather the four secrets
| Secret name | What it is / where to get it |
|---|---|
| `REGS_API_KEY` | Your Regulations.gov key (from api.data.gov). |
| `ANTHROPIC_API_KEY` | From **console.anthropic.com → Billing** (add a little credit) **→ API Keys → Create Key**. Starts with `sk-ant-…`. Usage-based, ~pennies/day here. |
| `SUPABASE_URL` | `https://xmmvllscvuufwskhcdlj.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase → your **mpfs-comment-tracker** project → **Project Settings → API → `service_role` secret key** (NOT the anon key). This can write to the database, so keep it only in this GitHub secret. |

### 3. Add them to GitHub
Repo **Settings → Secrets and variables → Actions → New repository secret**, and add all four above.
Optionally add a repository **variable** named `MODEL` set to a current Anthropic model id (see
docs.anthropic.com/en/docs/about-claude/models); if you skip it, the runner uses a sensible default.

### 4. Turn on GitHub Pages
Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.

### 5. Run it once
Go to the **Actions** tab → **MPFS daily tracker** → **Run workflow**. After it finishes (a few
minutes), your public dashboard is live at:

```
https://<your-username>.github.io/<your-repo>/
```

That URL is what you share with the coalition. From then on it updates itself every morning, and
your Supabase database stays in sync so you can keep querying it.

## Costs
- GitHub Actions + Pages: free for this.
- Anthropic API: only new comments get tagged — a few cents a day.
- Supabase: already covered by your Pro plan.

## What runs each day (`run_pipeline.sh`)
1. `mpfs_ingest.py --mode daily` — fetch new/updated comments
2. `pdf_ingest.py` — download + extract new attachment PDFs (OCR fallback)
3. `reclassify.py` — keyword watch-list tagging
4. `tag_llm.py` — LLM tagging of the new comments (specialty, stance, women's-health tier, framings)
5. `export_data.py` + `build_dashboard.py` — rebuild the page
6. `supabase_sync.py` — upsert everything into Postgres
7. publish `public/index.html` to GitHub Pages

## Notes
- If a run fails on the model id, set the `MODEL` repository variable to a current Haiku model.
- To change the schedule, edit the `cron` line in `.github/workflows/daily.yml`.
- The dashboard styling/logic lives in `build_dashboard.py`; the watch-list in `taxonomy.json`;
  the tag definitions in `tag_schema.md`.
