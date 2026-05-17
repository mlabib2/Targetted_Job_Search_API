# HK Job Aggregator — To-Do

_Last updated: 2026-05-17_

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

### 2.3 Investigate Citadel — CONFIRMED DEAD END (May 2026)
**Citadel (hedge fund):** Greenhouse token `citadel` returns 404 — private board. No Lever board. Careers page blocks scrapers. Nothing to scrape.
**Citadel Securities:** Greenhouse token `citadelsecurities` exists (200 OK) but returns 0 total jobs currently. Will surface naturally in the daily run when/if they post. No further action needed.

---

## Priority 3 — Reliability

### ~~3.1 Add pipeline failure notifications~~ ✓ DONE
**Why:** If the GH Actions run fails (expired API key, DB connection issue, etc.) you'd only find out by checking the Actions tab manually.
**File:** `.github/workflows/daily-scrape.yml`
**Options (pick one):**
- **Easy:** Enable GitHub's built-in email notifications for failed runs (Settings → Notifications → Actions). No code needed.
- **Better:** Add a final workflow step with `if: failure()` that sends a plain-text email via `emailer.py` or a simple `curl` to a webhook.

---

## Company Coverage (May 2026)

_Only firms with a confirmed or likely Hong Kong office are tracked here. US/Europe-only firms are excluded at the bottom._

---

### ✅ Actively Scraped (29 companies)

These all run every day via `scrape_all.py`.

| Company | ATS / Method | Scraper | Notes |
|---|---|---|---|
| Goldman Sachs | Custom GraphQL | `goldman_scraper.py` | ~54 HK jobs, full descriptions |
| JPMorgan Chase | Oracle HCM REST | `jpmorgan_scraper.py` | ~131 HK jobs, descriptions via separate fetch |
| Standard Chartered | J2W sitemap | `standard_chartered_scraper.py` | ~112 HK jobs, **titles only** (JS-rendered site) |
| Morgan Stanley | Workday `ms.wd5/External` | `workday_scraper.py` | Technology division active |
| Barclays | Workday `barclays.wd3/External_Career_Site_Barclays` | `workday_scraper.py` | |
| Deutsche Bank | Workday `db.wd3/DBWebsite` | `workday_scraper.py` | |
| Macquarie | Workday `mq.wd3/CareersatMQ` | `workday_scraper.py` | |
| BlackRock | Workday `blackrock.wd1/BlackRock_Professional` | `workday_scraper.py` | |
| HKEX | Workday `hkex.wd3/HKEXCareerPage` | `workday_scraper.py` | Very HK-specific |
| Fidelity International (FIL) | Workday `fil.wd3/001` | `workday_scraper.py` | |
| State Street | Workday `statestreet.wd1/Global` | `workday_scraper.py` | ~10 HK jobs |
| Brevan Howard | Workday `brevanhoward.wd3/BH_ExternalCareers` | `workday_scraper.py` | Global macro hedge fund, HK office |
| Qube Research & Technologies | Greenhouse `quberesearchandtechnologies` | `greenhouse_scraper.py` | ~24 HK jobs |
| Jane Street | Greenhouse `janestreet` | `greenhouse_scraper.py` | ~17 HK jobs |
| Point72 | Greenhouse `point72` | `greenhouse_scraper.py` | ~9 HK jobs |
| Squarepoint Capital | Greenhouse `squarepointcapital` | `greenhouse_scraper.py` | ~9 HK jobs |
| Tower Research Capital | Greenhouse `towerresearchcapital` | `greenhouse_scraper.py` | ~7 HK jobs |
| Flow Traders | Greenhouse `flowtraders` | `greenhouse_scraper.py` | ~6 HK jobs |
| Schonfeld | Greenhouse `schonfeld` | `greenhouse_scraper.py` | ~6 HK jobs |
| Jump Trading | Greenhouse `jumptrading` | `greenhouse_scraper.py` | ~4 HK jobs |
| Optiver | Greenhouse `optiverus` | `greenhouse_scraper.py` | ~3 HK jobs |
| IMC Trading | Greenhouse `imc` | `greenhouse_scraper.py` | ~2 HK jobs |
| Man Group | Greenhouse `mangroup` | `greenhouse_scraper.py` | ~2 HK jobs |
| Virtu Financial | Greenhouse `virtu` | `greenhouse_scraper.py` | ~2 HK jobs |
| Engineers Gate | Greenhouse `engineersgate` | `greenhouse_scraper.py` | ~2 HK jobs |
| WorldQuant | Greenhouse `worldquant` | `greenhouse_scraper.py` | ~1 HK job |
| DRW | Greenhouse `drweng` | `greenhouse_scraper.py` | ~1 HK job |
| Hudson River Trading | Greenhouse `wehrtyou` | `greenhouse_scraper.py` | ~1 HK job |

