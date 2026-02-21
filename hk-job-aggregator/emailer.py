"""
emailer.py — Weekly HTML digest of HK hedge fund jobs

Two sections:
  1. AI-Scored Matches  — jobs with match_score >= threshold, unsent, last 7 days
  2. New Unscored Jobs  — jobs with match_score IS NULL, last 7 days
     (shown when AI is disabled/failed so you never miss a posting)

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

MATCH_THRESHOLD = 0.6


# ── DB queries ────────────────────────────────────────────────────────────────

def get_scored_matches(db) -> list:
    cur = db._cursor()
    cur.execute("""
        SELECT j.id, j.title, c.name AS company, j.url,
               j.match_score, j.match_reasons, j.location, j.first_seen_at
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE j.match_score >= %s
          AND j.notified_at IS NULL
          AND j.first_seen_at >= NOW() - INTERVAL '7 days'
        ORDER BY j.match_score DESC, c.name
    """, (MATCH_THRESHOLD,))
    return [dict(row) for row in cur.fetchall()]


def get_unscored_new(db) -> list:
    """Jobs scraped this week that haven't been scored yet (AI was off/failed)."""
    cur = db._cursor()
    cur.execute("""
        SELECT j.id, j.title, c.name AS company, j.url,
               j.location, j.first_seen_at
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE j.match_score IS NULL
          AND j.notified_at IS NULL
          AND j.first_seen_at >= NOW() - INTERVAL '7 days'
        ORDER BY c.name, j.title
    """)
    return [dict(row) for row in cur.fetchall()]


# ── HTML helpers ──────────────────────────────────────────────────────────────

TABLE_STYLE = "width:100%;border-collapse:collapse;font-size:13px;"
TH_STYLE = "padding:8px 12px;text-align:left;background:#1e3a5f;color:#fff;font-weight:600;white-space:nowrap;"
TD_STYLE = "padding:10px 12px;border-bottom:1px solid #e5e7eb;vertical-align:top;"
TD_ALT_STYLE = "padding:10px 12px;border-bottom:1px solid #e5e7eb;vertical-align:top;background:#f9fafb;"


def score_badge(score: float) -> str:
    pct = int(score * 100)
    if pct >= 80:
        color, bg = "#166534", "#dcfce7"
    elif pct >= 60:
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


def scored_table(jobs: list) -> str:
    if not jobs:
        return '<p style="color:#6b7280;font-style:italic;">No scored matches this week.</p>'

    rows = ""
    for i, job in enumerate(jobs):
        td = TD_ALT_STYLE if i % 2 else TD_STYLE
        reasons = parse_reasons(job.get('match_reasons'))
        reasons_html = (
            "<ul style='margin:4px 0 0 0;padding-left:16px;color:#374151;'>"
            + "".join(f"<li>{r}</li>" for r in reasons[:3])
            + "</ul>"
        ) if reasons else ""

        rows += f"""<tr>
          <td style="{td}">{score_badge(job['match_score'])}</td>
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


def unscored_table(jobs: list) -> str:
    if not jobs:
        return '<p style="color:#6b7280;font-style:italic;">No unscored jobs this week.</p>'

    rows = ""
    for i, job in enumerate(jobs):
        td = TD_ALT_STYLE if i % 2 else TD_STYLE
        rows += f"""<tr>
          <td style="{td}"><strong>{job['company']}</strong></td>
          <td style="{td}">
            <a href="{job['url']}" style="color:#1d4ed8;text-decoration:none;font-weight:600;">
              {job['title']}
            </a>
          </td>
          <td style="{td};color:#6b7280;">{job.get('location') or 'Hong Kong'}</td>
          <td style="{td}">
            <a href="{job['url']}" style="display:inline-block;padding:4px 12px;background:#6b7280;
               color:#fff;border-radius:4px;text-decoration:none;font-size:12px;white-space:nowrap;">
              View →
            </a>
          </td>
        </tr>"""

    return f"""
    <table style="{TABLE_STYLE}">
      <thead><tr>
        <th style="{TH_STYLE}">Company</th>
        <th style="{TH_STYLE}">Role</th>
        <th style="{TH_STYLE}">Location</th>
        <th style="{TH_STYLE}"></th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


def section(title: str, subtitle: str, content: str, accent: str = "#1e3a5f") -> str:
    return f"""
    <tr><td style="padding:24px 32px 0;">
      <h2 style="margin:0 0 2px;font-size:16px;color:{accent};">{title}</h2>
      <p style="margin:0 0 12px;font-size:12px;color:#9ca3af;">{subtitle}</p>
      {content}
    </td></tr>"""


def build_html(scored: list, unscored: list) -> str:
    today = datetime.now().strftime("%d %b %Y")
    total = len(scored) + len(unscored)

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
      <h1 style="margin:6px 0 0;font-size:24px;color:#fff;font-weight:700;">{len(scored)} match{"es" if len(scored) != 1 else ""} · {len(unscored)} unscored</h1>
      <p style="margin:6px 0 0;font-size:13px;color:#93c5fd;">{today} · Last 7 days · Threshold {int(MATCH_THRESHOLD*100)}%</p>
    </td>
  </tr>

  <!-- Scored matches -->
  {section(
      f"AI-Scored Matches ({len(scored)})",
      "Jobs scored above your match threshold — sorted by fit",
      scored_table(scored),
      "#1e3a5f"
  )}

  <!-- Divider -->
  <tr><td style="padding:20px 32px 0;"><hr style="border:none;border-top:1px solid #e5e7eb;margin:0;"></td></tr>

  <!-- Unscored -->
  {section(
      f"New Unscored Jobs ({len(unscored)})",
      "AI scorer was off or hasn't run yet — review manually",
      unscored_table(unscored),
      "#6b7280"
  )}

  <!-- Footer -->
  <tr>
    <td style="padding:24px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;margin-top:24px;">
      <p style="margin:0;font-size:11px;color:#9ca3af;text-align:center;">
        HK Job Aggregator · Greenhouse scraper · {total} new jobs this week across {len(set(j['company'] for j in scored + unscored))} companies
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
    notify = os.getenv("NOTIFY_EMAIL")
    today = datetime.now().strftime("%d %b %Y")

    subject = f"[HK Jobs] {scored_count} match{'es' if scored_count != 1 else ''}, {unscored_count} unscored — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail
    msg["To"] = notify
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail, password)
        server.sendmail(gmail, notify, msg.as_string())


# ── Main ──────────────────────────────────────────────────────────────────────

def run_emailer(dry_run: bool = False):
    print("=" * 60)
    print("HK Job Digest — Emailer")
    print("=" * 60 + "\n")

    with get_db() as db:
        scored = get_scored_matches(db)
        unscored = get_unscored_new(db)

        print(f"Scored matches (>= {int(MATCH_THRESHOLD*100)}%): {len(scored)}")
        print(f"Unscored new jobs:              {len(unscored)}")

        if not scored and not unscored:
            print("\nNothing to send.")
            return

        html = build_html(scored, unscored)

        if dry_run:
            out = Path("digest_preview.html")
            out.write_text(html)
            print(f"\nDry run — preview saved to: {out.resolve()}")
            print("Open in browser to check layout.")
            return

        print("\nSending...")
        send_email(html, len(scored), len(unscored))

        for job in scored + unscored:
            db.mark_job_notified(job['id'])

        print(f"Sent to {os.getenv('NOTIFY_EMAIL')}")
        print(f"Marked {len(scored)} scored + {len(unscored)} unscored jobs as notified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Save HTML preview instead of sending email")
    args = parser.parse_args()

    run_emailer(dry_run=args.dry_run)
