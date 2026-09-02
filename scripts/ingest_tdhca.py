#!/usr/bin/env python3
"""TDHCA Community Affairs subrecipients -> contract JSONL.

Source: https://www.tdhca.texas.gov/sites/default/files/community-affairs/docs/CA-SubRecip.pdf
        "Master List of Community Affairs Subrecipients"

The raw pipe-delimited input in data/sources/ was extracted from that PDF by a language
model, so every row is marked extraction_method=llm_pdf_extract and
needs_source_verification=true. It is a DRAFT until a deterministic parse or a human
confirms it. See data/CONTRACT.md.

One org runs several programs (CEAP, CSBG, WAP); the contract dedupes on the program,
so each program becomes its own row.
"""
import json, re, sys, pathlib, argparse

SRC_NAME = 'TDHCA Master List of Community Affairs Subrecipients'
SRC_URL  = 'https://www.tdhca.texas.gov/sites/default/files/community-affairs/docs/CA-SubRecip.pdf'

# Program -> (display name, volatility tier, need tags)
# CEAP is funds-cycling (tier A). WAP is a stable capital program (C).
# CSBG is a funding stream covering varied services (B).
PROGRAMS = {
    'CEAP': ('Comprehensive Energy Assistance Program (CEAP)', 'A',
             ['electric_bill','gas_bill','utility_deposit','reconnect_fee']),
    'CSBG': ('Community Services Block Grant (CSBG)', 'B',
             ['rent_assistance','food_pantry','transportation']),
    'WAP':  ('Weatherization Assistance Program (WAP)', 'C',
             ['weatherization','home_repair','hvac_repair']),
}

# Corrections applied to the model extraction, each with its reason.
# Recorded here rather than edited into the raw file so the artifact stays auditable.
COUNTY_FIXES = {
    'Davis':    None,        # not a Texas county; split out of 'Jeff Davis', also present
    'LaSalle':  'La Salle',  # spelling variant of a county already in the row
}

def org_type_for(name):
    n = name.lower()
    if 'council of governments' in n or 'regional planning' in n or 'development council' in n:
        return 'other'
    if n.startswith('city of') or ', city of' in n or 'county' in n:
        return 'other'
    return 'caa'

def slugify(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')

def to_e164(raw):
    d = re.sub(r'\D', '', raw or '')
    return f'+1{d}' if len(d) == 10 else None

def main(src, out, retrieved_at):
    rows = []
    for line in open(src, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, city, phone, progs, counties = [p.strip() for p in line.split('|')]

        cs, dropped = [], []
        for c in (x.strip() for x in counties.split(',')):
            if not c:
                continue
            if c in COUNTY_FIXES:
                fixed = COUNTY_FIXES[c]
                dropped.append(c)
                if fixed is None:
                    continue
                c = fixed
            if c not in cs:            # collapse intra-row duplicates
                cs.append(c)

        for code in [p.strip() for p in progs.split(',')]:
            if code not in PROGRAMS:
                print(f'  warn: unknown program {code!r} on {name!r}', file=sys.stderr)
                continue
            pname, tier, tags = PROGRAMS[code]
            rows.append({
                'org_name': name,
                'program_name': pname,
                'slug': f'{slugify(name)}-{code.lower()}',
                'org_type': org_type_for(name),
                'city': city or None,
                'phone': to_e164(phone),
                'url': None,
                'volatility_tier': tier,
                'need_tags': tags,
                'service_counties': cs,
                'service_zips': [],                      # crosswalk expansion is a later step
                'geo_derivation': 'source_county',
                'current_status': 'unknown',             # contract rule 1
                'last_verified_at': None,                # contract rule 1
                'source_name': SRC_NAME,
                'source_url': SRC_URL,
                'source_retrieved_at': retrieved_at,
                'extraction_method': 'llm_pdf_extract',  # contract rule 6
                'needs_source_verification': True,
                'extraction_notes': (f'counties corrected during ingest: {dropped}'
                                     if dropped else None),
            })

    with open(out, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    orgs = len({r['org_name'] for r in rows})
    allc = sorted({c for r in rows for c in r['service_counties']})
    print(f'{len(rows)} program rows from {orgs} organizations -> {out}')
    print(f'{len(allc)} distinct counties')
    by = {}
    for r in rows: by[r['program_name']] = by.get(r['program_name'], 0) + 1
    for k, v in sorted(by.items()): print(f'  {v:>3}  {k}')
    return allc

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default='data/sources/tdhca-subrecipients.raw.psv')
    ap.add_argument('--out', default='data/listings/tdhca-subrecipients.jsonl')
    ap.add_argument('--retrieved-at', default='2026-09-02')
    ap.add_argument('--write-counties', default=None,
                    help='also write the distinct county list here (canonical list seed)')
    a = ap.parse_args()
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    allc = main(a.src, a.out, a.retrieved_at)
    if a.write_counties:
        pathlib.Path(a.write_counties).parent.mkdir(parents=True, exist_ok=True)
        open(a.write_counties, 'w', encoding='utf-8').write('\n'.join(allc) + '\n')
        print(f'county list -> {a.write_counties}')
