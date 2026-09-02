#!/usr/bin/env python3
"""Week-one verification call sheet.

Cold start: nothing is verified, so the priority score reduces to reach + volatility
(docs/02-data-model.md section 6). This ranks by that and emits a CSV whose right-hand
columns are exactly the fields the script in docs/05-va-operations.md captures, in the
order the call makes them.

No database required -- a spreadsheet and a phone. Fill it in, hand it back, and the
rows import as status_log entries.
"""
import csv, json, math, argparse, collections

TIER_VOL = {'A': 100, 'B': 65, 'C': 35, 'D': 15}
CAPTURE = ['status', 'funding_lasts_until', 'reopens_on', 'how_to_apply', 'hours',
           'daily_cap', 'documents_required', 'most_common_turnaway', 'anything_changing',
           'spoke_with', 'verify_outcome', 'note', 'called_at', 'va']

def main(listings, geo, out, program_filter, limit):
    pop = {}
    for r in csv.DictReader(open(f'{geo}/counties.csv', encoding='utf-8')):
        pop[r['name'].replace(' County', '')] = int(r['population'] or 0)
    # ZIP population, when loaded, is the same basis rebuild_queue uses -- so the
    # sheet and the database rank identically instead of drifting apart.
    zpop = {r['zip']: int(r['population'] or 0)
            for r in csv.DictReader(open(f'{geo}/zips.csv', encoding='utf-8'))
            if (r['population'] or '').strip()}

    rows = []
    for line in open(listings, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if program_filter and program_filter.lower() not in r['program_name'].lower():
            continue
        reach_pop = (sum(zpop.get(z, 0) for z in r['service_zips'])
                     if zpop else sum(pop.get(c, 0) for c in r['service_counties']))
        # log-normalised exactly as docs/03-database.md rebuild_queue does
        reach = min(100, 100 * math.log(1 + reach_pop) / math.log(1 + 8_000_000))
        vol = TIER_VOL[r['volatility_tier']]
        # cold start: staleness/demand null, contactability full
        score = 0.30 * reach + 0.25 * vol + 0.05 * 100
        top = sorted(r['service_counties'], key=lambda c: -pop.get(c, 0))[:3]
        rows.append({
            'score': round(score, 2), 'reach': round(reach, 1),
            'org_name': r['org_name'], 'program': r['program_name'],
            'phone': r['phone'] or '', 'city': r['city'] or '',
            'counties': len(r['service_counties']),
            'population_reach': reach_pop,
            'largest_counties': ', '.join(top),
            'zips': len(r['service_zips']),
            'source_url': r['source_url'],
            'needs_source_verification': r['needs_source_verification'],
        })

    rows.sort(key=lambda r: -r['score'])
    if limit:
        rows = rows[:limit]
    for i, r in enumerate(rows, 1):
        r['rank'] = i

    cols = (['rank', 'score', 'org_name', 'program', 'phone', 'city', 'counties',
             'population_reach', 'largest_counties', 'zips', 'reach'] + CAPTURE +
            ['source_url', 'needs_source_verification'])
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({**{c: '' for c in CAPTURE}, **r})

    print(f'{len(rows)} calls -> {out}')
    print(f'population reach of the whole sheet: {sum(r["population_reach"] for r in rows):,} '
          '(counties counted once per provider; providers overlap)')
    print('\ntop 10 by cold-start score:')
    print(f'{"":>3}  {"score":>6}  {"pop reach":>11}  {"cty":>3}  org')
    for r in rows[:10]:
        print(f'{r["rank"]:>3}  {r["score"]:>6}  {r["population_reach"]:>11,}  '
              f'{r["counties"]:>3}  {r["org_name"][:52]}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--listings', default='data/listings/tdhca-subrecipients.jsonl')
    ap.add_argument('--geo', default='data/geo')
    ap.add_argument('--out', default='data/call-sheets/week-01-ceap.csv')
    ap.add_argument('--program', default='CEAP')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    import pathlib; pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    main(a.listings, a.geo, a.out, a.program, a.limit)
