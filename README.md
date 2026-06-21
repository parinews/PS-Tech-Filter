
### What it does
- Fetches all ~322 holdings from the Vanguard Information Technology ETF (VGT) daily via Vanguard's official portfolio API
- Filters to SaaS companies only (Yahoo Finance industry = "Software - Application" or "Software - Infrastructure")
- Further filters to stocks with a trailing-twelve-month Price/Sales (P/S) ratio between 2.0x and 4.0x
- Emails the resulting list sorted ascending by P/S ratio at 9:00 AM IST every day

### Why this range
P/S of 2–4x for SaaS is a historically low valuation zone — these are established software businesses trading at prices that may represent value relative to their revenue.

### How it works (architecture)
| Layer | Tool | Cost |
|---|---|---|
| Scheduler | GitHub Actions cron (`30 3 * * *` = 9 AM IST) | Free |
| VGT holdings | Vanguard portfolio API | Free |
| P/S + industry data | yfinance | Free |
| Email delivery | Gmail SMTP + App Password | Free |

### Files
- `ps_screener.py` — main script
- `ps_screener_requirements.txt` — dependencies (`yfinance`, `requests`)
- `.github/workflows/ps_screener.yml` — GitHub Actions workflow

### One-time setup
1. Generate a Gmail App Password: Google Account → Security → 2-Step Verification → App Passwords
2. In GitHub repo Settings → Secrets → Actions, add:
   - `GMAIL_USER` — your Gmail address
   - `GMAIL_APP_PASSWORD` — the 16-character app password
3. The workflow runs automatically. To test manually: Actions → Daily P/S Screener Email → Run workflow

### Adjusting the filter
Edit `ps_screener.py`:
- Change the P/S range: line `if 2.0 <= ps <= 4.0`
- Change the industry filter: `SAAS_INDUSTRIES` set at the top
- Holdings source: `fetch_vgt_tickers()` calls the Vanguard API
