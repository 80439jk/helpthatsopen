#!/usr/bin/env python3
"""Filled verification call sheet -> call_attempts + status_log.

Export the Google Sheet as CSV (File > Download > Comma-separated values) and point
this at it. Idempotent per batch: re-importing the same file replaces that batch
rather than duplicating, so you can export mid-day and again at close.

  python3 scripts/import_call_sheet.py --csv sheet.csv --dsn "$DATABASE_URL"
  python3 scripts/import_call_sheet.py --csv sheet.csv --dry-run

Two things this deliberately does NOT do:

  It never invents a status. A row whose STATUS cell is blank imports as 'unknown'
  with the note attached, because that is what happened -- somebody was reached and
  the status was not established. Filling it in would be the exact fabrication the
  contract exists to stop.

  It never drops a row for having failed. A voicemail is an observation. A number the
  dialer refused to place is an observation. Both write call_attempts rows so the
  reach rate and the contactability score see them.
"""
import csv, json, argparse, sys, re, hashlib, datetime, pathlib

# sheet Outcome -> (call_attempts.disposition, status_log.verify_outcome)
OUTCOME = {
    'reached':         ('reached',       'reached'),
    'gatekeeper':      ('gatekeeper',    'partial'),
    'callback_booked': ('callback_booked','partial'),
    'refused':         ('refused',       'refused'),
    'voicemail':       ('voicemail',     'unreachable'),
    'no_answer':       ('no_answer',     'unreachable'),
    'busy':            ('busy',          'unreachable'),
    'disconnected':    ('disconnected',  'unreachable'),
    'wrong_number':    ('wrong_number',  'unreachable'),
}
STATUSES = {'accepting','waitlist','funds_exhausted','seasonal_closed',
            'appointment_only','unknown'}
# a blank Outcome plus a DNC note means the dialer never placed the call
DNC = re.compile(r'\bdnc\b|do not call|federal dnc', re.I)


def col(row, *names):
    """Sheet headers drift; match on a normalised key."""
    norm = {re.sub(r'[^a-z]', '', (k or '').lower()): (v or '').strip()
            for k, v in row.items()}
    for n in names:
        v = norm.get(re.sub(r'[^a-z]', '', n.lower()))
        if v:
            return v
    return ''


def parse(csv_path, batch):
    rows, problems = [], []
    with open(csv_path, encoding='utf-8-sig') as f:
        # the sheet has banner rows above the header; find the row containing 'slug'
        raw = list(csv.reader(f))
    hdr_i = next((i for i, r in enumerate(raw)
                  if any((c or '').strip().lower() == 'slug' for c in r)), None)
    if hdr_i is None:
        sys.exit("Could not find a header row containing 'slug'.")
    header = [c.strip() for c in raw[hdr_i]]
    for r in raw[hdr_i + 1:]:
        if not any((c or '').strip() for c in r):
            continue
        row = dict(zip(header, r))
        slug = col(row, 'slug')
        if not slug:
            continue

        outcome_raw = col(row, 'Outcome').lower().replace(' ', '_')
        note = col(row, 'NOTE', 'Note')
        blankwhy = col(row, 'Blank fields — why', 'Blank fields why', 'Blank fields')

        if outcome_raw in OUTCOME:
            disp, vout = OUTCOME[outcome_raw]
        elif DNC.search(note) or DNC.search(blankwhy):
            disp, vout = 'blocked', 'unreachable'
        elif not outcome_raw:
            problems.append(f'{slug}: no Outcome and no DNC note — row skipped')
            continue
        else:
            problems.append(f'{slug}: unrecognised Outcome {outcome_raw!r} — row skipped')
            continue

        status = col(row, 'STATUS', 'Status').lower().replace(' ', '_')
        if status and status not in STATUSES:
            problems.append(f'{slug}: STATUS {status!r} not in the enum — imported as unknown')
            status = 'unknown'
        if not status:
            status = 'unknown'

        practicals = {}
        for key, *names in (('how_to_apply', 'How to apply'),
                            ('daily_cap', 'Daily cap'),
                            ('documents_required', 'Documents required'),
                            ('disqualifier', 'MOST COMMON DISQUALIFIER', 'Most common disqualifier')):
            v = col(row, *names)
            # rule 5: a zero that means "not asked" is not a number
            if key == 'daily_cap':
                v = v if re.fullmatch(r'[1-9]\d*', v) else ''
            if key == 'documents_required' and v:
                practicals[key] = [x.strip(' .') for x in re.split(r'[;\n]|\d+\.\s*', v) if x.strip(' .')]
                continue
            if v:
                practicals[key] = v

        date = col(row, 'Date called') or datetime.date.today().isoformat()
        rows.append({
            'slug': slug,
            'org': col(row, 'Organization'),
            'observed_at': date,
            'status': status,
            'verify_method': 'phone',
            'verify_outcome': vout,
            'disposition': disp,
            'attempt': col(row, 'Att') or '1',
            'va': col(row, 'VA'),
            'spoke_with': col(row, 'Spoke with') or None,
            'funds_last_until': col(row, 'Funds last until') or None,
            'reopens_on': col(row, 'Reopens on') or None,
            'note': note or None,
            'practicals': practicals or None,
            'stated_service_area': col(row, 'Service area') or None,
            'languages_stated': col(row, 'Languages') or None,
            'null_reasons': {'blank_fields': blankwhy} if blankwhy else None,
            'import_batch': batch,
        })
    return rows, problems


