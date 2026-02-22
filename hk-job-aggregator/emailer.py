"""
emailer.py — Weekly HTML digest of HK hedge fund jobs

Single unified table of all last-7-day jobs:
  - Scored jobs first, sorted by match_score DESC
  - Unscored jobs at the bottom (AI was off or hasn't run)

Usage:
    python emailer.py            # send digest
    python emailer.py --dry-run  # save digest_preview.html, don't send
"""

import sys
import os
import json
import smtplib
import argparse
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
from models.db import get_db

load_dotenv()

# ── DB queries ────────────────────────────────────────────────────────────────

def get_all_new_jobs(db) -> list:
    """All jobs from last 7 days, unsent. Scored first (desc), unscored last."""
    cur = db._cursor()
    cur.execute("""
        SELECT j.id, j.title, c.name AS company, j.url,
               j.match_score, j.match_reasons, j.location, j.first_seen_at
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE j.notified_at IS NULL
          AND j.first_seen_at >= NOW() - INTERVAL '7 days'
        ORDER BY j.match_score DESC NULLS LAST, c.name
    """)
    return [dict(row) for row in cur.fetchall()]


# ── HTML helpers ──────────────────────────────────────────────────────────────

TABLE_STYLE = "width:100%;border-collapse:collapse;font-size:13px;"
TH_STYLE = "padding:8px 12px;text-align:left;background:#1e3a5f;color:#fff;font-weight:600;white-space:nowrap;"
TD_STYLE = "padding:10px 12px;border-bottom:1px solid #e5e7eb;vertical-align:top;"
TD_ALT_STYLE = "padding:10px 12px;border-bottom:1px solid #e5e7eb;vertical-align:top;background:#f9fafb;"


def score_badge(score) -> str:
    if score is None:
        return '<span style="display:inline-block;padding:2px 8px;border-radius:12px;background:#f3f4f6;color:#9ca3af;font-size:12px;">—</span>'
    pct = int(score * 100)
    if pct >= 70:
        color, bg = "#166534", "#dcfce7"
    elif pct >= 45:
        color, bg = "#92400e", "#fef3c7"
    else:
        color, bg = "#374151", "#f3f4f6"
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:12px;'
        f'background:{bg};color:{color};font-weight:700;font-size:12px;">{pct}%</span>'
    )


def parse_reasons(raw) -> list:
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return [raw]
    return [r for r in raw if r and not r.startswith("Pre-filtered")]


