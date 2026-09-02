#!/usr/bin/env python3
"""Rank Texas counties for build order.

Population alone is the wrong criterion. Three things actually drive whether a
county page is worth building:

1. DEMAND -- people below the poverty line, not people. A county of 500k at 8%
   poverty generates far fewer assistance searches than one of 300k at 28%.
2. MARGINAL VERIFICATION COST -- county pages are nearly free once their providers
   are verified, because one CAA typically covers many counties. The right unit is
   "calls needed to publish this county", not "counties".
3. ENERGY MONETISATION -- retail electricity choice does not exist in municipal
   utility territory. Austin Energy, CPS Energy and El Paso Electric are regulated,
   so the energy vertical is worth zero in Travis, Bexar and El Paso however large
   they are. Traffic still converts on the call; the energy product does not exist.

Output: data/geo/county_priority.csv
"""
import csv, json, collections, argparse, math

# Municipally owned or non-ERCOT utilities: no retail choice. Counties whose
# population centre sits in one of these. Outlying parts of these counties may be
# served by a deregulated TDU, hence 'partial' rather than a hard zero.
NO_RETAIL_CHOICE = {
    'Travis': 'Austin Energy (municipal)',
    'Bexar': 'CPS Energy (municipal)',
    'El Paso': 'El Paso Electric (non-ERCOT)',
    'Cameron': 'Brownsville PUB (municipal, partial)',
    'Lubbock': 'LP&L (municipal, partial)',
    'Denton': 'Denton Municipal Electric (partial)',
    'Bryan': 'BTU (municipal, partial)',
    'Brazos': 'BTU (municipal, partial)',
}

def main(launch):
    pop = {}; 
    for r in csv.DictReader(open('data/geo/counties.csv')):
        pop[r['name'].replace(' County','')] = int(r['population'] or 0)
    pov = {r['name']: float(r['poverty_rate']) for r in
           csv.DictReader(open('data/geo/county_poverty.csv')) if r['poverty_rate']}

    rows=[json.loads(l) for l in open('data/listings/tdhca-subrecipients.jsonl') if l.strip()]
    ceap=[r for r in rows if 'CEAP' in r['program_name']]
    byc=collections.defaultdict(set)
    for r in ceap:
        for c in r['service_counties']: byc[c].add(r['org_name'])

    week1={r['org_name'] for r in ceap if set(launch) & set(r['service_counties'])}

    out=[]
    for c, providers in byc.items():
        p = pop.get(c,0); pr = pov.get(c)
        below = int(p*pr/100) if pr else None
        remaining = providers - week1
        tier = 1 if not remaining else (2 if providers & week1 else 3)
        out.append({
            'county': c, 'population': p, 'poverty_rate': pr,
            'people_below_poverty': below,
            'providers': len(providers),
            'calls_after_week1': len(remaining),
            'tier': tier,
            'retail_choice': 'no' if c in NO_RETAIL_CHOICE else 'yes',
            'utility_note': NO_RETAIL_CHOICE.get(c,''),
        })
    out.sort(key=lambda r: (r['tier'], -(r['people_below_poverty'] or 0)))
    with open('data/geo/county_priority.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

    for t in (1,2,3):
        g=[r for r in out if r['tier']==t]
        if not g: continue
        needy=sum(r['people_below_poverty'] or 0 for r in g)
        calls=len(set().union(*[byc[r['county']] for r in g])) if t>1 else len(week1)
        print(f"\nTIER {t}: {len(g)} counties · {sum(r['population'] for r in g):,} people · "
              f"{needy:,} below poverty")
        print(f"{'county':<16}{'pop':>10}{'pov%':>7}{'below':>10}{'prov':>6}{'+calls':>8}  energy")
        for r in g[:12]:
            print(f"{r['county']:<16}{r['population']:>10,}{r['poverty_rate'] or 0:>7.1f}"
                  f"{r['people_below_poverty'] or 0:>10,}{r['providers']:>6}"
                  f"{r['calls_after_week1']:>8}  {r['retail_choice']}")
        if len(g)>12: print(f"{'...':<16}{len(g)-12} more")
    print(f"\nwrote data/geo/county_priority.csv ({len(out)} counties)")

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--launch',default='Harris,Dallas,Tarrant,Bexar,Travis,Collin,Denton,Hidalgo,El Paso,Fort Bend')
    main(ap.parse_args().launch.split(','))
