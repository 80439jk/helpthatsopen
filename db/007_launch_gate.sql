-- Applied to Supabase project vdursgkijnoqjprkbojo 2026-09-03.
--
-- D2, the open question from docs/00-review-findings.md: what makes a ZIP eligible to go
-- live. Rule 7 said unpublish a county rather than serve stale statuses, but never said
-- how verified is verified enough.
--
-- THE RULE: a place is live when at least min_verified_to_publish() of its programs carry
-- a status confirmed inside that program's own tier interval, ON A SERVICE AREA THE
-- PROVIDER HAS CONFIRMED.
--
-- Two facts, not one, and the first run is why. With only the freshness half of the rule
-- the gate passed 130 ZIPs, every one a false positive: all 18 programs carried an
-- identical blanket assignment of 130 ZIPs from a county-level crosswalk expansion. WHAM
-- serves five (77042 77057 77063 77077 77082). Publishing on that would have put agencies
-- in front of people 40 miles outside their catchment -- the precise failure this product
-- exists to prevent, wearing the costume of coverage. Adding service_area_verified took
-- the count to the honest answer: 0 live, 3 one question away.
--
-- Status verification and service-area verification are separate facts and the call
-- establishes them separately: an agency can tell you they are accepting in ten seconds
-- and still need a follow-up question about catchment.
--
-- Design notes on the threshold:
--   * A place where every program is funds_exhausted STILL publishes. "Nothing is open
--     here this week" is true, useful, and the single most valuable thing this site can
--     say -- it stops somebody driving to a closed door. Requiring an 'accepting' program
--     would have suppressed exactly the pages that justify the product.
--   * Thin places stay dark. A page with one listing gets flattened by search and
--     embarrasses the freshness claim.
--   * Staleness handles itself: a record ages past its tier interval and drops out of the
--     count with no cron job and no manual unpublishing.

ALTER TABLE programs ADD COLUMN IF NOT EXISTS service_area_verified boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN programs.service_area_verified IS
 'True only when an agency confirmed its service area on a call AND program_zips reflects '
 'what they said. Crosswalk expansion from a county does not count: a third of Texas ZIPs '
 'cross a county line.';

CREATE OR REPLACE FUNCTION min_verified_to_publish() RETURNS integer AS $$
  SELECT 3;
$$ LANGUAGE sql IMMUTABLE;

DROP VIEW IF EXISTS zip_publish_status;
DROP VIEW IF EXISTS county_publish_status;
DROP VIEW IF EXISTS program_freshness;

CREATE VIEW program_freshness AS
SELECT p.program_id, p.slug, p.name, p.org_id, p.volatility_tier,
       p.current_status, p.last_verified_at, p.next_verify_due,
       p.service_area_verified,
       (p.last_verified_at IS NOT NULL
        AND p.current_status IS NOT NULL
        AND p.current_status <> 'unknown'
        AND p.service_area_verified
        AND now() <= p.last_verified_at + tier_interval(p.volatility_tier)) AS is_fresh,
       -- status confirmed but catchment not: the work is half done. This is what the VA
       -- console should surface as "one question away from publishable".
       (p.last_verified_at IS NOT NULL
        AND p.current_status IS NOT NULL
        AND p.current_status <> 'unknown'
        AND NOT p.service_area_verified)                                    AS needs_service_area
FROM programs p
WHERE p.removal_requested_at IS NULL;

CREATE VIEW zip_publish_status AS
SELECT z.zip,
       count(*) FILTER (WHERE f.is_fresh)                                    AS verified_programs,
       count(*) FILTER (WHERE f.needs_service_area)                          AS pending_service_area,
       count(*)                                                              AS total_programs,
       count(*) FILTER (WHERE f.is_fresh AND f.current_status = 'accepting') AS accepting_now,
       max(f.last_verified_at) FILTER (WHERE f.is_fresh)                     AS last_verified_at,
       (count(*) FILTER (WHERE f.is_fresh) >= min_verified_to_publish())     AS is_live
FROM zips z
LEFT JOIN program_zips pz ON pz.zip = z.zip
LEFT JOIN program_freshness f ON f.program_id = pz.program_id
GROUP BY z.zip;

CREATE VIEW county_publish_status AS
SELECT c.county_fips, c.name, c.state, c.slug,
       count(DISTINCT f.program_id) FILTER (WHERE f.is_fresh)             AS verified_programs,
       count(DISTINCT f.program_id) FILTER (WHERE f.needs_service_area)   AS pending_service_area,
       count(DISTINCT f.program_id)                                       AS total_programs,
       count(DISTINCT f.program_id) FILTER (WHERE f.is_fresh
             AND f.current_status = 'accepting')                          AS accepting_now,
       max(f.last_verified_at) FILTER (WHERE f.is_fresh)                  AS last_verified_at,
       (count(DISTINCT f.program_id) FILTER (WHERE f.is_fresh)
        >= min_verified_to_publish())                                     AS is_live
FROM counties c
LEFT JOIN program_counties pc ON pc.county_fips = c.county_fips
LEFT JOIN program_freshness f ON f.program_id = pc.program_id
GROUP BY c.county_fips, c.name, c.state, c.slug;
