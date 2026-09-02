#!/usr/bin/env python3
"""Harris County Tier 2 leads -> contract JSONL.

These are LEADS TO CALL, not listings. One source is an aggregator, which is exactly
the kind of stale third-party list this product exists to replace — so every row
imports with status unknown, last_verified_at null and needs_source_verification
true, and nothing publishes until a VA confirms it by phone.

Need tags are inferred from the free-text services column with a keyword map. That
inference is a starting point for the call, not a claim: the VA confirms what the
agency actually does. Tags land in the record so the queue can rank them; the
contract's needs_source_verification flag is what keeps them out of publication.

  python3 scripts/ingest_harris_tier2.py
"""
import json, re, sys, argparse, pathlib

SOURCES = {
 'NHPB': ('needhelppayingbills.com — Harris County assistance programs (AGGREGATOR)',
          'https://www.needhelppayingbills.com/html/harris_county_assistance_progr.html'),
 'HCPL': ('Harris County Public Library — Food Banks and Food Assistance',
          'https://hcpl.net/news/food-banks-and-food-assistance/'),
 'SALV': ('The Salvation Army Houston Area Command — Community Centers',
          'https://salvationarmyhouston.org/houston/ccc/'),
 'CCGH': ('Catholic Charities Archdiocese of Galveston-Houston — Locations',
          'https://catholiccharities.org/about-us/locations/'),
}

# keyword -> need tag, from the closed vocabulary in docs/02-data-model.md 5a
NEEDS = [
 (r'\brent\b|rental|eviction|re-hous|homeless prevention|homelessness prevention', 'rent_assistance'),
 (r'eviction', 'eviction_prevention'),
 (r'deposit', 'deposit_assistance'),
 (r'mortgage|foreclosure', 'mortgage_assistance'),
 (r'electric|light bill|cooling|energy|utilit|CEAP', 'electric_bill'),
 (r'\bgas\b(?! card| voucher)|natural gas', 'gas_bill'),
 (r'water bill|\bwater\b', 'water_bill'),
 (r'food|pantry|groceries|meals|formula', 'food_pantry'),
 (r'hot meals|soup', 'hot_meals'),
 (r'formula|diaper', 'formula_diapers'),
 (r'prescription|medic(al|ine)|dental|clinic|immunization', 'prescriptions'),
 (r'dental', 'dental'),
 (r'eyeglass|eyewear|vision', 'vision'),
 (r'clinic|health care|medical', 'free_clinic'),
 (r'transport|bus (token|pass|ticket)|Q Card', 'transportation'),
 (r'gas (card|voucher)', 'gas_vouchers'),
 (r'childcare|child care|Head Start', 'childcare'),
 (r'school suppl|educational suppl', 'school_supplies'),
 (r'holiday|Christmas', 'holiday_assistance'),
 (r'legal', 'legal_aid'),
 (r'burial|funeral|cremation', 'burial_assistance'),
 (r'clothing|clothes', 'holiday_assistance'),
 (r'shelter|lodging|transitional', 'rent_assistance'),
 (r'senior|aging|Medicare', 'transportation'),
]

def tags(txt):
    t = []
    for pat, tag in NEEDS:
        if re.search(pat, txt, re.I) and tag not in t:
            t.append(tag)
    return t

def slugify(s):
    return re.sub(r'-+','-', re.sub(r'[^a-z0-9]+','-', s.lower())).strip('-')[:80]

def to_e164(raw):
    d = re.sub(r'\D','', raw or '')
    return f'+1{d}' if len(d)==10 else None

def main(src, out, retrieved, existing):
    have = set()
    if pathlib.Path(existing).exists():
        for line in open(existing, encoding='utf-8'):
            if line.strip():
                have.add(json.loads(line)['org_name'].lower())

    rows, skipped = [], []
    for line in open(src, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line.strip() or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) != 8:
            print(f'  malformed ({len(parts)} fields): {line[:60]}', file=sys.stderr); continue
        key, name, addr, city, zipc, county, phone, services = parts
        if name.lower() in have:
            skipped.append(name); continue
        sname, surl = SOURCES[key]
        nt = tags(services) or ['rent_assistance']
        rows.append({
            'org_name': name,
            'program_name': 'Assistance services',   # the call establishes the real programs
            'slug': slugify(name),
            'org_type': ('faith' if re.search(r'church|catholic|ministr|baptist|methodist|'
                                              r'salvation|st\.|vincent|interfaith', name, re.I)
                         else 'food_bank' if re.search(r'food bank|pantry|hunger', name, re.I)
                         else 'aaa' if 'Aging' in name
                         else 'clinic' if re.search(r'clinic|health', name, re.I)
                         else 'school_district' if 'Department of Education' in name
                         else 'nonprofit'),
            'city': city or None,
            'address': addr or None,
            'location_zip': zipc or None,
            'phone': to_e164(phone),
            'url': None,
            'volatility_tier': 'C',      # pantries/ministries are stable; the call may reclassify
            'need_tags': nt,
            'service_counties': [county],
            'service_zips': [],          # real service area is a call question, not a guess
            'geo_derivation': 'source_county',
            'current_status': 'unknown',
            'last_verified_at': None,
            'source_name': sname,
            'source_url': surl,
            'source_retrieved_at': retrieved,
            'extraction_method': 'llm_pdf_extract',
            'needs_source_verification': True,
            'extraction_notes': ('source is a third-party aggregator; treat every field as '
                                 'unconfirmed' if key == 'NHPB' else None),
        })

    with open(out, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    import collections
    bysrc = collections.Counter(r['source_name'].split(' —')[0].split(' (')[0] for r in rows)
    bycty = collections.Counter(r['service_counties'][0] for r in rows)
    alltags = collections.Counter(t for r in rows for t in r['need_tags'])
    print(f'{len(rows)} leads -> {out}')
    if skipped: print(f'skipped (already in {existing}): {skipped}')
    print('\nby source:');  [print(f'  {v:>3}  {k}') for k,v in bysrc.most_common()]
    print('by county:');    [print(f'  {v:>3}  {k}') for k,v in bycty.most_common()]
    print('need coverage added:')
    for k,v in alltags.most_common(): print(f'  {v:>3}  {k}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default='data/sources/harris-tier2.raw.psv')
    ap.add_argument('--out', default='data/listings/harris-tier2.jsonl')
    ap.add_argument('--existing', default='data/listings/tdhca-subrecipients.jsonl')
    ap.add_argument('--retrieved-at', default='2026-09-02')
    a = ap.parse_args()
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    main(a.src, a.out, a.retrieved_at, a.existing)
