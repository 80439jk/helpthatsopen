#!/usr/bin/env python3
"""Geography layer: counties, ZCTAs, and the ZIP-county junction.

Sources (both public, no API key):
  - Census 2020 ZCTA-to-county relationship file
    https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt
  - Census county population estimates (vintage 2024)
    https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv

IMPORTANT — area_ratio is not res_ratio.
docs/02-data-model.md and data/SOURCES.md call for HUD's USPS crosswalk, whose
res_ratio is the share of a ZIP's *households* falling in each county. The Census
relationship file gives only *land area* overlap, which this script emits as
`area_ratio`. They are not interchangeable: a ZIP that spans a county line mostly
across empty ranchland looks significant by area and negligible by households.

Use area_ratio only as an interim. Get a HUD USPS Crosswalk API token (free) and
replace this column before any county-page inclusion threshold depends on it.

ZCTA population is left null: it needs a Census API key. County population is
populated and is enough to rank the verification queue by reach at county
granularity until then.
"""
import csv, io, re, sys, urllib.request, pathlib, argparse

REL_URL = ('https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/'
           'tab20_zcta520_county20_natl.txt')
POP_URL = ('https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/'
           'counties/totals/co-est2024-alldata.csv')

STATE_FIPS = {'48': 'TX'}   # extend as markets are added; nothing here is TX-specific


def fetch(url, cache):
    p = pathlib.Path(cache)
    if p.exists():
        print(f'  cached {p.name} ({p.stat().st_size:,} bytes)')
        return p.read_text(encoding='utf-8-sig', errors='replace')
    print(f'  downloading {url.rsplit("/",1)[-1]} ...')
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    print(f'  saved {p.name} ({len(data):,} bytes)')
    return data.decode('utf-8-sig', errors='replace')


def slugify(name):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', name.lower())).strip('-')


def main(states, outdir, cachedir):
    out = pathlib.Path(outdir); out.mkdir(parents=True, exist_ok=True)

    print('geography sources:')
    rel = list(csv.DictReader(io.StringIO(fetch(REL_URL, f'{cachedir}/zcta_county_rel.txt')),
                              delimiter='|'))
    pop = list(csv.DictReader(io.StringIO(fetch(POP_URL, f'{cachedir}/county_pop.csv'))))

    # county population, keyed by 5-digit FIPS
    cpop = {}
    for r in pop:
        if r.get('SUMLEV') != '050':
            continue
        cpop[f"{int(r['STATE']):02d}{int(r['COUNTY']):03d}"] = int(r['POPESTIMATE2024'])

    counties, pairs, zips = {}, [], {}
    for r in rel:
        z = (r.get('GEOID_ZCTA5_20') or '').strip()
        cf = (r.get('GEOID_COUNTY_20') or '').strip()
        if not z or not cf or cf[:2] not in states:
            continue
        st = states[cf[:2]]

        name = (r.get('NAMELSAD_COUNTY_20') or '').strip()
        counties[cf] = {'county_fips': cf, 'name': name, 'state': st,
                        'slug': slugify(name), 'population': cpop.get(cf, '')}
        zips.setdefault(z, {'zip': z, 'primary_state': st, 'population': ''})

        try:
            part = float(r.get('AREALAND_PART') or 0)
            whole = float(r.get('AREALAND_ZCTA5_20') or 0)
            ratio = round(part / whole, 4) if whole else ''
        except ValueError:
            ratio = ''
        pairs.append({'zip': z, 'county_fips': cf, 'area_ratio': ratio, 'res_ratio': ''})

    def write(fn, rows, cols):
        with open(out / fn, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
        print(f'  {len(rows):>6,} -> {out/fn}')

    print('\nwriting:')
    write('counties.csv', sorted(counties.values(), key=lambda r: r['county_fips']),
          ['county_fips', 'name', 'state', 'slug', 'population'])
    write('zips.csv', sorted(zips.values(), key=lambda r: r['zip']),
          ['zip', 'primary_state', 'population'])
    write('zip_counties.csv', sorted(pairs, key=lambda r: (r['zip'], r['county_fips'])),
          ['zip', 'county_fips', 'area_ratio', 'res_ratio'])

    from collections import Counter
    c = Counter(p['zip'] for p in pairs)
    multi = sum(1 for v in c.values() if v > 1)
    missing = [f for f, v in counties.items() if v['population'] == '']
    print(f'\n  {len(counties)} counties, {len(zips)} ZCTAs, {len(pairs)} pairs')
    print(f'  {multi} ZCTAs span more than one county ({100*multi/len(c):.1f}%) '
          f'— this is why service area is ZIP-level, not county-level')
    if missing:
        print(f'  WARNING: {len(missing)} counties without population: {missing[:5]}')
    print('  res_ratio column is empty by design — needs the HUD crosswalk (see docstring)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--states', default='48', help='comma-separated state FIPS, e.g. 48,12')
    ap.add_argument('--out', default='data/geo')
    ap.add_argument('--cache', default='data/sources/census')
    a = ap.parse_args()
    sel = {s.strip(): STATE_FIPS.get(s.strip(), s.strip()) for s in a.states.split(',')}
    main(sel, a.out, a.cache)
