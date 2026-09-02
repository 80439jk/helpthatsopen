-- The append-only status layer, the trigger, and the priority queue.
-- Fixes A3, A4, A5, A6, B2, B4, D5 from docs/00-review-findings.md.
BEGIN;

-- B2: method is the CHANNEL, outcome is the RESULT. Folding them into one column
-- meant an unreachable attempt lost the channel, so "what is our phone reach rate"
-- became unanswerable -- and that rate is the input to the entire staffing model.
CREATE TABLE status_log (
  entry_id      bigserial PRIMARY KEY,
  program_id    uuid NOT NULL REFERENCES programs,
  observed_at   timestamptz NOT NULL DEFAULT now(),
  status        text NOT NULL CHECK (status IN
                ('accepting','waitlist','funds_exhausted','seasonal_closed',
                 'appointment_only','unknown')),
  verify_method text NOT NULL CHECK (verify_method IN
                ('phone','email','web','agency_self_report')),
  verify_outcome text NOT NULL CHECK (verify_outcome IN
                ('reached','partial','unreachable','refused')),
  va_id         uuid REFERENCES staff,
  spoke_with    text,
  funds_last_until text,
  reopens_on    date,
  note          text,
  practicals    jsonb,          -- B4: snapshot of the practicals this observation set
  call_id       uuid REFERENCES call_attempts,
  null_reasons  jsonb,
  -- a status change must carry a note (docs/05-va-operations.md step 2)
  CONSTRAINT status_change_needs_note CHECK (
    verify_outcome <> 'reached' OR status = 'unknown' OR note IS NOT NULL)
);
CREATE INDEX ON status_log (program_id, observed_at DESC);

CREATE OR REPLACE FUNCTION tier_interval(t char(1)) RETURNS interval AS $$
  SELECT CASE t WHEN 'A' THEN interval '14 days'
                WHEN 'B' THEN interval '45 days'
                WHEN 'C' THEN interval '90 days'
                ELSE interval '180 days' END;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION apply_status_log() RETURNS trigger AS $$
BEGIN
  UPDATE programs p SET
    current_status   = NEW.status,
    last_verified_at = NEW.observed_at,
    next_verify_due  = NEW.observed_at + tier_interval(p.volatility_tier),
    -- A5: a failed attempt increments; only ACTUAL CONTACT resets. Previously any
    -- write whose method was not 'unreachable' reset the counter to 0, so the
    -- documented "drop to unknown after three attempts" commit restored
    -- contactability to 100 and the dead record recirculated at full priority.
    failed_attempts  = CASE WHEN NEW.verify_outcome IN ('reached','partial')
                            THEN 0 ELSE p.failed_attempts + 1 END,
    -- practicals are only authoritative when somebody actually spoke to them
    how_to_apply       = COALESCE(NEW.practicals->>'how_to_apply', p.how_to_apply),
    documents_required = COALESCE(
      (SELECT array_agg(x) FROM jsonb_array_elements_text(
         NEW.practicals->'documents_required') x), p.documents_required),
    application_window = COALESCE(NEW.practicals->>'application_window', p.application_window),
    hours              = COALESCE(NEW.practicals->'hours', p.hours),
    daily_cap          = COALESCE((NEW.practicals->>'daily_cap')::int, p.daily_cap),
    disqualifier       = COALESCE(NEW.practicals->>'disqualifier', p.disqualifier)
  WHERE p.program_id = NEW.program_id
    -- A6: never let a backfilled or out-of-order entry overwrite newer state.
    -- Without this, an older observation moved current_status back AND dragged
    -- last_verified_at backwards -- and dateModified is sourced from that field,
    -- so the site would publish a false freshness timestamp. .cursorrules rule 7.
    AND (p.last_verified_at IS NULL OR NEW.observed_at >= p.last_verified_at);
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_status_log AFTER INSERT ON status_log
  FOR EACH ROW EXECUTE FUNCTION apply_status_log();

