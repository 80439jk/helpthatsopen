#!/usr/bin/env python3
"""The NC + FL replacement block for the master call sheet, and the leads file.

Emits two CSVs:

  nc-fl-sheet-block.csv   one row per ORGANIZATION, in the master sheet's own
                          column order, carrying slug and rent slug so calls can
                          import. Capture columns are left empty -- these have
                          never been called.

  unsourced-leads.csv     every pasted row that could not be matched to a state
                          directory. NOT deleted and NOT listed: kept verbatim
                          with the reason, because several are real
                          organizations (ABCCM, Burke United Christian
                          Ministries) that simply need their own source.
"""
import csv, json, glob, collections, pathlib

HDR = ['WEEK 1', '#', 'Organization', 'City', 'Address', 'Phone', 'Programs',
       'Help offered', 'Counties', 'ZIPs', 'People reached', 'Counties served',
       'ZIP codes served', 'Source', 'slug — do not edit', 'rent slug — do not edit',
       'Status', 'Rent status', 'SERVICE AREA — whole county? which areas?',
       'Funding lasts until', 'Reopens on', 'How to apply', 'Hours', 'Daily cap',
       'Documents required', 'Most common reason turned away', 'Anything changing',
       'Spoke with', 'Call outcome', 'Note', 'Called (date)', 'VA']

recs = {}
for f in ('nc-county-dss', 'fl-liheap-providers'):
    for line in open(f'data/listings/{f}.jsonl'):
        r = json.loads(line)
        recs[r['slug']] = r
byorg = collections.defaultdict(list)
for r in recs.values():
    byorg[r['org_name']].append(r)

smap = {r['org_name']: r for r in csv.DictReader(open('data/slug_map.csv'))}
pop = {(r['state'], r['name']): int(r['population'] or 0)
       for r in csv.DictReader(open('data/geo/counties.csv'))}

rows, n = [], 0
for org in sorted(byorg):
    if org not in smap:
        continue
    progs = byorg[org]
    m = smap[org]
    primary = recs[m['slug']]
    counties = sorted({c for p in progs for c in p['service_counties']})
    zips = sorted({z for p in progs for z in p['service_zips']})
    tags = sorted({t for p in progs for t in p['need_tags']})
    n += 1
    rows.append({
        'WEEK 1': '', '#': n, 'Organization': org,
        'City': primary.get('city') or '', 'Address': primary.get('address') or '',
        'Phone': primary.get('phone') or '',
        'Programs': '; '.join(sorted({p['program_name'] for p in progs})),
        'Help offered': ', '.join(tags),
        'Counties': len(counties), 'ZIPs': len(zips),
        'People reached': f"{sum(pop.get((primary['state'], c + ' County'), 0) for c in counties):,}",
        'Counties served': '; '.join(counties),
        'ZIP codes served': ' '.join(zips),
        'Source': primary['source_name'],
        'slug — do not edit': m['slug'],
        'rent slug — do not edit': m['rent_slug'],
    })

out = pathlib.Path('data/call-sheets/nc-fl-sheet-block.csv')
with out.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=HDR); w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in HDR})
print(f'{out}: {len(rows)} organizations')

audit = json.load(open('data/sources/pasted-rows-audit.json'))
leads = [a for a in audit if a['verdict'] in ('unmatched', 'placeholder')]
lp = pathlib.Path('data/call-sheets/unsourced-leads.csv')
with lp.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['Organization', 'City', 'Address', 'Phone',
                                      'Counties served', 'Help offered', 'State', 'Why not listed'])
    w.writeheader()
    for a in leads:
        w.writerow({'Organization': a['org'], 'City': a['city'], 'Address': a['addr'],
                    'Phone': a['phone'], 'Counties served': a['county'],
                    'Help offered': a['help'], 'State': a['state'],
                    'Why not listed': 'placeholder text in address/city — not a real record'
                    if a['verdict'] == 'placeholder'
                    else 'no match in the state directory — needs its own cited source'})
print(f'{lp}: {len(leads)} leads held back')
