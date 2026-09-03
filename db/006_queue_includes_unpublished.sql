-- Applied to Supabase project vdursgkijnoqjprkbojo 2026-09-03.
--
-- rebuild_queue filtered on is_published, but a record is only published once it has been
-- verified, and it is only verified by being pulled off this queue. That is a deadlock:
-- with all 18 Harris records unpublished, the queue built zero rows and no VA would ever
-- have been handed anything.
--
-- is_published gates what the SITE shows. removal_requested_at gates what we are allowed
-- to call. Those are different questions and only the second belongs here.
--
-- This bug is present in db/002_status_log.sql too, and in docs/03-database.md.
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
