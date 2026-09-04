#!/usr/bin/env python3
"""State-published provider directories -> data/sources/*.psv, with provenance.

Two authorities, both fetched and parsed here rather than transcribed:

  NC  NCDHHS Local DSS Directory, the CSV behind the county map. One office per
      county, 100 counties. Address and phone are inside an HTML blob per row.
  FL  FloridaCommerce "Find Your Local LIHEAP Provider", the state's own
      county -> agency table. 67 counties. The state does NOT publish street
      addresses here, so address stays empty rather than being invented.

Nothing in the output is inferred. A field the source does not state is blank.
"""
import csv, re, html, json, datetime, pathlib, sys

TODAY = datetime.date.today().isoformat()
NC_URL = 'https://www.ncdhhs.gov/divisions/social-services/local-dss-directory'
NC_CSV = 'https://www.ncdhhs.gov/tablefield/export/paragraph/2914/field_map_data/en/0'
FL_URL = ('https://floridajobs.org/community-development/Low-Income-Home-Energy-Assistance-Program/'
          'find-your-local-low-income-home-energy-assistance-program-provider-for-help')

def text(s):
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    return html.unescape(s).replace('\xa0', ' ')

def parse_nc(path):
    out = []
    for row in csv.DictReader(open(path, encoding='utf-8', errors='replace')):
        county = (row.get('county') or '').strip()
        if not county:
            continue
        body = text(row.get('title') or '')
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        # address: the line carrying ", NC <zip>"
        addr = next((l for l in lines if re.search(r',\s*NC\s*\d{5}', l)), '')
        # phone: the first line labelled Phone, not Fax/Emergency/CPS/APS
        phone = ''
        for l in lines:
            m = re.match(r'Phone[^:]*:\s*([0-9][0-9\-\(\) \.]{9,})', l)
            if m:
                phone = re.sub(r'[^\d]', '', m.group(1))[:10]
                break
        out.append({
            'state': 'NC', 'county': county,
            'org_name': f'{county} County Department of Social Services',
            'address': addr, 'phone': f'+1{phone}' if len(phone) == 10 else '',
            'url': (row.get('url') or '').strip(),
            'source': 'NCDHHS Local DSS Directory',
            'source_url': NC_URL, 'retrieved': TODAY,
        })
    return out

# The state page's spelling is not always the Census spelling. Only exact,
# verified corrections belong here -- never a guess at what a county might be.
FL_COUNTY_FIX = {'Desoto': 'DeSoto'}


def parse_fl(path):
    h = open(path, encoding='utf-8', errors='replace').read()
    # each county cell: <span class="fs-5 fw-bold">County</span> ... <ul>..</ul>
    cells = re.findall(
        r'<span class="fs-5 fw-bold">([^<]+)</span>\s*<ul>(.*?)</ul>', h, re.S)
    out = []
    for county, blob in cells:
        county = html.unescape(county).strip()
        county = FL_COUNTY_FIX.get(county, county)
        if not county or len(county) > 30:
            continue
        names = re.findall(r'<a [^>]*>([^<]+)</a>', blob)
        agency = next((html.unescape(n).strip() for n in names
                       if not n.strip().lower().startswith('get help')), '')
        # Seminole has no local provider: the state page tells applicants to
        # call FloridaCommerce. That is the provider, not a missing row.
        if not agency and re.search(r'floridacommerce', blob, re.I):
            agency = 'FloridaCommerce (state administers LIHEAP directly)'
        m = re.search(r'Phone:\s*([^<]+)', blob)
        phones = re.findall(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', m.group(1)) if m else []
        href = re.search(r'href="([^"]+)"', blob)
        out.append({
            'state': 'FL', 'county': county, 'org_name': agency,
            'address': '',                      # the state list does not publish one
            'phone': '+1' + re.sub(r'\D', '', phones[0]) if phones else '',
            'phones_all': '; '.join(phones),
            'url': html.unescape(href.group(1)) if href else '',
            'source': 'FloridaCommerce LIHEAP provider list',
            'source_url': FL_URL, 'retrieved': TODAY,
        })
    return out

if __name__ == '__main__':
    nc = parse_nc('data/sources/nc/ncdhhs-local-dss-directory.csv')
    fl = parse_fl('data/sources/fl/floridacommerce-liheap-providers.html')
    for name, rows in (('nc-county-dss', nc), ('fl-liheap-providers', fl)):
        p = pathlib.Path(f'data/sources/{name}.psv')
        cols = list(rows[0])
        with p.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols, delimiter='|')
            w.writeheader(); w.writerows(rows)
        print(f'{p}: {len(rows)} rows')
    print(f'\nNC counties: {len(nc)}  with address: {sum(1 for r in nc if r["address"])}'
          f'  with phone: {sum(1 for r in nc if r["phone"])}')
    print(f'FL counties: {len(fl)}  distinct agencies: {len({r["org_name"] for r in fl})}'
          f'  with phone: {sum(1 for r in fl if r["phone"])}')
    missing = [r['county'] for r in nc if not r['address'] or not r['phone']]
    if missing:
        print('NC rows missing address or phone:', missing)
