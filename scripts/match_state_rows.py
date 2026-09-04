#!/usr/bin/env python3
"""The 478 pasted FL/NC sheet rows vs the state-published directories.

Answers one question: which of these rows can be given a source, and which
cannot. A row that matches an official record inherits that record's
provenance. A row that does not stays a LEAD -- it may still be a real
organization, but nothing publishes on our say-so.
"""
import csv, re, collections, unicodedata, json, pathlib

def norm(s):
    s = unicodedata.normalize('NFKD', s or '').lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def digits(s):
    return re.sub(r'\D', '', s or '')[-10:]

sheet = list(csv.reader(open('data/sources/master-sheet-export-2026-09-04.csv')))
hdr = [c.strip() for c in sheet[2]]
rows = [dict(zip(hdr, r)) for r in sheet[3:] if any(c.strip() for c in r)]
pasted = rows[99:]

nc = list(csv.DictReader(open('data/sources/nc-county-dss.psv'), delimiter='|'))
fl = list(csv.DictReader(open('data/sources/fl-liheap-providers.psv'), delimiter='|'))
nc_by_county = {norm(r['county']): r for r in nc}
fl_by_county = collections.defaultdict(list)
for r in fl:
    fl_by_county[norm(r['county'])].append(r)

# placeholder text is the tell that a cell was written by a model, not extracted
PLACEHOLDER = re.compile(r'\b(varies|verify|confirm current|confirm .*intake|tbd|n/?a)\b', re.I)

out = []
for r in pasted:
    org, addr, city = r['Organization'], r['Address'], r['City']
    county_cell = r['Counties served']
    blob = f'{org} {addr} {city}'
    state = 'NC' if re.search(r'\bNC\b', blob) else ('FL' if re.search(r'\bFL\b', blob) else '')
    county = re.sub(r'\s*county\s*$', '', norm(county_cell))
    rec = {'org': org, 'city': city, 'addr': addr, 'phone': r['Phone'],
           'county': county_cell, 'help': r['Help offered'],
           'placeholder': bool(PLACEHOLDER.search(f'{addr} {city}')),
           'state': state, 'verdict': '', 'matched_to': '', 'source_url': ''}

    # NC: "<County> County DSS — <program>" against the NCDHHS directory
    m = re.match(r'(.+?)\s+County\s+DSS', org)
    if m and norm(m.group(1)) in nc_by_county:
        off = nc_by_county[norm(m.group(1))]
        rec['state'] = 'NC'
        same_phone = digits(r['Phone']) and digits(r['Phone']) == digits(off['phone'])
        rec['verdict'] = 'matched' if same_phone else 'matched_phone_differs'
        rec['matched_to'] = off['org_name']; rec['source_url'] = off['source_url']
        rec['official_phone'] = off['phone']; rec['official_addr'] = off['address']
        out.append(rec); continue

    # FL: agency name against the FloridaCommerce provider for that county.
    # Substring alone is too strict -- the sheet writes the same agency as
    # "LIHEAP - Charlotte County Human Services" where the state writes
    # "Charlotte County Dept. of Human Services". Score on shared significant
    # words instead, and require the phone to agree OR a strong name overlap.
    STOP = {'county','of','the','and','inc','department','dept','program',
            'programs','services','service','agency','assistance','community',
            'florida','liheap','low','income','home','energy'}
    def sig(s):
        return {w for w in norm(s).split() if w not in STOP and len(w) > 2}
    hit, best = None, 0.0
    for cand in fl_by_county.get(county, []):
        a, b = sig(cand['org_name']), sig(org)
        if not a:
            continue
        overlap = len(a & b) / len(a)
        if digits(r['Phone']) and digits(r['Phone']) == digits(cand['phone']):
            overlap = max(overlap, 1.0)
        # a bare "LIHEAP - <county>" row names no agency but is unambiguous:
        # the state publishes exactly one LIHEAP provider per county
        if not b and re.search(r'liheap', org, re.I) and len(fl_by_county[county]) == 1:
            overlap = max(overlap, 0.6)
        if overlap > best:
            hit, best = cand, overlap
    if best < 0.5:
        hit = None
    if hit:
        rec['state'] = 'FL'; rec['verdict'] = 'matched'
        rec['matched_to'] = hit['org_name']; rec['source_url'] = hit['source_url']
        rec['official_phone'] = hit['phone']; rec['official_addr'] = ''
    else:
        rec['verdict'] = 'placeholder' if rec['placeholder'] else 'unmatched'
    out.append(rec)

pathlib.Path('data/sources/pasted-rows-audit.json').write_text(json.dumps(out, indent=1))

v = collections.Counter(r['verdict'] for r in out)
byst = collections.Counter((r['state'] or '?', r['verdict']) for r in out)
print(f'{len(out)} pasted rows\n')
for k, n in v.most_common():
    print(f'  {k:24} {n:4}')
print('\nby state:')
for (s, k), n in sorted(byst.items()):
    print(f'  {s or "?":3} {k:24} {n:4}')

nc_seen = {r['matched_to'] for r in out if r['state'] == 'NC' and r['matched_to']}
fl_seen = {r['matched_to'] for r in out if r['state'] == 'FL' and r['matched_to']}
print(f'\nNC offices covered by the sheet: {len(nc_seen)} of 100')
print(f'FL LIHEAP agencies covered by the sheet: {len(fl_seen)} of '
      f'{len({r["org_name"] for r in fl})}')
missing_nc = sorted({r['county'] for r in nc} - {n.split(' County')[0] for n in nc_seen})
print(f'NC counties with NO row in the sheet ({len(missing_nc)}):', ', '.join(missing_nc[:40]))
