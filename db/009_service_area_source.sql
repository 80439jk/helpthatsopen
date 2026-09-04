-- Applied to Supabase project vdursgkijnoqjprkbojo 2026-09-04.
--
-- service_area_verified was a boolean, which forced every service area into "a rep told
-- us" or "unknown". That is wrong in both directions.
--
-- A CEAP subrecipient's counties are not an opinion, they are a CONTRACT. TDHCA assigns
-- them and publishes the assignment. Asking BakerRipley which counties they serve is
-- asking them to recite their own grant agreement, and their answer is worse evidence
-- than the state document. Those agencies were blocked pending a call that could only
-- degrade what we already knew.
--
-- And a church food pantry does not serve all 130 ZIPs of Harris County — but no intake
-- worker can recite a ZIP list either. What they CAN say is "we cover Spring Branch" or
-- "we turn people away outside 610". Resolving that to ZIPs is our job, not theirs.
--
-- So the column records WHERE the service area came from, and the gate accepts the
-- sources that are actually authoritative:
--   contract  = the funding agreement defines it. No call needed.
--   published = the agency states it on its own site (WHAM's five ZIPs).
--   stated    = described on a call, in their terms, resolved by us.
--   inferred  = our guess from an address or a county. Does NOT publish.
ALTER TABLE programs ADD COLUMN IF NOT EXISTS service_area_source text
  CHECK (service_area_source IN ('contract','published','stated','inferred'));
UPDATE programs SET service_area_source = 'inferred' WHERE service_area_source IS NULL;
UPDATE programs SET service_area_verified = (service_area_source IN ('contract','published','stated'));

-- program_freshness / zip_publish_status / county_publish_status recreated to read
-- service_area_source instead of the boolean. See 007 for the rest of the gate.
