#!/usr/bin/env python3
"""Validate a listings JSONL file against data/CONTRACT.md.

Usage: python3 scripts/validate_listings.py <file.jsonl> [--counties data/counties/tx.txt]
Exit 0 = all rows pass. Exit 1 = at least one violation (nothing is imported).
"""
import json, sys, re, argparse, pathlib, collections

ORG_TYPES = {'caa','pha','food_bank','food_pantry','faith','municipal_utility',
             'co_op','nonprofit','aaa','clinic','school_district','aic_211','other'}
METHODS   = {'deterministic_parse','llm_pdf_extract','manual'}
REQUIRED  = ['org_name','program_name','org_type','volatility_tier','service_counties',
             'current_status','last_verified_at','source_name','source_url',
             'source_retrieved_at','extraction_method','needs_source_verification']
E164 = re.compile(r'^\+1\d{10}$')
ISO  = re.compile(r'^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?')

def validate(path, counties):
    errs, seen = [], {}
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        line = line.strip()
        if not line:
            continue
        def bad(msg): errs.append(f'line {n}: {msg}')
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            bad(f'not valid JSON — {e}'); continue

        for f in REQUIRED:
            if f not in r: bad(f'missing required field {f!r}')
        if errs and errs[-1].startswith(f'line {n}: missing'): continue

        # rule 1 — never import a status
        if r['current_status'] != 'unknown':
            bad(f'current_status must be "unknown", got {r["current_status"]!r}')
        if r['last_verified_at'] is not None:
            bad(f'last_verified_at must be null, got {r["last_verified_at"]!r}')

        # rule 2 — provenance
        for f in ('source_name','source_url','source_retrieved_at'):
            if not str(r.get(f) or '').strip(): bad(f'{f} is empty')
        if not ISO.match(str(r.get('source_retrieved_at',''))):
            bad('source_retrieved_at is not ISO 8601')
        if r['extraction_method'] not in METHODS:
            bad(f'extraction_method {r["extraction_method"]!r} not in {sorted(METHODS)}')

        # rule 3 — phones are real or absent
        ph = r.get('phone')
        if ph is not None and not E164.match(str(ph)):
            bad(f'phone {ph!r} is not E.164 (+1XXXXXXXXXX) or null')

        # rule 4 — counties must exist
        cs = r.get('service_counties') or []
        if not cs: bad('service_counties is empty')
        if len(cs) != len(set(cs)): 
            d = [c for c,k in collections.Counter(cs).items() if k>1]
            bad(f'duplicate counties within row: {d}')
        if counties:
            for c in cs:
                if c not in counties: bad(f'county {c!r} is not in the canonical list')

        # rule 5 — dedupe on program
        key = (r['org_name'], r['program_name'])
        if key in seen: bad(f'duplicate (org_name, program_name) — first seen line {seen[key]}')
        else: seen[key] = n

        # rule 6 — model output is a draft
        if str(r['extraction_method']).startswith('llm_') and not r['needs_source_verification']:
            bad('llm_* extraction must set needs_source_verification: true')

        if r['org_type'] not in ORG_TYPES: bad(f'org_type {r["org_type"]!r} invalid')
        if r['volatility_tier'] not in set('ABCD'): bad(f'volatility_tier {r["volatility_tier"]!r} invalid')
    return errs, len(seen)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--counties', default=None,
                    help='newline-delimited canonical county names for the state')
    a = ap.parse_args()
    counties = None
    if a.counties and pathlib.Path(a.counties).exists():
        counties = {l.strip() for l in open(a.counties, encoding='utf-8') if l.strip()}
    errs, ok = validate(a.file, counties)
    if errs:
        print(f'FAIL — {len(errs)} violation(s):')
        for e in errs[:50]: print('  ' + e)
        if len(errs) > 50: print(f'  ... and {len(errs)-50} more')
        sys.exit(1)
    print(f'PASS — {ok} rows, all contract rules satisfied'
          + (f', {len(counties)} canonical counties checked' if counties else
             ' (no county list supplied — rule 4 partially skipped)'))
