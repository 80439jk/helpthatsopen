-- NOT APPLIED. Review before running.
--
-- Supabase flags RLS as disabled on all 15 tables at critical priority: anyone holding
-- the anon key -- which ships to every browser by design -- can read AND WRITE every row.
-- The app only reads, so nothing breaks by locking writes down, but enabling RLS without
-- policies blocks all access, so this must go in as one piece.
--
-- Split by what the public actually needs:
--   PUBLIC READ  the directory itself. This data is meant to be on a web page.
--   NO PUBLIC ACCESS  staff, call_attempts, status_log, contacts, search_events,
--                     verification_queue. Operational data. status_log carries who said
--                     what on a recorded call; it should never be reachable with a
--                     browser key.
-- Writes belong to the service role, which bypasses RLS and never leaves the server.

ALTER TABLE zips             ENABLE ROW LEVEL SECURITY;
ALTER TABLE counties         ENABLE ROW LEVEL SECURITY;
ALTER TABLE zip_counties     ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations    ENABLE ROW LEVEL SECURITY;
ALTER TABLE programs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE program_zips     ENABLE ROW LEVEL SECURITY;
ALTER TABLE program_counties ENABLE ROW LEVEL SECURITY;
ALTER TABLE program_tags     ENABLE ROW LEVEL SECURITY;
ALTER TABLE corrections      ENABLE ROW LEVEL SECURITY;
ALTER TABLE local_facts      ENABLE ROW LEVEL SECURITY;

CREATE POLICY public_read ON zips             FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY public_read ON counties         FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY public_read ON zip_counties     FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY public_read ON organizations    FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY public_read ON programs         FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY public_read ON program_zips     FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY public_read ON program_counties FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY public_read ON program_tags     FOR SELECT TO anon, authenticated USING (true);
-- corrections: only rows the team marked public. The page is a trust asset, not a leak.
CREATE POLICY public_read ON corrections      FOR SELECT TO anon, authenticated USING (is_public);
CREATE POLICY public_read ON local_facts      FOR SELECT TO anon, authenticated USING (true);

-- Operational tables: RLS on, no policy. Denies anon and authenticated entirely; the
-- service role still has full access because it bypasses RLS.
ALTER TABLE staff              ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts           ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_attempts      ENABLE ROW LEVEL SECURITY;
ALTER TABLE status_log         ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_events      ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_queue ENABLE ROW LEVEL SECURITY;

-- search_events is written from the site to feed the demand signal, so it needs one
-- narrow exception: insert only, never read back with a browser key.
CREATE POLICY public_insert ON search_events FOR INSERT TO anon, authenticated WITH CHECK (true);

-- After running, confirm the app still renders: the views (program_freshness,
-- zip_publish_status, county_publish_status) inherit the policies of their base tables.
