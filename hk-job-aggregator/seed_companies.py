"""
Seed database with target HK finance companies
"""

from models.db import get_db

# Target HK Finance Companies
TARGET_COMPANIES = [
    {
        'name': 'Goldman Sachs Hong Kong',
        'career_url': 'https://www.goldmansachs.com/careers/students/programs/asia-pacific/hong-kong.html',
        'ats_platform': 'Workday',
        'notes': 'Check both campus and experienced roles'
    },
    {
        'name': 'Morgan Stanley Hong Kong',
        'career_url': 'https://morganstanley.tal.net/vx/candidate/cms/careerhome?site=Hong+Kong',
        'ats_platform': 'Taleo',
        'notes': 'Technology division highly active'
    },
    {
        'name': 'HSBC Hong Kong',
        'career_url': 'https://www.hsbc.com/careers/students-and-graduates/student-programmes/hong-kong',
        'ats_platform': 'Workday',
        'notes': 'Large tech teams, many entry roles'
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
        'career_url': 'https://careers.jpmorgan.com/global/en/students/programs/hong-kong',
        'ats_platform': 'Workday',
        'notes': 'Large tech org, many divisions'
    },
    {
        'name': 'Bank of America Hong Kong',
        'career_url': 'https://campus.bankofamerica.com/opportunities.html',
        'ats_platform': 'Workday',
        'notes': 'Technology Analyst programs'
    },
    {
        'name': 'Barclays Hong Kong',
        'career_url': 'https://search.jobs.barclays/career-areas/technology',
        'ats_platform': 'Custom',
        'notes': 'Investment banking tech'
    },
    # HK-based prop shops and tech-forward firms
    {
        'name': 'Optiver',
        'career_url': 'https://optiver.com/working-at-optiver/career-opportunities/',
        'ats_platform': 'SmartRecruiters',
        'notes': 'Market making, APAC HQ in Sydney but HK roles'
    },
    {
        'name': 'Flow Traders',
        'career_url': 'https://www.flowtraders.com/careers',
        'ats_platform': 'Custom',
        'notes': 'ETF market making'
    },
    {
        'name': 'Susquehanna International Group (SIG)',
        'career_url': 'https://sig.com/campus-programs/',
        'ats_platform': 'Custom',
        'notes': 'Quant trading, options market making'
    },
    {
        'name': 'IMC Trading',
        'career_url': 'https://careers.imc.com/us/en',
        'ats_platform': 'Custom',
        'notes': 'Tech-driven trading'
    },
    {
        'name': 'Virtu Financial',
        'career_url': 'https://www.virtu.com/careers/',
        'ats_platform': 'iCIMS',
        'notes': 'HFT, market making'
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
