#!/usr/bin/env python3
"""Expand service_counties -> service_zips via the ZIP-county junction.

docs/02-data-model.md: service_zips is authoritative, service_counties is derived
for display and SEO only. Sources give us counties, so the expansion happens here
and is recorded with geo_derivation='crosswalk_expanded'.

--min-ratio drops marginal ZIP-county pairs so a program serving one county does not
surface on a neighbouring county's page because a ZIP clips the line. It filters on
res_ratio (HUD, share of a ZIP's residential addresses) when present, falling back to
area_ratio (Census land overlap) otherwise.

Default is 0.05. Measured on Texas: 19.4% of ZIP-county pairs carry under 5% of the
ZIP's residents, and the threshold drops 1,179 of 10,194 program-ZIP pairs (11.6%)
without leaving any program with zero ZIPs.
"""
import csv, json, argparse, pathlib, collections

def main(listings, geo, out, min_ratio):
    # Keyed on (STATE, county). County names are not unique across states -- there
    # is a Caldwell, a Cherokee, a Clay, a Franklin, a Henderson and a Jackson
    # County in both Texas and North Carolina. Keying on the name alone silently
    # gave every North Carolina office a set of Texas ZIP codes, because whichever
    # state loaded last won. Every listing must declare its state.
    counties = {}
    for r in csv.DictReader(open(f'{geo}/counties.csv', encoding='utf-8')):
        st, name = r['state'], r['name']
        counties[(st, name)] = r['county_fips']
        # sources say "Harris"; the relationship file says "Harris County"
        counties[(st, name.replace(' County', ''))] = r['county_fips']

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
        st = r.get('state')
        if not st:
            raise SystemExit(
                f"listing {r.get('slug')} has no state. Refusing to expand ZIPs: a "
                f"bare county name is ambiguous across states.")
        zips = set()
        for c in r['service_counties']:
            f = counties.get((st, c))
            if not f:
                unmatched[f'{c} ({st})'] += 1
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
    ap.add_argument('--min-ratio', type=float, default=0.05)
    a = ap.parse_args()
    main(a.listings, a.geo, a.out, a.min_ratio)
