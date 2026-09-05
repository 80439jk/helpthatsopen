-- County slugs are unique WITHIN a state, not globally.
--
-- The live schema carried UNIQUE (slug) on counties, which held while the only
-- market was Texas. 26 slugs collide the moment North Carolina and Florida
-- exist: liberty-county is in Texas and Florida, clay-county, franklin-county,
-- jackson-county and lee-county are in all three.
--
-- Globally-unique slugs were never needed. The URL already carries the state
-- (/texas/harris-county/), so (state, slug) is the real key -- which is what
-- db/001_schema.sql says. This brings the live database in line with it.
--
-- Any query that looks a county up by slug alone must also filter on state
-- after this, or it will match the wrong one.

ALTER TABLE counties DROP CONSTRAINT IF EXISTS counties_slug_key;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'counties'::regclass AND conname = 'counties_state_slug_key'
  ) THEN
    ALTER TABLE counties ADD CONSTRAINT counties_state_slug_key UNIQUE (state, slug);
  END IF;
END $$;

-- Applied to the live database 2026-09-05 along with 011, 012 and 013 below,
-- which reconcile three more places where the live schema (built 2026-08-31
-- from its own init_schema) had drifted from db/001_schema.sql.