---

### ⚠️ Needs Workaround — Board Confirmed, Blocked

These companies **definitely have a public job board** but we cannot access it programmatically. The fix for most of them is finding the correct Workday site name. If you ever visit their careers page in a browser and see the Workday URL (format: `{tenant}.wd1.myworkdayjobs.com/{SiteName}`), drop it here and I can wire up the scraper in minutes.

| Company | What we know | Blocker | Workaround needed |
|---|---|---|---|
| **PIMCO** | Workday on `pimco.wd3` and `pimcoinvestments.wd1` confirmed (422) | Site name unknown | Find URL: `pimco.wd3.myworkdayjobs.com/???` — careers page returns 403 to scrapers |
| **Marshall Wace** | Uses Greenhouse (`marshallwace`, 2 jobs, 0 HK); no public Workday found | Greenhouse has 0 HK roles | Check back quarterly; may post HK roles on Greenhouse |
| **Coatue Management** | Workday on `coatue.wd1` confirmed (422); no public portal found in web searches | Site name unknown | Find URL: `coatue.wd1.myworkdayjobs.com/???` |
| **Winton** | Greenhouse `winton` has 11 jobs but 0 HK; EU board (`job-boards.eu.greenhouse.io/winton`) returns 404 — inactive; Workday `winton.wd1` (422, site name unknown) | No active public board with HK jobs | Low priority — re-check quarterly |
| **UBS** | `ubs.wd3` is **not** UBS AG — it's "Unique Business Systems" (AV rental). UBS AG uses `ubs.com/careers` directly | No public Workday found; Taleo blocked | Low priority — UBS AG may not expose a public Workday board |
| **Citadel (hedge fund)** | Greenhouse 404, Lever 404, careers page 403 | All known boards blocked/private | Manually browse `citadel.com/careers` — board may have changed |
| **Citadel Securities** | Lever 404, careers page 403 | All known boards blocked | Manually browse `citadelsecurities.com/careers` |
| **Balyasny Asset Management** | Tenant `bamfunds.wd1` confirmed working (200 OK, site `External`) — but returns **401** | Auth required — private board | Low priority; board is internal-only |
| **DE Shaw** | Workday on `deshaw.wd1` confirmed — returns **401** | Auth required — likely internal board only | Low priority; D.E. Shaw is notoriously secretive |
| **Tudor Investment Corp** | Workday on `tudor.wd1` confirmed — returns **401** | Auth required — likely internal board only | Low priority |

---

### ✗ Dead End — ATS Not Scrapeable

These boards exist and likely have HK jobs, but the ATS itself does not expose a public API.

| Company | ATS | Why blocked |
|---|---|---|
| HSBC | Custom (`mycareer.hsbc.com`) | Proprietary ATS, no standard API — largest HK employer |
| Citi | TalentBrew / Radancy | API always returns `hasContent: false` — JS-rendered, anti-bot protected |
| ~~Millennium Management~~ | ✓ Now scraped — Eightfold public API, 18 HK jobs | `millennium_scraper.py` |
| SIG (Susquehanna) | iCIMS (`careers-sig.icims.com`) | iCIMS has no public job listing API |
| Bank of America | Workday `ghr.wd1/lateral-us` | Only US lateral hires board found; no international Workday board |
| Nomura | Taleo (`nomuracampus.tal.net`) | Taleo requires authentication |
| BNP Paribas | Taleo (`bnpparibas.tal.net`) | Taleo requires authentication |
| Societe Generale | Unknown / Custom | Can't identify ATS; careers page JS-rendered |
| Two Sigma | Custom (`careers.twosigma.com`) | Bespoke site, no API, and 0 HK jobs in practice |

