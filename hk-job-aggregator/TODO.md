# HK Job Aggregator — To-Do

_Last updated: 2026-05-16_

---

## Priority 1 — Bugs (quick fixes, do these first)

### ~~1.1 Remove `--no-descriptions` from GitHub Actions~~ ✓ DONE
**Why:** The workflow currently scrapes jobs without fetching descriptions, so the AI scores jobs on title only. One-line fix.
**File:** `.github/workflows/daily-scrape.yml`
**Change:** In the "Scrape jobs" step, change:
```
python scrape_all.py --no-descriptions
```
to:
```
python scrape_all.py
```

---

### ~~1.2 Rewrite `schema.sql` in PostgreSQL syntax~~ ✓ DONE
**Why:** `models/schema.sql` still has SQLite syntax (`AUTOINCREMENT`, `BLOB`, `INSERT OR IGNORE`). The live Supabase DB works fine but can't be recreated from this file. If Supabase is ever reset or the project is handed to someone else, there's no source of truth.
**File:** `models/schema.sql`
**Change:** Rewrite to match the actual live schema — use `SERIAL`, `BYTEA`, `INSERT ... ON CONFLICT DO NOTHING`, `TIMESTAMPTZ`, etc.

---

## Priority 2 — Coverage gaps (more/better jobs)

### ~~2.1 Find companies that use Lever and add them~~ ✓ DONE
**Why:** The Lever scraper is built and ready but `LEVER_TOKENS = {}` in `scrape_all.py` — nothing runs through it. Citadel (the original reason it was added) has a private board.
**File:** `scrape_all.py`
**Action:**
- For each company below, check `https://jobs.lever.co/{token}` to confirm board is public
- Add valid tokens to `LEVER_TOKENS`
- Seed those companies in Supabase if not already there (`seed_companies.py`)

**Companies to check (Lever suspected):**
| Company | Lever token to try | Notes |
|---|---|---|
| Optiver | `optiver` | HK office, quant trading |
| Virtu Financial | `virtu` | HK office, market maker |
| SIG (Susquehanna) | `sig` | HK office, options trading |
| Citadel Securities | `citadelsecurities` | Separate from Citadel hedge fund |
| Bridgewater | `bridgewater` | Long shot, small HK presence |

**Known dead ends:** Citadel hedge fund (404), Two Sigma (custom site careers.twosigma.com), Millennium (Eightfold at career.mlp.com), HRT (moved to Greenhouse)

---

### ~~2.2 Add a Workday scraper for big banks~~ ✓ DONE
**Why:** Goldman Sachs, HSBC, JPMorgan, BofA, and Barclays all use Workday — none of them are currently scraped at all.
**File:** Create `scrapers/workday_scraper.py`, register companies in `scrape_all.py`
**Effort:** Medium. Workday has a semi-public JSON API (`/wday/cxs/{tenant}/jobs`) but the tenant ID varies per company and some use bot protection.

**Companies to add (Workday):**
| Company | Workday tenant to try | Priority |
|---|---|---|
| HSBC | `hsbc` | High — large HK presence |
| JPMorgan | `jpmorgan` | High — large HK presence |
| Goldman Sachs | `goldmansachs` | High |
| Morgan Stanley | `morganstanley` | High |
| Bank of America | `bankofamerica` | Medium |
| Barclays | `barclays` | Medium |
| Deutsche Bank | `deutschebank` | Medium |
| Nomura | `nomura` | Medium — strong HK/Asia presence |
| Macquarie | `macquarie` | Medium — HK office |
| BNP Paribas | `bnpparibas` | Low |
| Societe Generale | `socgen` | Low |
| Standard Chartered | `standardchartered` | Low |

**Suggested order to try:** HSBC → JPMorgan → Goldman → Morgan Stanley → rest

---

### 2.3 Investigate Citadel
**Why:** Citadel is a top target but neither their Greenhouse nor Lever board is reachable.
**Action:**
- Check `citadel.com/careers` — they may post directly on their own site
- Check `citadelsecurities.com/careers` — Citadel Securities is a separate entity and may have a different board
- See if the HTML is scrapeable (static pagination vs JS-rendered)
- If too complex, deprioritise and move on

---

## Priority 3 — Reliability

### ~~3.1 Add pipeline failure notifications~~ ✓ DONE
**Why:** If the GH Actions run fails (expired API key, DB connection issue, etc.) you'd only find out by checking the Actions tab manually.
**File:** `.github/workflows/daily-scrape.yml`
**Options (pick one):**
- **Easy:** Enable GitHub's built-in email notifications for failed runs (Settings → Notifications → Actions). No code needed.
- **Better:** Add a final workflow step with `if: failure()` that sends a plain-text email via `emailer.py` or a simple `curl` to a webhook.

---

## Dead Ends — Do Not Retry (investigated May 2026)

These were all checked and ruled out. Don't waste time on them again unless something major changes (e.g. a company migrates to Greenhouse/Workday).

