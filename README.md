# Alexandria Daily Report

Auto-generates a daily HTML stats page from Sigma every night and hosts it on GitHub Pages.

## Setup (one time, ~10 minutes)

### 1. Create a GitHub repo
- Go to github.com → New repository
- Name it anything (e.g. `alexandria-report`)
- Set it to **Private**
- Upload all files from this folder

### 2. Enable GitHub Pages
- Go to your repo → Settings → Pages
- Under "Source" select **GitHub Actions** (not a branch)
- Save

### 3. Add your Sigma credentials as Secrets
- Go to Settings → Secrets and variables → Actions → New repository secret
- Add these two:
  - `SIGMA_CLIENT_ID` — from Sigma → Administration → Developer Access
  - `SIGMA_CLIENT_SECRET` — same place

### 4. You're done
- GitHub Actions runs every night at 9 PM MT
- Your report is live at: `https://YOUR-GITHUB-USERNAME.github.io/alexandria-report/`
- Bookmark that URL on your iPhone — it updates automatically every night

## Manual trigger
Go to your repo → Actions → Daily Report → Run workflow
to generate it on demand for any day.

## Change the send time
Edit `.github/workflows/daily.yml` and change the cron line.
Cron is in UTC — MT is UTC-6 (UTC-7 in summer).
  9 PM MT  = 3 AM UTC  → `0 3 * * *`
  10 PM MT = 4 AM UTC  → `0 4 * * *`
  8 PM MT  = 2 AM UTC  → `0 2 * * *`
