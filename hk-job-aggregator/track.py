"""
track.py — Application status tracker

Usage:
    python track.py list                        # new jobs, score >= 0.6
    python track.py list --status applied       # list by status
    python track.py list --status new --all     # all new jobs regardless of score
    python track.py set <job_id> applied        # mark as applied
    python track.py set <job_id> interviewing
    python track.py set <job_id> offer
    python track.py set <job_id> rejected
    python track.py set <job_id> new            # un-archive / reset
    python track.py stats                       # pipeline overview
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).parent))

from models.db import get_db, JobDatabase

VALID_STATUSES = sorted(JobDatabase.VALID_STATUSES)

STATUS_EMOJI = {
    'new':          '🆕',
    'seen':         '👁 ',
    'applied':      '📨',
    'interviewing': '🤝',
    'offer':        '🎉',
    'rejected':     '❌',
}

SCORE_THRESHOLD = 0.6


def _fmt_score(score) -> str:
    if score is None:
        return '  —  '
    bar = '█' * int(score * 5) + '░' * (5 - int(score * 5))
    return f'{bar} {score:.2f}'


def _fmt_date(dt) -> str:
    if dt is None:
        return '—'
    if hasattr(dt, 'date'):
        return dt.date().isoformat()
    return str(dt)[:10]


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n - 1] + '…'


def cmd_list(args):
    status = args.status
    show_all = getattr(args, 'all', False)

    with get_db() as db:
        jobs = db.get_jobs_by_status(status=status, limit=100)

    if not status:
        # Default: show new jobs above threshold
        if not show_all:
            jobs = [j for j in jobs if j['status'] == 'new'
                    and (j['match_score'] or 0) >= SCORE_THRESHOLD]
        else:
            jobs = [j for j in jobs if j['status'] == 'new']

    if not jobs:
        label = f"status={status}" if status else "new jobs above score threshold"
        print(f"No jobs found ({label}).")
        return

    col_id    = 6
    col_score = 12
    col_co    = 22
    col_title = 45
    col_date  = 10

    header = (f"{'ID':<{col_id}}  {'Score':<{col_score}}  {'Status':<13}"
              f"{'Company':<{col_co}}  {'Title':<{col_title}}  {'Seen'}")
    print(header)
    print('─' * len(header))

    for j in jobs:
        emoji = STATUS_EMOJI.get(j['status'], '  ')
        print(
            f"{j['id']:<{col_id}}  "
            f"{_fmt_score(j['match_score']):<{col_score}}  "
            f"{emoji} {j['status']:<11}"
            f"{_truncate(j['company'], col_co):<{col_co}}  "
            f"{_truncate(j['title'], col_title):<{col_title}}  "
            f"{_fmt_date(j['first_seen_at'])}"
        )


def cmd_set(args):
    job_id = args.job_id
    status = args.status

    with get_db() as db:
        updated = db.set_job_status(job_id, status)

    if updated:
        emoji = STATUS_EMOJI.get(status, '')
        print(f"Job {job_id} → {emoji} {status}")
    else:
        print(f"Job {job_id} not found.")
        sys.exit(1)


def cmd_stats(args):
    with get_db() as db:
        counts = db.get_application_stats()

    total = sum(counts.values())
    print(f"\nApplication pipeline  ({total} total jobs)\n")
    for status in ['new', 'seen', 'applied', 'interviewing', 'offer', 'rejected']:
        n = counts.get(status, 0)
        emoji = STATUS_EMOJI.get(status, '  ')
        bar = '█' * min(n, 40)
        print(f"  {emoji} {status:<13}  {n:>4}  {bar}")

    other = {k: v for k, v in counts.items() if k not in STATUS_EMOJI}
    for status, n in other.items():
        print(f"     {status:<13}  {n:>4}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Application status tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest='cmd', required=True)

    # list
    p_list = sub.add_parser('list', help='List jobs')
    p_list.add_argument('--status', choices=VALID_STATUSES, default=None,
                        help='Filter by status (default: new + score >= 0.6)')
    p_list.add_argument('--all', action='store_true',
                        help='Show all new jobs regardless of score')

    # set
    p_set = sub.add_parser('set', help='Set status on a job')
    p_set.add_argument('job_id', type=int, help='Job ID from list')
    p_set.add_argument('status', choices=VALID_STATUSES, help='New status')

    # stats
    sub.add_parser('stats', help='Show pipeline overview')

    args = parser.parse_args()

    dispatch = {'list': cmd_list, 'set': cmd_set, 'stats': cmd_stats}
    dispatch[args.cmd](args)


if __name__ == '__main__':
    main()
