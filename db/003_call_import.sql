-- Additions needed by the call-sheet importer.
BEGIN;

-- The first ten calls produced three rows the dialer refused to place at all
-- ("federal DNC list"). The disposition enum had no value for that, so those rows
-- would have imported as ordinary no-answers -- hiding a systemic block behind
-- what looks like normal attrition. 'blocked' keeps them visible and countable.
ALTER TABLE call_attempts DROP CONSTRAINT IF EXISTS call_attempts_disposition_check;
ALTER TABLE call_attempts ADD CONSTRAINT call_attempts_disposition_check
  CHECK (disposition IN ('reached','voicemail','no_answer','busy','wrong_number',
                         'callback_booked','refused','gatekeeper','disconnected',
                         'blocked'));

-- Service area as the agency states it on the call. This is the field the crosswalk
-- cannot produce: WHAM serves five ZIPs, the county expansion gives it 263. Free text
-- because agencies describe it in their own terms ("west Houston", a ZIP list, "the
-- whole of Houston"); a VA or a later pass turns it into program_zips.
ALTER TABLE programs ADD COLUMN IF NOT EXISTS stated_service_area text;
ALTER TABLE programs ADD COLUMN IF NOT EXISTS languages_stated text;

-- Where a sheet row came from, so an import can be re-run or rolled back.
ALTER TABLE status_log ADD COLUMN IF NOT EXISTS import_batch text;
CREATE INDEX IF NOT EXISTS status_log_import_batch_idx ON status_log (import_batch);

COMMIT;
