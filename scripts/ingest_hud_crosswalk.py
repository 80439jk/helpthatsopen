#!/usr/bin/env python3
"""HUD USPS ZIP-County crosswalk -> res_ratio on data/geo/zip_counties.csv.

res_ratio is the share of a ZIP's RESIDENTIAL ADDRESSES falling in each county.
That is the number the county-page inclusion threshold needs. The Census
relationship file used by ingest_geo.py gives land-area overlap only, which
over-weights rural ZIPs that cross a county line across empty acreage.

Auth: reads HUD_API_TOKEN from the environment or from .env in the repo root.
The token is never printed and .env is gitignored.

  python3 scripts/ingest_hud_crosswalk.py --state TX
"""
import csv, json, os, sys, argparse, pathlib, urllib.request, urllib.error

API = 'https://www.huduser.gov/hudapi/public/usps'
TYPE_ZIP_COUNTY = 2


def token():
    t = os.environ.get('HUD_API_TOKEN')
    if not t:
        env = pathlib.Path(__file__).resolve().parent.parent / '.env'
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith('HUD_API_TOKEN='):
                    t = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    if not t:
        sys.exit('No HUD_API_TOKEN. Put it in .env as HUD_API_TOKEN=... (gitignored).')
    return t


def fetch(state, year, quarter, tok):
    url = f'{API}?type={TYPE_ZIP_COUNTY}&query={state}&year={year}&quarter={quarter}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {tok}'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        sys.exit(f'HUD API {e.code}: {body}\n(401/403 = token problem; 400 = bad year/quarter)')


def results(payload):
    """HUD nests results under data.results; tolerate shape drift."""
    if isinstance(payload, dict):
        for path in (('data', 'results'), ('results',)):
            node = payload
            for k in path:
                node = node.get(k) if isinstance(node, dict) else None
                if node is None:
                    break
            if isinstance(node, list):
                return node
    sys.exit(f'Unexpected HUD response shape. Top-level keys: '
             f'{list(payload)[:10] if isinstance(payload, dict) else type(payload)}')


def main(state, year, quarter, geo):
    rows = results(fetch(state, year, quarter, token()))
    print(f'HUD returned {len(rows):,} ZIP-county pairs for {state} {year}Q{quarter}')
    if rows:
        print(f'  fields: {sorted(rows[0])}')

    hud = {}
    for r in rows:
        z = str(r.get('zip', '')).zfill(5)
        fips = str(r.get('geoid') or r.get('county') or '').zfill(5)
        try:
            hud[(z, fips)] = round(float(r.get('res_ratio', 0)), 4)
        except (TypeError, ValueError):
            pass

    path = pathlib.Path(geo) / 'zip_counties.csv'
    existing = list(csv.DictReader(open(path, encoding='utf-8')))
    filled = missing = 0
    for r in existing:
        v = hud.get((r['zip'], r['county_fips']))
        if v is None:
            missing += 1
        else:
            r['res_ratio'] = v
            filled += 1
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['zip', 'county_fips', 'area_ratio', 'res_ratio'])
        w.writeheader()
        w.writerows([{k: r.get(k, '') for k in w.fieldnames} for r in existing])

    only_hud = set(hud) - {(r['zip'], r['county_fips']) for r in existing}
    print(f'  res_ratio filled: {filled:,} of {len(existing):,} pairs')
    if missing:
        print(f'  {missing:,} pairs HUD does not list (ZCTAs with no residential addresses)')
    if only_hud:
        print(f'  {len(only_hud):,} HUD pairs absent from the Census file (ZIP vs ZCTA differ)')

    # how much would a threshold actually drop?
    for t in (0.01, 0.05, 0.10):
        n = sum(1 for r in existing if r['res_ratio'] not in ('', None)
                and float(r['res_ratio']) < t)
        print(f'  pairs below res_ratio {t:.0%}: {n:,}  '
              f'({100*n/max(filled,1):.1f}% of filled)')
    print('\nNext: re-run scripts/expand_zips.py --min-ratio 0.05 to apply a threshold.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', default='TX')
    ap.add_argument('--year', type=int, default=2025)
    ap.add_argument('--quarter', type=int, default=4)
    ap.add_argument('--geo', default='data/geo')
    a = ap.parse_args()
    main(a.state, a.year, a.quarter, a.geo)
