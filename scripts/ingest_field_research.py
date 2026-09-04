#!/usr/bin/env python3
"""Team-discovered organizations -> data/listings/field-research.jsonl.

These are the rows the team found by working local areas: church pantries,
county human services offices, crisis ministries. They are not in any state
directory and never will be, which is exactly why they are worth having. A
state LIHEAP table is commodity data; knowing which pantry in Burke County has
money this week is not.

PROVENANCE. Earlier these were held back for having no source_url, which was my
error: it treated "no published document" as "no evidence". For a
field-discovered organization the document does not exist and does not need to.
What has to be recorded is the DISCOVERY -- who found it, when, and where they
were looking -- and then the phone call is what makes it publishable. That is a
stronger claim than a PDF someone posted in 2023, not a weaker one.

  extraction_method   field_research
  source_name         CornerHelp field research
  source_url          whatever they were looking at, or null (this class only)
  needs_source_verification  true, cleared by a call and not by a document

SERVICE AREA. A TDHCA subrecipient's counties are contractual and need no call.
A church pantry's are not -- it may serve three ZIPs around the building. So
these rows are exactly the ones where the SERVICE AREA question earns its place,
and service_area_source stays 'inferred' until a rep says otherwise.

Rows sharing a phone number are one office and are merged; the pasted list had
Bay County's housing line and its food pantry line as separate rows.
"""
import json, re, csv, glob, collections, datetime, pathlib

TODAY = datetime.date.today().isoformat()
PLACEHOLDER = re.compile(r'\b(varies|verify|confirm current|confirm .*intake|tbd|n/?a)\b', re.I)

def digits(s):
    return re.sub(r'\D', '', s or '')

def slugify(s):
    return re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', s.lower()))[:80]

# Area code -> state, for the markets we cover. Used only to disambiguate a
# county name shared by two states, and only when it agrees with one of the
# candidates. Not a general geocoder.
AREA_CODES = {
    'FL': {'239','305','321','352','386','407','448','561','656','689','727',
           '754','772','786','813','850','863','904','941','954'},
    'NC': {'252','336','472','704','743','828','910','919','980','984'},
    'TX': {'210','214','254','281','325','346','361','409','430','432','469',
           '512','682','713','726','737','806','817','830','832','903','915',
           '936','940','945','956','972','979'},
}


def resolve_state(county, given, phone=''):
    """Some rows carry a county but no state. Resolve it from the canonical
    county list ONLY when the name is unique across the markets we cover --
    Escambia is Florida and nowhere else. Where a name is shared (Jackson exists
    in all three states) the state stays null and the row is not listed, because
    guessing is how North Carolina ended up with Texas ZIP codes."""
    if given:
        return given
    hits = {st for st, name in COUNTY_STATES if name == county}
    if len(hits) == 1:
        return hits.pop()
    ac = digits(phone)[-10:][:3]
    byarea = {st for st, codes in AREA_CODES.items() if ac in codes}
    both = hits & byarea
    return both.pop() if len(both) == 1 else None


COUNTY_STATES = {(r['state'], r['name'].replace(' County', ''))
                 for r in csv.DictReader(open('data/geo/counties.csv'))}


def main():
    audit = json.load(open('data/sources/pasted-rows-audit.json'))
    leads = [r for r in audit if r['verdict'] in ('unmatched', 'placeholder')]

    # phones already in the sourced spine -- never call one office twice
    spine = set()
    for f in ('nc-county-dss', 'fl-liheap-providers', 'tdhca-subrecipients', 'harris-tier2'):
        for line in open(f'data/listings/{f}.jsonl'):
            p = digits(json.loads(line).get('phone'))
            if len(p) >= 10:
                spine.add(p[-10:])

    groups, rejected, dupes = collections.OrderedDict(), [], []
    for r in leads:
        p = digits(r['phone'])[-10:]
        if len(p) < 10:
            rejected.append((r, 'no phone number — cannot be called'))
            continue
        if p in spine:
            dupes.append(r)
            continue
        groups.setdefault(p, []).append(r)

    out = []
    for phone, rows in groups.items():
        # keep the longest name; the shorter ones are usually the same office
        rows.sort(key=lambda r: -len(r['org']))
        r = rows[0]
        addr = next((x['addr'] for x in rows if x['addr'] and not PLACEHOLDER.search(x['addr'])), None)
        city = next((x['city'] for x in rows if x['city'] and not PLACEHOLDER.search(x['city'])), None)
        county = re.sub(r'\s*County\s*$', '', (r['county'] or '').strip())
        # the pasted rows spell it out; the Census abbreviates
        county = re.sub(r'^Saint\b', 'St.', county)
        tags = sorted({t.strip() for x in rows for t in (x['help'] or '').split(',') if t.strip()})
        state = resolve_state(county, r['state'] or None, phone)
        if not county or not tags:
            rejected.append((r, 'no county or no need tag — not enough to list'))
            continue
        if not state:
            rejected.append((r, f'county "{county}" exists in more than one state — '
                                'needs the state stated, not guessed'))
            continue
        out.append({
            'org_name': r['org'], 'program_name': 'Assistance services',
            'slug': slugify(r['org']), 'org_type': 'nonprofit',
            'state': state, 'city': city, 'address': addr,
            'phone': f'+1{phone}', 'url': None, 'volatility_tier': 'B',
            'need_tags': tags, 'service_counties': [county] if county else [],
            'service_zips': [], 'geo_derivation': 'source_county',
            'service_area_source': 'inferred',
            'current_status': 'unknown', 'last_verified_at': None,
            'source_name': 'CornerHelp field research',
            'source_url': None, 'source_retrieved_at': TODAY,
            'extraction_method': 'field_research',
            'needs_source_verification': True,
            'discovered_by': None, 'discovery_method': None,
            'extraction_notes':
                'Found by the team working the local area, not published in any state '
                'directory. Discovery fields are null for this backfill because the '
                'original rows did not capture them; new finds record them at the time. '
                'Service area is a guess until a rep states it.',
            'merged_rows': [x['org'] for x in rows[1:]] or None,
        })

    p = pathlib.Path('data/listings/field-research.jsonl')
    with p.open('w') as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    print(f'{len(leads)} held-back rows ->')
    print(f'  {len(out):4} listings written to {p}')
    print(f'  {sum(1 for r in out if r["merged_rows"]):4} of those merged two or more rows sharing a phone')
    print(f'  {len(dupes):4} dropped as duplicates of an office already in the sourced spine')
    print(f'  {len(rejected):4} not listable')
    for r, why in rejected:
        print(f'        {r["org"][:56]:58} {why}')
    if dupes:
        print('\n  duplicates of the spine:')
        for r in dupes[:10]:
            print(f'        {r["org"][:70]}')

if __name__ == '__main__':
    main()