| Company | What we tried | Result | Why blocked |
|---|---|---|---|
| Goldman Sachs | Workday search, Taleo | ✓ SOLVED | Custom GraphQL API at `api-higher.gs.com/gateway/api/v1/graphql` — no auth required, 54 HK jobs, full descriptions included. Scraper: `scrapers/goldman_scraper.py` |
| HSBC | Workday search | ✗ | Uses **custom ATS** (`mycareer.hsbc.com`) — no standard API |
| JPMorgan | Workday search | ✓ SOLVED | Oracle HCM public REST API — `hcmRestApi/resources/latest/recruitingCEJobRequisitions`, 131 HK jobs confirmed May 2026. Scraper: `scrapers/jpmorgan_scraper.py` |
| SIG (Susquehanna) | Lever (`sig`), careers page | ✗ | Uses **iCIMS** (`careers-sig.icims.com`) — no public API |
| Nomura | Workday search, careers page | ✗ | ATS unknown/custom — couldn't determine platform |
| Citadel (hedge fund) | Greenhouse (`citadel`), Lever (`citadel`), careers page | ✗ | Both boards 404; careers site returns 403 to scrapers |
| Citadel Securities | Lever (`citadelsecurities`), careers page | ✗ | Lever 404; careers site returns 403 to scrapers |
| Bridgewater | Lever (`bridgewater`) | ✗ | Lever 404 — minimal HK presence anyway |
| Akuna Capital | Greenhouse (`akunacapital`) | ✗ | Greenhouse works but 0 HK jobs — Chicago/Sydney/Singapore only |
| XTX Markets | Greenhouse (`xtxmarkets`) | ✗ | Greenhouse 404 — likely custom site |
| Citi | careers page | ✗ | Uses TalentBrew (custom) — not scrapeable |
| UBS | careers page | ✗ | Uses Taleo (`jobs.ubs.com/TGnewUI`) — not scrapeable |
| Optiver | Lever (`optiver`) | ✗ | Lever 404 — **actually uses Greenhouse** (`optiverus`) ✓ added |
| Virtu Financial | Lever (`virtu`) | ✗ | Lever 404 — **actually uses Greenhouse** (`virtu`) ✓ added |
| Two Sigma | All | ✗ | Custom careers site (`careers.twosigma.com`) — no public API, 0 HK jobs |
| Millennium Management | Lever, Greenhouse | ✗ | Uses **Eightfold** (`career.mlp.com`) — 19 HK jobs but no scrapeable API |
| Bank of America | Workday (assumed) | ✗ Not tried | Low priority — defer until others confirmed working |
| BNP Paribas | Taleo | ✗ | Uses `bnpparibas.tal.net` — not scrapeable |
| Societe Generale | Unknown | ✗ | Can't find Workday tenant — custom ATS likely |
| Standard Chartered | Workday | ✗ | `standard.wd1` is wrong company (US insurer); real SCB Workday URL unknown |
| Nomura | Taleo | ✗ | Uses `nomuracampus.tal.net` — not scrapeable |
| Lazard | Taleo | ✗ | Uses `lazard-careers.tal.net` — not scrapeable (small HK presence anyway) |
| Schroders | Workday | ✗ | Tenant `schroders.wd1` exists (422 = wrong site name) but correct site ID unknown |
| KKR | Workday | ✗ | Tenant `kkr.wd1` exists but correct site ID unknown |
| Apollo Global | Workday | ✗ | Tenant `apolloglobal.wd1` exists but correct site ID unknown |
| Blackstone | Workday `blackstone.wd1/Blackstone_Careers` | ✗ | Board works but 0 HK jobs currently |
| Invesco | Workday | ✗ | 0 HK jobs (global AM, limited HK presence) |
| Moelis & Company | Workday `moelis.wd1/Experienced-Hires` | ✗ | 0 HK jobs — US boutique IB |
| CLSA | Greenhouse `clsa` | ✗ | Board works but 0 total jobs — likely using different board |

---

## Priority 4 — Nice to have (do later)

### 4.1 Web dashboard
Browse and filter jobs, mark as applied/rejected, see scoring history.
**Stack:** FastAPI + simple HTML/Jinja2 frontend, reads from Supabase.

### 4.2 Application tracking
Add a status column to the `jobs` table: `applied / interviewing / offer / rejected`.
Update via dashboard (4.1) or a simple CLI command.

### 4.3 Additional notification channels
Telegram bot or Slack webhook as an alternative to email.

---

## Effort summary

| # | Task | Effort |
|---|---|---|
| 1.1 | Remove `--no-descriptions` | 2 min |
| 1.2 | Fix `schema.sql` | 30 min |
| 2.1 | Find + add Lever companies | 1–2 hrs (research heavy) |
| 2.2 | Workday scraper | 3–6 hrs |
| 2.3 | Investigate Citadel | 30 min |
| 3.1 | Failure notifications | 15 min (easy option) |
| 4.1 | Web dashboard | 1–2 days |
| 4.2 | Application tracking | 2–3 hrs |
| 4.3 | More notification channels | 1–2 hrs |