def all_jobs_table(jobs: list) -> str:
    if not jobs:
        return '<p style="color:#6b7280;font-style:italic;">No new jobs this week.</p>'

    rows = ""
    for i, job in enumerate(jobs):
        td = TD_ALT_STYLE if i % 2 else TD_STYLE
        score = job.get('match_score')
        reasons = parse_reasons(job.get('match_reasons')) if score is not None else []
        reasons_html = (
            "<ul style='margin:4px 0 0 0;padding-left:16px;color:#374151;font-size:12px;'>"
            + "".join(f"<li>{r}</li>" for r in reasons[:3])
            + "</ul>"
        ) if reasons else ""

        rows += f"""<tr>
          <td style="{td}">{score_badge(score)}</td>
          <td style="{td}"><strong>{job['company']}</strong></td>
          <td style="{td}">
            <a href="{job['url']}" style="color:#1d4ed8;text-decoration:none;font-weight:600;">
              {job['title']}
            </a>
            {reasons_html}
          </td>
          <td style="{td};color:#6b7280;">{job.get('location') or 'Hong Kong'}</td>
          <td style="{td}">
            <a href="{job['url']}" style="display:inline-block;padding:4px 12px;background:#1e3a5f;
               color:#fff;border-radius:4px;text-decoration:none;font-size:12px;white-space:nowrap;">
              Apply →
            </a>
          </td>
        </tr>"""

    return f"""
    <table style="{TABLE_STYLE}">
      <thead><tr>
        <th style="{TH_STYLE}">Score</th>
        <th style="{TH_STYLE}">Company</th>
        <th style="{TH_STYLE}">Role</th>
        <th style="{TH_STYLE}">Location</th>
        <th style="{TH_STYLE}"></th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


def build_html(jobs: list) -> str:
    today = datetime.now().strftime("%d %b %Y")
    scored_count = sum(1 for j in jobs if j.get('match_score') is not None)
    unscored_count = len(jobs) - scored_count
    companies = len(set(j['company'] for j in jobs))

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px;">
<tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">

  <!-- Header -->
  <tr>
    <td style="background:#1e3a5f;padding:28px 32px;">
      <p style="margin:0;font-size:11px;color:#93c5fd;letter-spacing:1.5px;text-transform:uppercase;">HK Hedge Fund Job Digest</p>
      <h1 style="margin:6px 0 0;font-size:24px;color:#fff;font-weight:700;">{len(jobs)} job{"s" if len(jobs) != 1 else ""} this week</h1>
      <p style="margin:6px 0 0;font-size:13px;color:#93c5fd;">{today} · {scored_count} scored · {unscored_count} unscored · sorted by fit</p>
    </td>
  </tr>

  <!-- Unified job table -->
  <tr><td style="padding:24px 32px 0;">
    <h2 style="margin:0 0 2px;font-size:16px;color:#1e3a5f;">All New Jobs ({len(jobs)})</h2>
    <p style="margin:0 0 12px;font-size:12px;color:#9ca3af;">Scored jobs first — sorted by AI fit score. Tweak your CV for amber ones.</p>
    {all_jobs_table(jobs)}
  </td></tr>

  <!-- Footer -->
  <tr>
    <td style="padding:24px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;margin-top:24px;">
      <p style="margin:0;font-size:11px;color:#9ca3af;text-align:center;">
        HK Job Aggregator · Greenhouse scraper · {len(jobs)} new jobs across {companies} companies
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Send ──────────────────────────────────────────────────────────────────────

def send_email(html: str, scored_count: int, unscored_count: int):
    gmail = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    notify_raw = os.getenv("NOTIFY_EMAIL", "")
    recipients = [addr.strip() for addr in notify_raw.split(",") if addr.strip()]
    today = datetime.now().strftime("%d %b %Y")

    total = scored_count + unscored_count
    subject = f"[HK Jobs] {total} new job{'s' if total != 1 else ''} — {scored_count} scored — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail, password)
        server.sendmail(gmail, recipients, msg.as_string())


# ── Main ──────────────────────────────────────────────────────────────────────

def run_emailer(dry_run: bool = False):
    print("=" * 60)
    print("HK Job Digest — Emailer")
    print("=" * 60 + "\n")

    with get_db() as db:
        jobs = get_all_new_jobs(db)
        scored_count = sum(1 for j in jobs if j.get('match_score') is not None)
        unscored_count = len(jobs) - scored_count

        print(f"Total new jobs (last 7 days): {len(jobs)}")
        print(f"  Scored:   {scored_count}")
        print(f"  Unscored: {unscored_count}")

        if not jobs:
            print("\nNothing to send.")
            return

        html = build_html(jobs)

        if dry_run:
            out = Path("digest_preview.html")
            out.write_text(html)
            print(f"\nDry run — preview saved to: {out.resolve()}")
            print("Open in browser to check layout.")
            return

        print("\nSending...")
        send_email(html, scored_count, unscored_count)

        for job in jobs:
            db.mark_job_notified(job['id'])

        notify_raw = os.getenv("NOTIFY_EMAIL", "")
        recipients_log = [a.strip() for a in notify_raw.split(",") if a.strip()]
        print(f"Sent to {', '.join(recipients_log)}")
        print(f"Marked {len(jobs)} jobs as notified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Save HTML preview instead of sending email")
    args = parser.parse_args()

    run_emailer(dry_run=args.dry_run)
