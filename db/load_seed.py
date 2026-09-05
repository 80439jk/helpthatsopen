#!/usr/bin/env python3
"""Load geography and contract-validated listings into Postgres.

Idempotent: re-running updates rather than duplicating. Deliberately does NOT write
status_log -- import never asserts a status. Every program lands with
current_status NULL and last_verified_at NULL, and becomes publishable only after a
VA commits an observation. See data/CONTRACT.md.

  python3 db/load_seed.py --dsn "$DATABASE_URL" --geo data/geo \
      --listings data/listings/tdhca-subrecipients.jsonl
"""
import csv, json, argparse, sys
import psycopg2, psycopg2.extras

def load(dsn, geo, listings):
    conn = psycopg2.connect(dsn); conn.autocommit = False
    cur = conn.cursor()

    def rows(fn):
        return list(csv.DictReader(open(f'{geo}/{fn}', encoding='utf-8')))

    c = [(r['county_fips'], r['name'], r['state'], int(r['population'] or 0) or None, r['slug'])
         for r in rows('counties.csv')]
    psycopg2.extras.execute_batch(cur, """
        INSERT INTO counties (county_fips,name,state,population,slug) VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (county_fips) DO UPDATE SET
          name=EXCLUDED.name, population=EXCLUDED.population, slug=EXCLUDED.slug""", c)

    z = [(r['zip'], r['primary_state'], int(r['population'] or 0) or None) for r in rows('zips.csv')]
    psycopg2.extras.execute_batch(cur, """
        INSERT INTO zips (zip,primary_state,population) VALUES (%s,%s,%s)
        ON CONFLICT (zip) DO UPDATE SET population=EXCLUDED.population""", z)

    zc = [(r['zip'], r['county_fips'],
           float(r['res_ratio']) if r['res_ratio'] else None,
           float(r['area_ratio']) if r['area_ratio'] else None)
          for r in rows('zip_counties.csv')]
    psycopg2.extras.execute_batch(cur, """
        INSERT INTO zip_counties (zip,county_fips,res_ratio,area_ratio) VALUES (%s,%s,%s,%s)
        ON CONFLICT (zip,county_fips) DO UPDATE SET
          res_ratio=EXCLUDED.res_ratio, area_ratio=EXCLUDED.area_ratio""", zc)
    print(f'geography: {len(c)} counties, {len(z)} zips, {len(zc)} pairs')

    recs = [json.loads(l) for l in open(listings, encoding='utf-8') if l.strip()]
    nostate = [r for r in recs if not r.get('state')]
    if nostate:
        conn.rollback()
        sys.exit(f'REFUSED: {len(nostate)} rows carry no state. County names are not '
                 'unique across states; attaching them by name alone is how a North '
                 'Carolina office ends up serving Texas.')
    bad = [r for r in recs if r['current_status'] != 'unknown' or r['last_verified_at'] is not None]
    if bad:
        conn.rollback()
        sys.exit(f'REFUSED: {len(bad)} rows carry a status. Import never asserts status. '
                 'Run scripts/validate_listings.py.')

    orgs, prog = 0, 0
    for r in recs:
        cur.execute("""INSERT INTO organizations (name,org_type) VALUES (%s,%s)
                       ON CONFLICT DO NOTHING RETURNING org_id""", (r['org_name'], r['org_type']))
        got = cur.fetchone()
        if got: org_id = got[0]; orgs += 1
        else:
            cur.execute("SELECT org_id FROM organizations WHERE name=%s AND org_type=%s LIMIT 1",
                        (r['org_name'], r['org_type']))
            org_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO programs (org_id,name,slug,volatility_tier,intake_phone,
              source_name,source_url,source_retrieved_at,extraction_method,
              needs_source_verification,service_area_source)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (slug) DO UPDATE SET
              intake_phone=EXCLUDED.intake_phone,
              needs_source_verification=EXCLUDED.needs_source_verification,
              -- never downgrade what a rep actually told us on a call
              service_area_source=CASE
                WHEN programs.service_area_source = 'stated' THEN 'stated'
                ELSE EXCLUDED.service_area_source END
            RETURNING program_id""",
            (org_id, r['program_name'], r['slug'], r['volatility_tier'], r['phone'],
             r['source_name'], r['source_url'], r['source_retrieved_at'],
             r['extraction_method'], r['needs_source_verification'],
             r.get('service_area_source') or 'inferred'))
        pid = cur.fetchone()[0]; prog += 1

        cur.execute("DELETE FROM program_zips WHERE program_id=%s", (pid,))
        psycopg2.extras.execute_batch(cur,
            "INSERT INTO program_zips (program_id,zip) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            [(pid, zz) for zz in r['service_zips']])
        cur.execute("DELETE FROM program_counties WHERE program_id=%s", (pid,))
        psycopg2.extras.execute_batch(cur,
            # state comes from the record. Hardcoding 'TX' here silently gave every
            # North Carolina and Florida program zero counties -- and county names
            # are shared across states, so matching on the name alone would have
            # attached the wrong ones instead. Same bug class as expand_zips.
            "INSERT INTO program_counties (program_id,county_fips) "
            "SELECT %s, county_fips FROM counties WHERE state=%s AND name=%s "
            "ON CONFLICT DO NOTHING",
            [(pid, r['state'], cn + ' County') for cn in r['service_counties']])
        cur.execute("DELETE FROM program_tags WHERE program_id=%s AND tag_type='need'", (pid,))
        psycopg2.extras.execute_batch(cur,
            "INSERT INTO program_tags (program_id,tag,tag_type) VALUES (%s,%s,'need') "
            "ON CONFLICT DO NOTHING", [(pid, t) for t in r.get('need_tags', [])])

    conn.commit()
    print(f'listings: {orgs} organizations, {prog} programs')
    cur.execute("SELECT rebuild_queue()"); conn.commit()
    print(f'queue: {cur.fetchone()[0]} rows')
    cur.execute("""SELECT p.name, o.name, q.score, q.staleness
                   FROM verification_queue q JOIN programs p USING (program_id)
                   JOIN organizations o USING (org_id) ORDER BY q.score DESC LIMIT 5""")
    print('\ntop of the queue:')
    for n, o, s, st in cur.fetchall():
        print(f'  {s:>6}  staleness {st:>6}  {o[:40]:<40} {n[:34]}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dsn', required=True)
    ap.add_argument('--geo', default='data/geo')
    ap.add_argument('--listings', default='data/listings/tdhca-subrecipients.jsonl')
    a = ap.parse_args()
    load(a.dsn, a.geo, a.listings)