-- status_log is append-only. Enforced at the grant level, not by convention.
CREATE OR REPLACE FUNCTION block_status_log_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'status_log is append-only (attempted %)', TG_OP;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_status_log_immutable BEFORE UPDATE OR DELETE ON status_log
  FOR EACH ROW EXECUTE FUNCTION block_status_log_mutation();

-- ============ DEMAND + QUEUE ============
CREATE TABLE search_events (
  event_id    bigserial PRIMARY KEY,
  zip         char(5),
  need_tag    text,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON search_events (zip, occurred_at DESC);

CREATE TABLE verification_queue (
  program_id  uuid PRIMARY KEY REFERENCES programs,
  score       numeric(5,2) NOT NULL,
  reach numeric(5,2), volatility numeric(5,2), staleness numeric(5,2),
  demand numeric(5,2), contactability numeric(5,2),
  computed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON verification_queue (score DESC);

CREATE OR REPLACE FUNCTION rebuild_queue() RETURNS integer AS $$
DECLARE n integer;
BEGIN
  -- D5: build then swap inside one transaction. TRUNCATE-then-INSERT left the
  -- queue empty for the duration of the nightly rebuild, so a VA on a late shift
  -- could pull nothing, and TRUNCATE takes ACCESS EXCLUSIVE which blocks behind
  -- an open shift lock.
  CREATE TEMP TABLE _q ON COMMIT DROP AS
  SELECT p.program_id,
         -- A3: ln() returns double precision and there is no round(double, int).
         ROUND((0.30*reach + 0.25*vol + 0.25*stale + 0.15*dem + 0.05*contact)::numeric, 2) AS score,
         reach::numeric(5,2), vol::numeric(5,2), stale::numeric(5,2),
         dem::numeric(5,2), contact::numeric(5,2)
  FROM programs p
  CROSS JOIN LATERAL (SELECT
    -- reach: population covered by the served ZIPs. ZCTA population needs a Census
    -- API key; until it is loaded, SUM() is 0 and every record ties, so fall back to
    -- the population of the counties the program DECLARES it serves. Not counties
    -- re-derived from ZIPs: cross-county ZIPs would pull in neighbours it does not serve.
    LEAST(100, 100 * ln(1 + COALESCE(NULLIF(
      (SELECT SUM(z.population) FROM program_zips pz
        JOIN zips z ON z.zip = pz.zip WHERE pz.program_id = p.program_id), 0),
      (SELECT COALESCE(SUM(c.population),0) FROM program_counties pc
        JOIN counties c USING (county_fips) WHERE pc.program_id = p.program_id),
      0)) / ln(1 + 8000000)) AS reach,
    CASE p.volatility_tier WHEN 'A' THEN 100 WHEN 'B' THEN 65
                           WHEN 'C' THEN 35 ELSE 15 END AS vol,
    -- A4: never-verified is MAXIMALLY stale. The documented expression divided by
    -- (next_verify_due - last_verified_at), null on an unverified record; the
    -- division went null, and GREATEST/LEAST silently drop nulls in Postgres, so
    -- staleness resolved to 0 -- and stayed 0 forever for anything never contacted.
    CASE WHEN p.last_verified_at IS NULL THEN 100
         ELSE LEAST(100, GREATEST(0,
           100 * EXTRACT(epoch FROM now() - p.last_verified_at)
               / EXTRACT(epoch FROM tier_interval(p.volatility_tier)))) END AS stale,
    LEAST(100, COALESCE((SELECT COUNT(*)::numeric FROM search_events se
       JOIN program_zips pz ON pz.zip = se.zip
       WHERE pz.program_id = p.program_id
         AND se.occurred_at > now() - interval '30 days'), 0) / 5) AS dem,
    GREATEST(0, 100 - p.failed_attempts * 20) AS contact
  ) s
  WHERE p.is_published AND p.removal_requested_at IS NULL;

  DELETE FROM verification_queue;
  INSERT INTO verification_queue
    (program_id, score, reach, volatility, staleness, demand, contactability)
  SELECT * FROM _q;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$ LANGUAGE plpgsql;

COMMIT;