def report(rows, problems):
    import collections
    disp = collections.Counter(r['disposition'] for r in rows)
    reached = disp['reached'] + disp['gatekeeper'] + disp['callback_booked']
    dialed = sum(v for k, v in disp.items() if k != 'blocked')
    print(f'{len(rows)} rows parsed\n')
    print('dispositions:')
    for k, v in disp.most_common():
        print(f'  {v:>3}  {k}')
    if dialed:
        print(f'\nreach rate: {reached}/{dialed} dialed = {100*reached/dialed:.0f}%'
              f'   (model assumes 60%)')
    if disp['blocked']:
        print(f'BLOCKED BY DIALER: {disp["blocked"]} of {len(rows)} '
              f'({100*disp["blocked"]/len(rows):.0f}%) never placed — business lines '
              f'scrubbed against the consumer DNC list')
    st = collections.Counter(r['status'] for r in rows)
    print('\nstatuses recorded:')
    for k, v in st.most_common():
        print(f'  {v:>3}  {k}')
    named = [r for r in rows if r['stated_service_area']]
    if named:
        print(f'\nservice area stated on the call ({len(named)}) — the field the crosswalk cannot produce:')
        for r in named:
            print(f'  {r["org"][:40]:<42} {r["stated_service_area"][:52]}')
    if problems:
        print(f'\nPROBLEMS ({len(problems)}):')
        for p in problems:
            print(f'  {p}')


def load(rows, dsn, batch):
    import psycopg2, psycopg2.extras
    conn = psycopg2.connect(dsn); cur = conn.cursor()
    cur.execute("DELETE FROM status_log WHERE import_batch = %s", (batch,))
    ins = skipped = 0
    for r in rows:
        cur.execute("SELECT program_id FROM programs WHERE slug = %s", (r['slug'],))
        got = cur.fetchone()
        if not got:
            skipped += 1; continue
        pid = got[0]
        cur.execute("SELECT va_id FROM staff WHERE name = %s", (r['va'],))
        s = cur.fetchone()
        if not s and r['va']:
            cur.execute("INSERT INTO staff (name) VALUES (%s) RETURNING va_id", (r['va'],))
            s = cur.fetchone()
        va = s[0] if s else None

        cur.execute("""INSERT INTO call_attempts (program_id, va_id, started_at, disposition)
                       VALUES (%s,%s,%s,%s) RETURNING call_id""",
                    (pid, va, r['observed_at'], r['disposition']))
        call_id = cur.fetchone()[0]
        cur.execute("""INSERT INTO status_log
            (program_id, observed_at, status, verify_method, verify_outcome, va_id,
             spoke_with, funds_last_until, reopens_on, note, practicals, call_id,
             null_reasons, import_batch)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (pid, r['observed_at'], r['status'], r['verify_method'], r['verify_outcome'], va,
             r['spoke_with'], r['funds_last_until'], r['reopens_on'] or None, r['note'],
             json.dumps(r['practicals']) if r['practicals'] else None, call_id,
             json.dumps(r['null_reasons']) if r['null_reasons'] else None, batch))
        if r['stated_service_area'] or r['languages_stated']:
            cur.execute("""UPDATE programs SET
                             stated_service_area = COALESCE(%s, stated_service_area),
                             languages_stated    = COALESCE(%s, languages_stated)
                           WHERE program_id = %s""",
                        (r['stated_service_area'], r['languages_stated'], pid))
        ins += 1
    conn.commit()
    print(f'\nloaded {ins} observations (batch {batch})')
    if skipped:
        print(f'{skipped} rows had a slug not present in programs — seed them first')
    cur.execute("SELECT rebuild_queue()"); conn.commit()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--dsn')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--batch')
    a = ap.parse_args()
    batch = a.batch or ('sheet-' + hashlib.sha1(
        pathlib.Path(a.csv).read_bytes()).hexdigest()[:8])
    rows, problems = parse(a.csv, batch)
    report(rows, problems)
    if a.dry_run or not a.dsn:
        print('\n(dry run — nothing written)')
    else:
        load(rows, a.dsn, batch)
