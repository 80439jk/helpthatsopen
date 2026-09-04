#!/usr/bin/env python3
"""NC county DSS + FL LIHEAP providers -> data/listings/*.jsonl.

Built from the two state-published directories parsed by
scripts/parse_state_directories.py, not from the rows that were pasted into the
call sheet. Those rows are audited separately; this is the sourced spine.

One record per PROGRAM, because status is a property of a funding pot, not of a
building. build_slug_map.py then picks each organization's primary (utility)
and rent records, so a caller still places one call per office.

NC, from NCDHHS:
  Energy Assistance (LIEAP / CIP)      utility pot  -> primary
  Work First Emergency Assistance      rent pot     -> second status cell
  Food and Nutrition Services (FNS)    SNAP, an entitlement -- listed so the
      office surfaces in a food search, but it carries no status light. "Are
      you open" is not a question about an entitlement.

FL, from FloridaCommerce: LIHEAP only. The state publishes one provider per
county and no street addresses, so address is null rather than invented.

extraction_method is structured_parse, not llm_*: both sources were machine
parsed from the state's own table, so needs_source_verification is false. That
is a stronger provenance than the Texas rows, which came out of a PDF.
"""
import csv, json, re, datetime, pathlib, collections

TODAY = datetime.date.today().isoformat()
OUT = pathlib.Path('data/listings')

def slugify(s):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower())
    return re.sub(r'^-|-$', '', s)

NC_PROGRAMS = [
    ('energy',    'Energy Assistance (LIEAP / CIP)',
     ['electric_bill', 'gas_bill', 'reconnect_fee', 'utility_deposit'], 'B'),
    ('emergency', 'Work First Emergency Assistance',
     ['rent_assistance', 'eviction_prevention'], 'C'),
    ('fns',       'Food and Nutrition Services (FNS)',
     ['snap_benefits'], 'D'),
]

def nc_records():
    rows = list(csv.DictReader(open('data/sources/nc-county-dss.psv'), delimiter='|'))
    out = []
    for r in rows:
        base = slugify(r['org_name'])
        city = ''
        m = re.search(r',\s*([A-Za-z .\'-]+),\s*NC\s*\d{5}', r['address'] or '')
        if m:
            city = m.group(1).strip()
        for key, pname, tags, tier in NC_PROGRAMS:
            out.append({
                'org_name': r['org_name'], 'program_name': pname, 'state': 'NC',
                'slug': f'{base}-{key}', 'org_type': 'government',
                'city': city or None, 'address': r['address'] or None,
                'phone': r['phone'] or None,
                'url': ('https://www.ncdhhs.gov' + r['url']
                        if r['url'].startswith('/') else r['url']) or None,
                'volatility_tier': tier,
                'need_tags': tags, 'service_counties': [r['county']],
                'service_zips': [], 'geo_derivation': 'source_county',
                'current_status': 'unknown', 'last_verified_at': None,
                'source_name': r['source'], 'source_url': r['source_url'],
                'source_retrieved_at': r['retrieved'],
                'extraction_method': 'structured_parse',
                'needs_source_verification': False,
                'extraction_notes':
                    'County Department of Social Services. LIEAP heating applications run '
                    'Dec 1 - Mar 31 (Dec reserved for age 60+ and disabled); CIP crisis '
                    'assistance runs year round. Season per the NC FFY2027 LIHEAP state '
                    'plan; NCDHHS directs applicants to the county office for actual '
                    'opening dates. Government agency: never present as affiliated.',
            })
    return out

def fl_records():
    rows = list(csv.DictReader(open('data/sources/fl-liheap-providers.psv'), delimiter='|'))
    # The state page writes the same agency slightly differently across counties
    # ("Suwannee River Economic Council, Inc." vs "...Council Inc"), so group on
    # the slug. Grouping on the raw string silently dropped counties.
    byagency = collections.defaultdict(list)
    meta = {}
    for r in rows:
        if not r['org_name']:
            continue
        # "Capital Area Community Action Agency" and "...Agency, Inc." are the
        # same agency written two ways on the state page. Normalise the
        # corporate suffix for the grouping key only; keep the fullest name for
        # display.
        key = slugify(re.sub(r',?\s+(inc|incorporated|corp|llc)\.?$', '',
                             r['org_name'], flags=re.I))
        byagency[key].append(r['county'])
        if key not in meta or len(r['org_name']) > len(meta[key]['org_name']):
            meta[key] = r
    out = []
    for key, counties in byagency.items():
        r = meta[key]
        agency = r['org_name']
        out.append({
            'org_name': agency, 'state': 'FL',
            'program_name': 'Low-Income Home Energy Assistance Program (LIHEAP)',
            'slug': f'{key}-liheap',
            'org_type': 'government' if re.search(
                r'\b(county|city|commission|department|floridacommerce)\b', agency, re.I)
                else 'nonprofit',
            'city': None, 'address': None,   # the state list publishes no address
            'phone': r['phone'] or None, 'url': r['url'] or None,
            'volatility_tier': 'B',
            'need_tags': ['electric_bill', 'gas_bill', 'reconnect_fee', 'utility_deposit'],
            'service_counties': sorted(counties),
            'service_zips': [], 'geo_derivation': 'source_county',
            'current_status': 'unknown', 'last_verified_at': None,
            'source_name': r['source'], 'source_url': r['source_url'],
            'source_retrieved_at': r['retrieved'],
            'extraction_method': 'structured_parse',
            'needs_source_verification': False,
            'extraction_notes':
                'FloridaCommerce publishes one LIHEAP provider per county and no street '
                'address; address is null rather than guessed. Heating 10/01-03/31, '
                'cooling 04/01-09/30, crisis year round, per the FFY2027 state plan. A '
                'statewide online application exists at floridaliheap.com.',
        })
    return out

if __name__ == '__main__':
    for name, recs in (('nc-county-dss', nc_records()), ('fl-liheap-providers', fl_records())):
        p = OUT / f'{name}.jsonl'
        with p.open('w') as f:
            for r in recs:
                f.write(json.dumps(r) + '\n')
        orgs = len({r['org_name'] for r in recs})
        print(f'{p}: {len(recs)} program records across {orgs} organizations')