---

### ✗ Dead End — Board Works, 0 HK Jobs

These companies have an accessible job board but currently post no Hong Kong roles. Worth re-checking quarterly.

| Company | Board | Last checked | Notes |
|---|---|---|---|
| AllianceBernstein | Workday `abglobal.wd1/alliancebernsteincareers` (85 jobs) | May 2026 | Asia presence is Taipei/India |
| AQR Capital | Greenhouse `aqr` (41 jobs) | May 2026 | HK office exists but no postings |
| Exodus Point | Greenhouse `exoduspoint` (2 jobs) | May 2026 | HK office exists; check again |
| Marshall Wace | Greenhouse `marshallwace` (2 jobs) | May 2026 | See Workday workaround above |
| Winton | Greenhouse `winton` (11 jobs) | May 2026 | See Workday workaround above |
| Akuna Capital | Greenhouse `akunacapital` | May 2026 | Chicago/Sydney/Singapore only |
| Blackstone | Workday `blackstone.wd1/Blackstone_Careers` | May 2026 | |
| Invesco | Workday | May 2026 | Limited HK presence |
| HAP Capital | All (404 everywhere) | May 2026 | HK-based HFT firm — no public board found; careers likely direct referral |
| GSA Capital | Greenhouse `gsacapital` (8 jobs) | May 2026 | UK-focused quant fund |
| Quadrature Capital | Greenhouse `quadraturecapital` (2 jobs) | May 2026 | |
| PDT Partners | Greenhouse `pdtpartners` (15 jobs) | May 2026 | US-focused |
| Bridgewater | Lever 404 | May 2026 | Very small HK office (client relations only) |

---

### — Excluded — No Hong Kong Office

Removed from tracking. US/Europe only firms with no HK hiring history.

`QuantLab` · `Headlands Technologies` · `Old Mission Capital` · `TransMarket Group` · `GTS` · `Volant Trading` · `Five Rings Capital` · `PDT Partners` · `Renaissance Technologies` · `Aquatic Capital` · `Voleon Capital` · `G-Research` · `Laurion Capital` · `Teza Technologies` · `Maverick Capital` · `Third Point` · `Verition Fund Management` · `Centiva Capital` · `PanAgora Asset Management` · `Guggenheim Partners` · `Highbridge Capital` · `Moelis & Company` · `Lazard` · `Credit Suisse` (merged into UBS)

---

## Priority 4 — Nice to have (do later)

### 4.1 Web dashboard
Browse and filter jobs, mark as applied/rejected, see scoring history.
**Stack:** FastAPI + simple HTML/Jinja2 frontend, reads from Supabase.

### ~~4.2 Application tracking~~ ✓ DONE
`track.py` CLI — `list`, `set <job_id> <status>`, `stats`.
Valid statuses: `new → seen → applied → interviewing → offer / rejected`
DB `set_job_status()` and `get_jobs_by_status()` added to `models/db.py`. No schema migration needed (column existed, just adding values).

### 4.3 Additional notification channels
Telegram bot or Slack webhook as an alternative to email.

---

## Remaining effort

| Task | Effort | Notes |
|---|---|---|
| Unlock "Needs Workaround" boards | ~5 min each | Just need the correct Workday URL from browser — find it, drop it in (PIMCO, Coatue) |
| 4.1 Web dashboard | 1–2 days | FastAPI + Jinja2, reads Supabase |
| 4.3 More notification channels | 1–2 hrs | Telegram bot or Slack webhook |
