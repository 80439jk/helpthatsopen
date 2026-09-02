#!/usr/bin/env python3
"""Reach rate and verification progress, from one or more call-sheet exports.

Reach rate is the input to the whole staffing model. docs/05-va-operations.md
extrapolates 5 FTE from an ASSUMED 60%. This measures it, and reprojects.

Runs off CSV exports — no database needed, so it works from day one.

  python3 scripts/reach_report.py tests/fixtures/*.csv
"""
import sys, csv, re, collections, argparse, datetime, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_call_sheet import parse   # one definition of what a row means

# docs/05-va-operations.md throughput model
CONTACTS_PER_YEAR = 92_000
MINUTES_PER_DIAL  = 4
HOURS_PER_FTE     = 2_080
CONTACT_DISPS     = {'reached', 'gatekeeper', 'callback_booked'}


def bar(pct, width=28):
    n = int(round(pct / 100 * width))
    return '█' * n + '·' * (width - n)


def main(paths, assumed):
    rows = []
    for p in paths:
        r, _ = parse(p, 'report')
        for x in r:
            x['file'] = pathlib.Path(p).name
        rows += r
    if not rows:
        sys.exit('no rows found')

    disp = collections.Counter(r['disposition'] for r in rows)
    blocked = disp['blocked']
    dialed = len(rows) - blocked
    contacts = sum(disp[d] for d in CONTACT_DISPS)
    rate = 100 * contacts / dialed if dialed else 0

    print(f'\n  VERIFICATION PROGRESS — {len(rows)} attempts logged, '
          f'{len({r["slug"] for r in rows})} distinct programs\n')
    print(f'  reach rate   {bar(rate)}  {rate:.0f}%   ({contacts} of {dialed} dialed)')
    print(f'  assumed      {bar(assumed)}  {assumed:.0f}%   (docs/05-va-operations.md)')

    if blocked:
        bp = 100 * blocked / len(rows)
        print(f'\n  BLOCKED       {bar(bp)}  {bp:.0f}%   {blocked} never placed by the dialer')
        print('                these are published nonprofit intake lines scrubbed against')
        print('                the consumer DNC list — a config decision, not attrition')

    print('\n  dispositions')
    for k, v in disp.most_common():
        mark = '  <- contact' if k in CONTACT_DISPS else ('  <- never dialed' if k == 'blocked' else '')
        print(f'    {v:>4}  {k:<16}{mark}')

    print('\n  by VA')
    byva = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r['disposition'] == 'blocked':
            continue
        byva[r['va'] or '(unnamed)'][0] += r['disposition'] in CONTACT_DISPS
        byva[r['va'] or '(unnamed)'][1] += 1
    for va, (c, d) in sorted(byva.items(), key=lambda kv: -kv[1][1]):
        print(f'    {va:<12} {c:>3}/{d:<3}  {100*c/d if d else 0:>3.0f}%')

    print('\n  by attempt number')
    byatt = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r['disposition'] == 'blocked':
            continue
        k = r['attempt'] or '1'
        byatt[k][0] += r['disposition'] in CONTACT_DISPS
        byatt[k][1] += 1
    for k in sorted(byatt):
        c, d = byatt[k]
        print(f'    attempt {k}    {c:>3}/{d:<3}  {100*c/d if d else 0:>3.0f}%')

    # statuses actually established
    est = [r for r in rows if r['status'] != 'unknown']
    print(f'\n  statuses established: {len(est)} of {len(rows)} attempts '
          f'({100*len(est)/len(rows):.0f}%)')
    for k, v in collections.Counter(r['status'] for r in est).most_common():
        print(f'    {v:>4}  {k}')

    # dead numbers — the aggregator tax
    dead = [r for r in rows if r['disposition'] in ('disconnected', 'wrong_number')]
    if dead:
        print(f'\n  dead numbers: {len(dead)} ({100*len(dead)/dialed:.0f}% of dialed) — re-source these')
        for r in dead:
            print(f'    {r["org"][:46]}')

    print('\n  STAFFING PROJECTION  (docs/05-va-operations.md model, '
          f'{CONTACTS_PER_YEAR:,} contacts/yr, {MINUTES_PER_DIAL} min/dial)')
    print(f'    {"":<18}{"reach":>8}{"dials/yr":>12}{"hours":>10}{"FTE":>7}')
    for label, r_ in (('assumed', assumed), ('measured', rate)):
        if r_ <= 0:
            continue
        dials = CONTACTS_PER_YEAR / (r_ / 100)
        hours = dials * MINUTES_PER_DIAL / 60
        print(f'    {label:<18}{r_:>7.0f}%{dials:>12,.0f}{hours:>10,.0f}{hours/HOURS_PER_FTE:>7.1f}')
    if blocked:
        eff = 100 * contacts / len(rows)
        dials = CONTACTS_PER_YEAR / (eff / 100)
        hours = dials * MINUTES_PER_DIAL / 60
        print(f'    {"measured + blocked":<18}{eff:>7.0f}%{dials:>12,.0f}{hours:>10,.0f}'
              f'{hours/HOURS_PER_FTE:>7.1f}')
        print('    (the last line is what the list actually costs while the dialer blocks)')

    n = len(rows)
    if n < 50:
        print(f'\n  NOTE: {n} attempts is a small sample. Treat the direction as real and the'
              '\n  decimal place as noise. Re-run this daily; it stabilises fast.')
    print()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('csvs', nargs='+')
    ap.add_argument('--assumed', type=float, default=60.0)
    a = ap.parse_args()
    main(a.csvs, a.assumed)
