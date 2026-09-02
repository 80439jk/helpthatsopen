#!/usr/bin/env python3
"""ZCTA population -> data/geo/zips.csv.

Fills the population column left null by ingest_geo.py. This is the `reach`
component of the verification priority score (docs/02-data-model.md section 6).
Without it, reach falls back to county population and cannot distinguish two
providers inside the same county -- fine for 119 records, wrong once ranking
pantries against each other inside Harris.

ZCTAs cross state lines, so the API is queried nationally and filtered against the
ZCTAs already in zips.csv.

Auth: CENSUS_API_KEY from the environment or .env. Never printed; .env is gitignored.

  python3 scripts/ingest_zcta_population.py
"""
import csv, json, os, sys, argparse, pathlib, urllib.request, urllib.error

# tried in order; the first that responds wins
DATASETS = [
    ('2020/dec/dhc',  'P1_001N',      '2020 Decennial DHC'),
    ('2020/dec/pl',   'P1_001N',      '2020 Decennial PL 94-171'),
    ('2023/acs/acs5', 'B01003_001E',  'ACS 5-year 2019-2023'),
    ('2022/acs/acs5', 'B01003_001E',  'ACS 5-year 2018-2022'),
]
GEO = 'zip%20code%20tabulation%20area:*'


def key():
    k = os.environ.get('CENSUS_API_KEY')
    if not k:
        env = pathlib.Path(__file__).resolve().parent.parent / '.env'
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith('CENSUS_API_KEY='):
                    k = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    if not k:
        sys.exit('No CENSUS_API_KEY. Append it to .env as CENSUS_API_KEY=... (gitignored).')
    return k


def try_dataset(ds, var, label, k):
    url = f'https://api.census.gov/data/{ds}?get=NAME,{var}&for={GEO}&key={k}'
    try:
        with urllib.request.urlopen(url, timeout=180) as r:
            body = r.read().decode()
    except urllib.error.HTTPError as e:
        return None, f'HTTP {e.code}'
    except Exception as e:                                   # noqa: BLE001
        return None, str(e)[:80]
    if not body.lstrip().startswith('['):
        return None, body.strip()[:80].replace('\n', ' ')
    try:
        return json.loads(body), None
    except json.JSONDecodeError as e:
        return None, f'bad JSON: {e}'


def main(geo):
    k = key()
    data = None
    for ds, var, label in DATASETS:
        print(f'trying {label} ...', end=' ', flush=True)
        data, err = try_dataset(ds, var, label, k)
        if data:
            print(f'ok, {len(data)-1:,} ZCTAs')
            source = label
            break
        print(f'no ({err})')
    if not data:
        sys.exit('No Census dataset returned ZCTA population. Key may be unactivated '
                 '(activation email) or every dataset changed shape.')

    hdr = data[0]
    vi = 1 if len(hdr) > 1 else 0
    zi = len(hdr) - 1                                        # geography is the last column
    popn = {}
    for row in data[1:]:
        z = str(row[zi]).zfill(5)
        try:
            v = int(row[vi])
        except (TypeError, ValueError):
            continue
        if v >= 0:
            popn[z] = v

    path = pathlib.Path(geo) / 'zips.csv'
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    filled = 0
    for r in rows:
        v = popn.get(r['zip'])
        if v is not None:
            r['population'] = v
            filled += 1
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['zip', 'primary_state', 'population'])
        w.writeheader(); w.writerows(rows)

    tot = sum(int(r['population']) for r in rows if str(r['population']).strip())
    print(f'\nsource: {source}')
    print(f'filled {filled:,} of {len(rows):,} ZCTAs')
    print(f'total population across them: {tot:,}')
    if filled < len(rows):
        print(f'{len(rows)-filled:,} ZCTAs absent from the Census response '
              '(zero-population or retired ZCTAs)')
    print('\nNext: reload the DB (db/load_seed.py) so reach recomputes at ZIP granularity.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--geo', default='data/geo')
    main(ap.parse_args().geo)
