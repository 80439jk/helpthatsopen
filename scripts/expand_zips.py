#!/usr/bin/env python3
"""Expand service_counties -> service_zips via the ZIP-county junction.

docs/02-data-model.md: service_zips is authoritative, service_counties is derived
for display and SEO only. Sources give us counties, so the expansion happens here
and is recorded with geo_derivation='crosswalk_expanded'.

--min-ratio drops marginal ZIP-county pairs so a program serving one county does not
surface on a neighbouring county's page because a ZIP clips the line. It filters on
res_ratio when present and falls back to area_ratio, which is a weaker signal --
see scripts/ingest_geo.py. Default 0.0 keeps every pair; raise it once res_ratio
is populated from the HUD crosswalk.
"""
import csv, json, argparse, pathlib, collections

def main(listings, geo, out, min_ratio):
    counties = {r['name']: r['county_fips']
                for r in csv.DictReader(open(f'{geo}/counties.csv', encoding='utf-8'))}
    # sources say "Harris"; the relationship file says "Harris County"
    byshort = {n.replace(' County', ''): f for n, f in counties.items()}

    fips_zips = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{geo}/zip_counties.csv', encoding='utf-8')):
        ratio = r['res_ratio'] or r['area_ratio'] or 0
        try:
            ratio = float(ratio)
        except ValueError:
            ratio = 0.0
        if ratio >= min_ratio:
            fips_zips[r['county_fips']].append(r['zip'])

    rows, unmatched = [], collections.Counter()
    for line in open(listings, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        zips = set()
        for c in r['service_counties']:
            f = byshort.get(c) or counties.get(c)
            if not f:
                unmatched[c] += 1
                continue
            zips |= set(fips_zips.get(f, []))
        r['service_zips'] = sorted(zips)
        r['geo_derivation'] = 'crosswalk_expanded'
        rows.append(r)

    with open(out, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    tot = sum(len(r['service_zips']) for r in rows)
    print(f'{len(rows)} rows -> {out}')
    print(f'{tot:,} program-ZIP pairs; mean {tot/len(rows):.0f} ZIPs per program')
    print(f'programs with zero ZIPs: {sum(1 for r in rows if not r["service_zips"])}')
    if unmatched:
        print(f'UNMATCHED county names (fix before import): {dict(unmatched)}')
    else:
        print('every county name matched the canonical list')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--listings', default='data/listings/tdhca-subrecipients.jsonl')
    ap.add_argument('--geo', default='data/geo')
    ap.add_argument('--out', default='data/listings/tdhca-subrecipients.jsonl')
    ap.add_argument('--min-ratio', type=float, default=0.0)
    a = ap.parse_args()
    main(a.listings, a.geo, a.out, a.min_ratio)
