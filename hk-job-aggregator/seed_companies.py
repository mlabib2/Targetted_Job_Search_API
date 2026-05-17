"""
Seed database with target HK finance companies
"""

from models.db import get_db

# Target HK Finance Companies
TARGET_COMPANIES = [
    {
        'name': 'Goldman Sachs Hong Kong',
        'career_url': 'https://higher.gs.com/results',
        'ats_platform': 'Custom GraphQL',
        'notes': 'Custom Next.js/GraphQL careers site — API at api-higher.gs.com/gateway/api/v1/graphql, no auth required, 112 HK jobs confirmed May 2026'
    },
    {
        'name': 'Morgan Stanley Hong Kong',
        'career_url': 'https://ms.wd5.myworkdayjobs.com/External',
        'ats_platform': 'Workday',
        'notes': 'Technology division highly active — tenant: ms, wd5, site: External'
    },
    {
        'name': 'HSBC Hong Kong',
        'career_url': 'https://mycareer.hsbc.com/',
        'ats_platform': 'Custom',
        'notes': 'Custom ATS at mycareer.hsbc.com — no standard API, not scrapeable'
    },
    {
        'name': 'Citadel Securities',
        'career_url': 'https://www.citadelsecurities.com/careers/',
        'ats_platform': 'Greenhouse',
        'notes': 'High-frequency trading, competitive pay'
    },
    {
        'name': 'Jane Street',
        'career_url': 'https://www.janestreet.com/join-jane-street/apply/',
        'ats_platform': 'Custom',
        'notes': 'Quant trading, OCaml/functional programming'
    },
    {
        'name': 'Jump Trading',
        'career_url': 'https://www.jumptrading.com/careers/',
        'ats_platform': 'Greenhouse',
        'notes': 'HFT, strong tech culture'
    },
    {
        'name': 'DRW',
        'career_url': 'https://drw.com/careers/',
        'ats_platform': 'Greenhouse',
        'notes': 'Prop trading, research-focused'
    },
    {
        'name': 'JPMorgan Chase Hong Kong',
        'career_url': 'https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs',
        'ats_platform': 'Oracle HCM',
        'notes': 'Oracle HCM public REST API at hcmRestApi/resources/latest/recruitingCEJobRequisitions — 131 HK jobs confirmed May 2026, site=CX_1001'
    },
    {
        'name': 'Bank of America Hong Kong',
        'career_url': 'https://campus.bankofamerica.com/opportunities.html',
        'ats_platform': 'Workday',
        'notes': 'Technology Analyst programs'
    },
    {
        'name': 'Barclays Hong Kong',
        'career_url': 'https://barclays.wd3.myworkdayjobs.com/External_Career_Site_Barclays',
        'ats_platform': 'Workday',
        'notes': 'Investment banking tech — tenant: barclays, wd3, site: External_Career_Site_Barclays'
    },
    # HK-based prop shops and tech-forward firms
    {
        'name': 'Optiver',
        'career_url': 'https://boards.greenhouse.io/optiverus',
        'ats_platform': 'Greenhouse',
        'notes': 'Market making, APAC HQ in Sydney but HK roles — token: optiverus'
    },
    {
        'name': 'Flow Traders',
        'career_url': 'https://www.flowtraders.com/careers',
        'ats_platform': 'Custom',
        'notes': 'ETF market making'
    },
    {
        'name': 'Susquehanna International Group (SIG)',
        'career_url': 'https://careers-sig.icims.com/jobs/search',
        'ats_platform': 'iCIMS',
        'notes': 'Uses iCIMS (careers-sig.icims.com) — no public API, not scrapeable'
    },
    {
        'name': 'IMC Trading',
        'career_url': 'https://careers.imc.com/us/en',
        'ats_platform': 'Custom',
        'notes': 'Tech-driven trading'
    },
    {
        'name': 'Virtu Financial',
        'career_url': 'https://job-boards.greenhouse.io/virtu',
        'ats_platform': 'Greenhouse',
        'notes': 'HFT, market making — token: virtu'
    },
    # Greenhouse hedge funds with confirmed HK jobs
    {
        'name': 'Point72',
        'career_url': 'https://point72.com/careers/',
        'ats_platform': 'Greenhouse',
        'notes': 'Multi-strategy hedge fund, strong HK presence'
    },
    {
        'name': 'Schonfeld',
        'career_url': 'https://www.schonfeld.com/careers/',
        'ats_platform': 'Greenhouse',
        'notes': 'Multi-strategy hedge fund'
    },
    {
        'name': 'Man Group',
        'career_url': 'https://www.man.com/careers',
        'ats_platform': 'Greenhouse',
        'notes': 'Quant hedge fund'
    },
    {
        'name': 'WorldQuant',
        'career_url': 'https://www.worldquant.com/career-listing/',
        'ats_platform': 'Greenhouse',
        'notes': 'Quant research firm'
    },
    {
        'name': 'Qube Research & Technologies',
        'career_url': 'https://www.qube-rt.com/careers/',
        'ats_platform': 'Greenhouse',
        'notes': 'Quant trading, strong HK presence'
    },
    {
        'name': 'Squarepoint Capital',
        'career_url': 'https://www.squarepointcap.com/careers',
        'ats_platform': 'Greenhouse',
        'notes': 'Quant hedge fund'
    },
    {
        'name': 'Tower Research Capital',
        'career_url': 'https://www.tower-research.com/open-positions',
        'ats_platform': 'Greenhouse',
        'notes': 'HFT prop trading'
    },
    # Workday companies (confirmed tenant IDs, May 2026)
    {
        'name': 'Deutsche Bank',
        'career_url': 'https://db.wd3.myworkdayjobs.com/DBWebsite',
        'ats_platform': 'Workday',
        'notes': 'Investment bank, HK tech and markets roles — tenant: db, wd3, site: DBWebsite'
    },
    {
        'name': 'Macquarie',
        'career_url': 'https://mq.wd3.myworkdayjobs.com/CareersatMQ',
        'ats_platform': 'Workday',
        'notes': 'Investment bank/asset manager, HK office — tenant: mq, wd3, site: CareersatMQ'
    },
    {
        'name': 'BlackRock',
        'career_url': 'https://blackrock.wd1.myworkdayjobs.com/BlackRock_Professional',
        'ats_platform': 'Workday',
        'notes': "World's largest asset manager, Aladdin tech platform, HK office — tenant: blackrock, wd1, site: BlackRock_Professional"
    },
    {
        'name': 'HKEX',
        'career_url': 'https://hkex.wd3.myworkdayjobs.com/HKEXCareerPage',
        'ats_platform': 'Workday',
        'notes': 'Hong Kong Stock Exchange — tech and data roles, very HK-specific — tenant: hkex, wd3, site: HKEXCareerPage'
    },
    {
        'name': 'Fidelity International',
        'career_url': 'https://fil.wd3.myworkdayjobs.com/001',
        'ats_platform': 'Workday',
        'notes': 'Global asset manager (FIL), HK office — tenant: fil, wd3, site: 001'
    },
    {
        'name': 'State Street',
        'career_url': 'https://statestreet.wd1.myworkdayjobs.com/Global',
        'ats_platform': 'Workday',
        'notes': 'Global custodian/asset manager, APAC hub in HK — 10 HK jobs confirmed May 2026 — tenant: statestreet, wd1, site: Global'
    },
    # Other firms with confirmed HK presence (custom/unsupported ATS or pending)
    {
        'name': 'Two Sigma',
        'career_url': 'https://careers.twosigma.com/',
        'ats_platform': 'Custom',
        'notes': 'Quant hedge fund — custom careers site, no public API, 0 HK jobs currently'
    },
    {
        'name': 'Hudson River Trading',
        'career_url': 'https://boards.greenhouse.io/wehrtyou',
        'ats_platform': 'Greenhouse',
        'notes': 'HFT / market maker (board token: wehrtyou)'
    },
    {
        'name': 'Millennium Management',
        'career_url': 'https://career.mlp.com/careers',
        'ats_platform': 'Eightfold',
        'notes': 'Multi-strat hedge fund — 19 HK jobs, Eightfold ATS (not scrapeable yet)'
    },
    {
        'name': 'Citadel',
        'career_url': 'https://www.citadel.com/careers/',
        'ats_platform': 'Unknown',
        'notes': 'Greenhouse 404, Lever 404, careers page returns 403 to scrapers — manually check in browser'
    },
    {
        'name': 'Standard Chartered Hong Kong',
        'career_url': 'https://jobs.standardchartered.com',
        'ats_platform': 'SuccessFactors J2W',
        'notes': 'J2W/CSB site (ssoCompanyId=standardch) — fully JS-rendered, no JSON API. Scraped via public sitemap: 112 HK jobs confirmed May 2026. Locations: Central, Kwun Tong, Quarry Bay.'
    },
    {
        'name': 'Engineers Gate',
        'career_url': 'https://boards.greenhouse.io/engineersgate',
        'ats_platform': 'Greenhouse',
        'notes': 'Quant/systematic hedge fund — token: engineersgate, 2 HK jobs confirmed May 2026'
    },
    {
        'name': 'Brevan Howard',
        'career_url': 'https://brevanhoward.wd3.myworkdayjobs.com/BH_ExternalCareers',
        'ats_platform': 'Workday',
        'notes': 'Global macro hedge fund, HK office — tenant: brevanhoward, wd3, site: BH_ExternalCareers. Confirmed 200 OK May 2026.'
    },
]


def seed_companies():
    """Add all target companies to database"""
    with get_db() as db:
        print("Seeding target HK finance companies...\n")

        for company in TARGET_COMPANIES:
            try:
                company_id = db.add_company(
                    name=company['name'],
                    career_url=company['career_url'],
                    ats_platform=company['ats_platform'],
                    notes=company['notes']
                )
                print(f"✓ Added: {company['name']} ({company['ats_platform']})")
            except Exception as e:
                # Likely duplicate, skip
                print(f"⊘ Skipped: {company['name']} (already exists)")

        print(f"\n✓ Database seeded with {len(TARGET_COMPANIES)} companies")

        # Show summary
        companies = db.get_active_companies()
        print(f"\nActive companies in database: {len(companies)}")

        # Count by ATS platform
        from collections import Counter
        platforms = Counter([c['ats_platform'] for c in companies])
        print("\nATS Platform breakdown:")
        for platform, count in platforms.most_common():
            print(f"  {platform}: {count}")


if __name__ == "__main__":
    seed_companies()
