-- Applied to Supabase project vdursgkijnoqjprkbojo (helpthatsopen) 2026-09-03.
-- Upgrades the live schema with the fixes from docs/00-review-findings.md, each of which
-- was reproduced against Postgres 16 before being written.
-- Additive and non-destructive: no table dropped, no row deleted. status_log was empty,
-- so reshaping it cost nothing.

-- B2: method is the CHANNEL, outcome is the RESULT. Folded together, an unreachable
-- attempt lost the channel and "what is our phone reach rate" became unanswerable --
-- and that rate is the input to the entire staffing model.
ALTER TABLE status_log ADD COLUMN IF NOT EXISTS verify_outcome text;
UPDATE status_log SET verify_outcome = 'reached' WHERE verify_outcome IS NULL;
ALTER TABLE status_log ALTER COLUMN verify_outcome SET NOT NULL;
ALTER TABLE status_log DROP CONSTRAINT IF EXISTS status_log_verify_outcome_check;
ALTER TABLE status_log ADD CONSTRAINT status_log_verify_outcome_check
  CHECK (verify_outcome IN ('reached','partial','unreachable','refused'));
ALTER TABLE status_log DROP CONSTRAINT IF EXISTS status_log_verify_method_check;
ALTER TABLE status_log ADD CONSTRAINT status_log_verify_method_check
  CHECK (verify_method IN ('phone','email','web','agency_self_report'));

-- B4: practicals history was claimed in the docs but never stored, so each verification
-- silently destroyed the previous documents_required.
ALTER TABLE status_log ADD COLUMN IF NOT EXISTS practicals jsonb;
ALTER TABLE status_log ADD COLUMN IF NOT EXISTS import_batch text;
CREATE INDEX IF NOT EXISTS status_log_import_batch_idx ON status_log (import_batch);

-- The field no crosswalk can produce. WHAM serves five ZIPs; this database gave it 130.
ALTER TABLE programs ADD COLUMN IF NOT EXISTS stated_service_area text;
ALTER TABLE programs ADD COLUMN IF NOT EXISTS languages_stated text;

-- The first ten calls produced three rows the dialer refused to place ("federal DNC
-- list"). With no enum value for that they import as ordinary no-answers, hiding a
-- systemic block inside what looks like normal attrition.
ALTER TABLE call_attempts DROP CONSTRAINT IF EXISTS call_attempts_disposition_check;
ALTER TABLE call_attempts ADD CONSTRAINT call_attempts_disposition_check
  CHECK (disposition IN ('reached','voicemail','no_answer','busy','wrong_number',
                         'callback_booked','refused','gatekeeper','disconnected','blocked'));

-- D3: counties the program DECLARES it serves. Cannot be re-derived from program_zips,
-- because a third of Texas ZIPs cross a county line.
CREATE TABLE IF NOT EXISTS program_counties (
  program_id  uuid    NOT NULL REFERENCES programs ON DELETE CASCADE,
  county_fips char(5) NOT NULL REFERENCES counties,
  PRIMARY KEY (program_id, county_fips)
);
CREATE INDEX IF NOT EXISTS program_counties_fips_idx ON program_counties (county_fips);

CREATE OR REPLACE FUNCTION tier_interval(t char(1)) RETURNS interval AS $$
  SELECT CASE t WHEN 'A' THEN interval '14 days' WHEN 'B' THEN interval '45 days'
                WHEN 'C' THEN interval '90 days' ELSE interval '180 days' END;
$$ LANGUAGE sql IMMUTABLE;

-- A5 + A6, two bugs in one function.
--   A5: failed_attempts reset on any write whose method was not 'unreachable', so the
--       documented "drop to unknown after three attempts" commit restored contactability
--       to 100 and the dead record recirculated at full priority. Measured: four attempts
--       left contactability at 100 instead of 20.
--   A6: the UPDATE was unconditional, so a backfilled or out-of-order entry overwrote
--       newer state AND dragged last_verified_at backwards. dateModified is sourced from
--       that field, so the site would publish a false freshness timestamp.
CREATE OR REPLACE FUNCTION apply_status_log() RETURNS trigger AS $$
BEGIN
  UPDATE programs p SET
    current_status   = NEW.status,
    last_verified_at = NEW.observed_at,
    next_verify_due  = NEW.observed_at + tier_interval(p.volatility_tier),
    failed_attempts  = CASE WHEN NEW.verify_outcome IN ('reached','partial')
                            THEN 0 ELSE p.failed_attempts + 1 END,
    how_to_apply       = COALESCE(NEW.practicals->>'how_to_apply', p.how_to_apply),
    documents_required = COALESCE(
      (SELECT array_agg(x) FROM jsonb_array_elements_text(
         NEW.practicals->'documents_required') x), p.documents_required),
    daily_cap          = COALESCE((NEW.practicals->>'daily_cap')::int, p.daily_cap),
    disqualifier       = COALESCE(NEW.practicals->>'disqualifier', p.disqualifier)
  WHERE p.program_id = NEW.program_id
    AND (p.last_verified_at IS NULL OR NEW.observed_at >= p.last_verified_at);
  RETURN NEW;
END $$ LANGUAGE plpgsql;

-- append-only enforced by trigger, not by convention
CREATE OR REPLACE FUNCTION block_status_log_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'status_log is append-only (attempted %)', TG_OP;
END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_status_log_immutable ON status_log;
CREATE TRIGGER trg_status_log_immutable BEFORE UPDATE OR DELETE ON status_log
  FOR EACH ROW EXECUTE FUNCTION block_status_log_mutation();
