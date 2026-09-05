#!/usr/bin/env python3
"""Automated QA on a filled call sheet, before anything reaches the database.

docs/05-va-operations.md asks for automated QA first and 5% human review on top. These
are the checks that would have caught what a human reading 44 rows did not:

  CONTAMINATION  one agency's answers pasted onto another's row. Caught by looking for
                 the same contact name, note or document list appearing under two
                 different organizations. This is the dangerous one -- the row reads
                 perfectly well on its own and publishes a false listing.

  NO PERSON      a status set from a recording or a voicemail greeting. A phone tree
                 tells you what the tree says, not whether the money is there. These are
                 not wrong, they are weaker: they downgrade to agency_self_report rather
                 than being thrown away.

  CONTRADICTION  the note says the call did not reach the program, while the status says
                 it is accepting.

  UNSUPPORTED    a status recorded on an outcome that was never a contact.

  NO CATCHMENT   status confirmed but no service area. Not an error -- the single most
                 common reason a confirmed program still cannot publish, so it is
                 counted separately.

  python3 scripts/qa_call_sheet.py --csv sheet.csv
"""
import csv, re, sys, argparse, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_call_sheet import parse, col

NO_PERSON = re.compile(r'\bvm\b|voice ?mail|recording|automated|answering machine', re.I)
NOT_REACHED = re.compile(
    r'not (?:utility|the) |appears to be for|wrong (?:number|department)|'
    r'different (?:program|department)|no (?:financial )?assistance|does not (?:offer|provide)', re.I)
CONTACT_STATUSES = {'reached', 'gatekeeper', 'callback_booked'}
# Notes that describe the CALL, not the agency. These repeat legitimately across rows --
# three numbers can all be DNC-blocked, two can both play hold music -- and treating them
# as a fingerprint drowns the real signal.
BOILERPLATE = re.compile(
    r'^\s*(hold music|full inbox|unavailable to assist|no answer|busy|closed due to|'
    r'this phone number is on the federal dnc|the number (dialed )?is (not in service|'
    r'disconnected)|on another call|hotline .* lunch)', re.I)


def qa(rows):
    flags = collections.defaultdict(list)

    # --- contamination: the same distinctive answer under two organizations ---
    # Only rows carrying a real status can reach a listing, so only those can contaminate
    # one. A repeated note across two voicemails is noise.
    publishable = [r for r in rows if r.get('status') and r['status'] != 'unknown']

    # A shared FIRST NAME is not evidence. Two agencies each having a Patricia is
    # ordinary; the Rolling Plains contamination was caught because the note and
    # the document list matched too. So a name collision only counts when a
    # substantive field corroborates it -- otherwise this flags four honest rows
    # for every real one and the gate stops being believed.
    def corroborated(a, b):
        for f in ('note', 'stated_service_area'):
            x, y = (a.get(f) or '').strip().lower(), (b.get(f) or '').strip().lower()
            if x and x == y:
                return True
        da = tuple(d.lower() for d in (a.get('practicals') or {}).get('documents_required') or ())
        db = tuple(d.lower() for d in (b.get('practicals') or {}).get('documents_required') or ())
        return bool(da) and da == db

    for field in ('spoke_with', 'note'):
        seen = collections.defaultdict(list)
        for r in publishable:
            v = (r.get(field) or '').strip()
            if len(v) < 4 or BOILERPLATE.match(v):
                continue
            if field == 'note' and len(v) < 40:
                continue          # short notes are rarely distinctive enough to fingerprint
            seen[v.lower()].append(r)
        for v, group in seen.items():
            orgs = {g['org'] for g in group}
            if len(orgs) < 2:
                continue
            if field == 'spoke_with' and not any(
                    corroborated(a, b) for i, a in enumerate(group) for b in group[i + 1:]):
                flags['SHARED NAME'].append(
                    (group[0], f'"{v[:40]}" appears under {len(orgs)} organizations with '
                               'different answers — common name, not contamination'))
                continue
            for g in group:
                flags['CONTAMINATION'].append(
                    (g, f'{field} "{v[:60]}" also appears under: '
                        f'{", ".join(sorted(orgs - {g["org"]}))[:70]}'))

    # documents lists are distinctive enough to be a fingerprint too
    seen = collections.defaultdict(list)
    for r in publishable:
        docs = (r.get('practicals') or {}).get('documents_required')
        if docs and len(docs) > 1:
            seen[tuple(d.lower() for d in docs)].append(r)
    for docs, group in seen.items():
        orgs = {g['org'] for g in group}
        if len(orgs) > 1:
            for g in group:
                flags['CONTAMINATION'].append(
                    (g, f'identical document list to: {", ".join(sorted(orgs - {g["org"]}))[:70]}'))

    for r in rows:
        status = r.get('status')
        confirmed = status and status != 'unknown'
        spoke = (r.get('spoke_with') or '')
        note = (r.get('note') or '')

        if confirmed and (NO_PERSON.search(spoke) or NO_PERSON.search(note)):
            flags['NO PERSON'].append(
                (r, 'status set from a recording or voicemail — downgrade to '
                    'agency_self_report / partial, not a conversation'))
        if confirmed and NOT_REACHED.search(note):
            flags['CONTRADICTION'].append(
                (r, f'status "{status}" but the note says the program was not reached: '
                    f'"{note[:70]}"'))
        # An IVR is not a person, but it does speak: "we are not currently
        # accepting applications" off a recording is a real observation, and the
        # importer already books it as agency_self_report / partial rather than a
        # conversation. A REFUSAL is different -- nobody said anything, so a
        # status on it came from somewhere other than the call.
        if confirmed and r.get('disposition') not in CONTACT_STATUSES:
            if r.get('disposition') == 'voicemail':
                flags['FROM A RECORDING'].append(
                    (r, f'status "{status}" taken off a recording — imports as '
                        'agency_self_report / partial, not a conversation'))
            else:
                flags['UNSUPPORTED'].append(
                    (r, f'status "{status}" recorded on outcome "{r.get("disposition")}" — '
                        'nobody stated it; importing as unknown'))
        if confirmed and not r.get('stated_service_area'):
            flags['NO CATCHMENT'].append((r, 'confirmed, but no service area — cannot publish'))
    return flags


def main(paths):
    rows = []
    for p in paths:
        rs, _ = parse(p, 'qa')
        rows += rs
    flags = qa(rows)
    order = ['CONTAMINATION', 'CONTRADICTION', 'UNSUPPORTED', 'FROM A RECORDING',
             'SHARED NAME', 'NO PERSON', 'NO CATCHMENT']
    blocking = 0
    for k in order:
        items = flags.get(k)
        if not items:
            continue
        seen = set(); uniq = []
        for r, msg in items:
            key = (r['slug'], msg)
            if key not in seen:
                seen.add(key); uniq.append((r, msg))
        block = k in ('CONTAMINATION', 'CONTRADICTION', 'UNSUPPORTED')
        if block:
            blocking += len(uniq)
        print(f'\n{k}  ({len(uniq)})' + ('   *** BLOCKS IMPORT ***' if block else '   (informational)'))
        for r, msg in uniq:
            print(f'  {r["org"][:44]:<46} {msg}')
    print(f'\n{len(rows)} rows checked · {blocking} blocking issue(s)')
    if blocking:
        print('Fix these in the sheet and re-export. A contaminated row publishes a false '
              'listing and reads perfectly well on its own.')
    return 1 if blocking else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', nargs='+', required=True)
    sys.exit(main(ap.parse_args().csv))
