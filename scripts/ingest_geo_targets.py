#!/usr/bin/env python3
"""Google Ads geo target IDs -> our states, counties and ZIPs.

Google's location targeting reports what it matched as a numeric criteria ID in
{loc_interest_ms} and {loc_physical_ms}. Resolving one needs Google's published
geo targets table. This maps every US state, county and postal-code target to a
record we already hold, so a landing page can answer "where is this click" from
Google's own signal instead of guessing from an IP.

Why this matters: MaxMind, who sell IP geolocation, publish city-level accuracy
of 20-75% and no postal-code figure at all, and say mobile "typically resolves
to a broad region". Google is working from device location and the words in the
search. It is a different quality of signal, and it is free.

Postal Code targets exist for 33,371 US ZIPs, which is better than expected --
a click can resolve straight to a ZIP page with no interstitial.

  python3 scripts/ingest_geo_targets.py --csv data/sources/google/geotargets-YYYY-MM-DD.csv
"""
import csv, sys, argparse, collections, pathlib

SRC = ('https://developers.google.com/google-ads/api/data/geotargets')

def load_ours(geo):
    counties, states = {}, {}
    for r in csv.DictReader(open(f'{geo}/counties.csv', encoding='utf-8')):
        counties[(r['state'], r['name'].lower())] = r['county_fips']
        states.setdefault(r['state'], set()).add(r['county_fips'])
    zips = {r['zip'] for r in csv.DictReader(open(f'{geo}/zips.csv', encoding='utf-8'))}
    return counties, states, zips

STATE_NAME = {'Texas': 'TX', 'North Carolina': 'NC', 'Florida': 'FL'}

def main(csv_path, geo, out):
    counties, states, zips = load_ours(geo)
    rows, seen = [], collections.Counter()
    for r in csv.DictReader(open(csv_path, encoding='utf-8-sig')):
        if r['Country Code'] != 'US' or r['Status'] != 'Active':
            continue
        t, cid, name = r['Target Type'], r['Criteria ID'], r['Name']
        canon = r['Canonical Name'].split(',')
        # "Dallas County,Texas,United States" -> state is the second-to-last part
        st_name = canon[-2] if len(canon) >= 3 else (canon[0] if canon else '')
        st = STATE_NAME.get(st_name if t != 'State' else name)
        if not st:
            continue                       # a market we do not cover

        if t == 'State':
            rows.append({'criteria_id': cid, 'kind': 'state', 'state': st,
                         'county_fips': '', 'zip': '', 'label': name})
        elif t == 'County':
            fips = counties.get((st, name.lower()))
            if not fips:
                seen['county miss'] += 1
                continue
            rows.append({'criteria_id': cid, 'kind': 'county', 'state': st,
                         'county_fips': fips, 'zip': '', 'label': f'{name}, {st}'})
        elif t == 'Postal Code':
            if name not in zips:
                seen['zip not in our geography'] += 1
                continue
            rows.append({'criteria_id': cid, 'kind': 'zip', 'state': st,
                         'county_fips': '', 'zip': name, 'label': f'ZIP {name}'})
        else:
            continue
        seen[t] += 1

    p = pathlib.Path(out)
    with p.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['criteria_id', 'kind', 'state',
                                          'county_fips', 'zip', 'label'])
        w.writeheader(); w.writerows(rows)
    print(f'{p}: {len(rows)} targets mapped')
    for k, n in seen.most_common():
        print(f'  {n:6}  {k}')
    print(f'\nsource: {SRC}\n{csv_path}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--geo', default='data/geo')
    ap.add_argument('--out', default='data/geo/google_geo_targets.csv')
    a = ap.parse_args()
    main(a.csv, a.geo, a.out)
