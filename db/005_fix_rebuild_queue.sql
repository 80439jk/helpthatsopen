-- Applied to Supabase project vdursgkijnoqjprkbojo 2026-09-03.
-- A3: ln() returns double precision and Postgres has no round(double precision, integer),
--     so the function documented in 03-database.md did not compile at all.
-- A4: staleness divided by (next_verify_due - last_verified_at), which is null on an
--     unverified record. The division went null, and GREATEST/LEAST silently DROP nulls
--     in Postgres rather than propagating them, so staleness resolved to 0 -- and stayed
--     0 forever for anything never contacted. Measured cold-start score 49.75 where the
--     docs claim 74.75. Never-verified is now explicitly maximal staleness.
-- D5: TRUNCATE-then-INSERT left the queue empty for the duration of the nightly rebuild,
--     and TRUNCATE takes ACCESS EXCLUSIVE, which blocks behind an open shift lock.
--     Build into a temp table and swap inside one transaction.
DROP FUNCTION IF EXISTS rebuild_queue();

CREATE OR REPLACE FUNCTION rebuild_queue() RETURNS integer AS $$
DECLARE n integer;
BEGIN
  CREATE TEMP TABLE _q ON COMMIT DROP AS
  SELECT p.program_id,
         ROUND((0.30*reach + 0.25*vol + 0.25*stale + 0.15*dem + 0.05*contact)::numeric, 2) AS score,
         reach::numeric(5,2), vol::numeric(5,2), stale::numeric(5,2),
         dem::numeric(5,2), contact::numeric(5,2)
  FROM programs p
  CROSS JOIN LATERAL (SELECT
    -- ZIP population when loaded; otherwise the population of the counties the program
    -- DECLARES it serves. Not counties re-derived from ZIPs: cross-county ZIPs would pull
    -- in neighbours it does not serve, which measurably ranked rural multi-county
    -- providers above Harris.
    LEAST(100, 100 * ln(1 + COALESCE(NULLIF(
      (SELECT SUM(z.population) FROM program_zips pz
        JOIN zips z ON z.zip = pz.zip WHERE pz.program_id = p.program_id), 0),
      (SELECT COALESCE(SUM(c.population),0) FROM program_counties pc
        JOIN counties c USING (county_fips) WHERE pc.program_id = p.program_id),
      0)) / ln(1 + 8000000)) AS reach,
    CASE p.volatility_tier WHEN 'A' THEN 100 WHEN 'B' THEN 65
                           WHEN 'C' THEN 35 ELSE 15 END AS vol,
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
  WHERE p.removal_requested_at IS NULL;

  DELETE FROM verification_queue;
  INSERT INTO verification_queue
    (program_id, score, reach, volatility, staleness, demand, contactability)
  SELECT * FROM _q;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$ LANGUAGE plpgsql;

-- every program in this database is on the Harris acquisition list
INSERT INTO program_counties (program_id, county_fips)
SELECT p.program_id, '48201' FROM programs p
WHERE EXISTS (SELECT 1 FROM counties c WHERE c.county_fips = '48201')
ON CONFLICT DO NOTHING;
