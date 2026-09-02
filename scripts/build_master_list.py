#!/usr/bin/env python3
"""Master provider list — one row per organization, with counties and ZIPs served.

One call covers all of an organization's programs, so the organization is the row.
Counties come from the source; ZIPs are the crosswalk expansion (HUD, res_ratio
thresholded in expand_zips.py) and are the field the site actually searches on.

  python3 scripts/build_master_list.py
"""
import json, csv, collections, argparse, pathlib

CODE = {'Comprehensive Energy Assistance Program (CEAP)': 'CEAP',
        'Community Services Block Grant (CSBG)': 'CSBG',
        'Weatherization Assistance Program (WAP)': 'WAP'}
ORDER = {'CEAP': 0, 'CSBG': 1, 'WAP': 2}


def main(listings, geo, out):
    pop = {r['name'].replace(' County', ''): int(r['population'] or 0)
           for r in csv.DictReader(open(f'{geo}/counties.csv', encoding='utf-8'))}
    zpop = {r['zip']: int(r['population']) for r in
            csv.DictReader(open(f'{geo}/zips.csv', encoding='utf-8'))
            if (r['population'] or '').strip()}

    orgs = collections.OrderedDict()
    for line in open(listings, encoding='utf-8'):
        if not line.strip():
            continue
        r = json.loads(line)
        o = orgs.setdefault(r['org_name'], {'city': r['city'], 'phone': r['phone'],
                                            'programs': set(), 'counties': set(), 'zips': set()})
        o['programs'].add(CODE.get(r['program_name'], r['program_name']))
        o['counties'] |= set(r['service_counties'])
        o['zips'] |= set(r['service_zips'])

    rows = []
    for name, o in orgs.items():
        cs, zs = sorted(o['counties']), sorted(o['zips'])
        rows.append({
            'org_name': name, 'city': o['city'], 'phone': o['phone'],
            'programs': ', '.join(sorted(o['programs'], key=lambda p: ORDER.get(p, 9))),
            'counties_count': len(cs), 'zips_count': len(zs),
            'population_reach': sum(zpop.get(z, 0) for z in zs) or sum(pop.get(c, 0) for c in cs),
            'counties': '; '.join(cs),
            'zips': ' '.join(zs),
        })
    rows.sort(key=lambda r: -r['population_reach'])
    for i, r in enumerate(rows, 1):
        r['rank'] = i

    cols = ['rank', 'org_name', 'city', 'phone', 'programs', 'counties_count', 'zips_count',
            'population_reach', 'counties', 'zips']
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows([{k: r[k] for k in cols} for r in rows])

    allz = set().union(*[o['zips'] for o in orgs.values()])
    allc = set().union(*[o['counties'] for o in orgs.values()])
    print(f'{len(rows)} organizations -> {out}')
    print(f'{len(allc)} counties · {len(allz):,} ZIP codes covered')
    print(f'longest ZIP list: {max(r["zips_count"] for r in rows)} ZIPs '
          f'({max(rows, key=lambda r: r["zips_count"])["org_name"]})')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--listings', default='data/listings/tdhca-subrecipients.jsonl')
    ap.add_argument('--geo', default='data/geo')
    ap.add_argument('--out', default='data/call-sheets/master-provider-list.csv')
    a = ap.parse_args()
    main(a.listings, a.geo, a.out)
