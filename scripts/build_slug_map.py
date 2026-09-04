#!/usr/bin/env python3
"""Organization -> (primary record, separate rent record).

The call sheet is one row per organization; the database is one row per program.
This resolves which program records a VA can honestly speak for after one call.

The PRIMARY record is what the sheet's Status cell writes to: the utility pot
where there is one, otherwise the rent pot, otherwise whatever single program
the agency runs. Every one of the 99 rows resolves to a primary, so no row is
dark -- a food pantry's "are you open" is as real a question as CEAP's.

The RENT record is filled only where rent is a genuinely separate pot from the
primary, which is the case wherever an agency runs CEAP and CSBG side by side.
That is the second status cell, and it is the reason rent keeps its coverage
without splitting the sheet into one row per program.

Everything else an agency runs (weatherization, transport) keeps its record and
its need tags, so the agency still surfaces in those searches. It simply never
carries a status light, because nobody verified it.

  python3 scripts/build_slug_map.py            # writes data/slug_map.csv
  python3 scripts/build_slug_map.py --check    # report only
"""
import json, csv, glob, argparse, collections, pathlib, sys

UTILITY = {'electric_bill', 'gas_bill', 'reconnect_fee', 'utility_deposit', 'water_bill'}
RENT    = {'rent_assistance', 'eviction_prevention', 'mortgage_assistance', 'deposit_assistance'}


def pick(recs, tags):
    """The record that best represents this need: most matching tags, fewest others."""
    hits = [r for r in recs if tags & set(r.get('need_tags') or ())]
    if not hits:
        return None
    return min(hits, key=lambda r: (-len(tags & set(r['need_tags'])), len(r['need_tags']), r['slug']))


def build():
    byorg = collections.defaultdict(list)
    for f in sorted(glob.glob('data/listings/*.jsonl')):
        for line in open(f):
            r = json.loads(line)
            byorg[r['org_name']].append(r)

    out = []
    for org, recs in sorted(byorg.items()):
        u, rn = pick(recs, UTILITY), pick(recs, RENT)
        # utility first, then rent, then the agency's only program -- never nothing
        primary = u or rn or min(recs, key=lambda r: (len(r.get('need_tags') or ()), r['slug']))
        # a second cell only where rent is its own pot; same record means one question
        rent = rn if rn and rn['slug'] != primary['slug'] else None
        out.append({
            'org_name': org,
            'slug': primary['slug'],
            'primary_need': 'utility' if u else ('rent' if rn else 'other'),
            'rent_slug': rent['slug'] if rent else '',
            'unlit_records': ';'.join(sorted(
                r['slug'] for r in recs
                if r['slug'] not in {x['slug'] for x in (primary, rent) if x})),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()

    two  = [r for r in rows if r['rent_slug']]
    byneed = collections.Counter(r['primary_need'] for r in rows)
    unlit  = sum(len(r['unlit_records'].split(';')) for r in rows if r['unlit_records'])

    print(f'{len(rows)} organizations, {len(rows)} with a Status cell -- no row is dark')
    print(f"  primary is the utility pot   {byneed['utility']:3}")
    print(f"  primary is the rent pot      {byneed['rent']:3}")
    print(f"  primary is the only program  {byneed['other']:3}")
    print(f'\n  {len(two):3} rows also get a live Rent status cell (rent is a separate pot)')
    print(f'  {len(rows)-len(two):3} rows have that cell greyed out')
    print(f'\n  {unlit} program records stay unlit -- listed in search, never a status light')
    assert all(r['slug'] for r in rows), 'a row resolved to no primary record'

    if a.check:
        return
    p = pathlib.Path('data/slug_map.csv')
    with p.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f'\nwrote {p} ({len(rows)} rows)')


if __name__ == '__main__':
    main()
