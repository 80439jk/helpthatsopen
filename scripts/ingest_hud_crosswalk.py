#!/usr/bin/env python3
"""HUD USPS ZIP-County crosswalk -> data/geo/zips.csv and data/geo/zip_counties.csv.

HUD is the AUTHORITY for which ZIP codes exist. The Census ZCTA file that seeds
counties.csv is not a ZIP list: ZCTAs are statistical areas built from census
blocks, so they omit PO-box-only and single-building ZIPs. Texas has 2,433
deliverable ZIPs and 1,992 ZCTAs — using ZCTAs meant 448 real ZIPs (18.4%) could
not be resolved at all when a visitor typed one in.

HUD also supplies res_ratio, the share of a ZIP's RESIDENTIAL addresses in each
county, which is what the county-page inclusion threshold needs. The Census file
gives land-area overlap, which over-weights rural ZIPs crossing a county line
across empty acreage.

ZIP population comes from ZCTA population where the ZIP matches a ZCTA. The extra
HUD ZIPs are largely PO-box and single-building and carry little or no residential
population, so their population is left null rather than estimated.

Auth: HUD_API_TOKEN from the environment or .env. Never printed; .env is gitignored.

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
        with urllib.request.urlopen(req, timeout=180) as r:
            payload = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f'HUD API {e.code}: {e.read().decode()[:300]}\n'
                 '(401/403 = token; 400 = year/quarter not published yet)')
    node = payload.get('data', payload)
    rows = node.get('results') if isinstance(node, dict) else None
    if not isinstance(rows, list):
        sys.exit(f'Unexpected HUD response shape: {list(payload)[:8]}')
    return rows


def main(state, year, quarter, geo):
    rows = fetch(state, year, quarter, token())
    print(f'HUD {state} {year}Q{quarter}: {len(rows):,} ZIP-county pairs')

    gd = pathlib.Path(geo)
    # existing area_ratio (Census) and ZCTA population, to carry across where available
    area = {}
    old_zc = gd / 'zip_counties.csv'
    if old_zc.exists():
        for r in csv.DictReader(open(old_zc, encoding='utf-8')):
            if r.get('area_ratio'):
                area[(r['zip'], r['county_fips'])] = r['area_ratio']
    zpop = {}
    old_z = gd / 'zips.csv'
    if old_z.exists():
        for r in csv.DictReader(open(old_z, encoding='utf-8')):
            if (r.get('population') or '').strip():
                zpop[r['zip']] = r['population']

    pairs, zips = [], {}
    for r in rows:
        z = str(r.get('zip', '')).zfill(5)
        fips = str(r.get('geoid') or '').zfill(5)
        if len(z) != 5 or len(fips) != 5:
            continue
        try:
            res = round(float(r.get('res_ratio', 0)), 4)
        except (TypeError, ValueError):
            res = ''
        pairs.append({'zip': z, 'county_fips': fips, 'area_ratio': area.get((z, fips), ''),
                      'res_ratio': res})
        zips.setdefault(z, {'zip': z, 'primary_state': r.get('state') or state,
                            'population': zpop.get(z, '')})

    with open(gd / 'zips.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['zip', 'primary_state', 'population'])
        w.writeheader(); w.writerows(sorted(zips.values(), key=lambda r: r['zip']))
    with open(gd / 'zip_counties.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['zip', 'county_fips', 'area_ratio', 'res_ratio'])
        w.writeheader(); w.writerows(sorted(pairs, key=lambda r: (r['zip'], r['county_fips'])))

    withpop = sum(1 for v in zips.values() if str(v['population']).strip())
    print(f'  {len(zips):,} ZIP codes -> {gd/"zips.csv"}   ({withpop:,} with population)')
    print(f'  {len(pairs):,} ZIP-county pairs -> {gd/"zip_counties.csv"}')
    print(f'  {len(pairs)-len(zips):,} ZIPs span more than one county')
    for t in (0.01, 0.05, 0.10):
        n = sum(1 for p in pairs if p['res_ratio'] != '' and float(p['res_ratio']) < t)
        print(f'  pairs below res_ratio {t:.0%}: {n:,}')
    print('\nNext: scripts/expand_zips.py, then scripts/build_call_list.py')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', default='TX')
    ap.add_argument('--year', type=int, default=2025)
    ap.add_argument('--quarter', type=int, default=4)
    ap.add_argument('--geo', default='data/geo')
    a = ap.parse_args()
    main(a.state, a.year, a.quarter, a.geo)
