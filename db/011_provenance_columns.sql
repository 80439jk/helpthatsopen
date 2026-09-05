-- Live schema carried a single free-text programs.source. The contract needs
-- four fields, because "where did this come from" has to be answerable when an
-- agency disputes a listing. Also adds zip_counties.area_ratio so the weaker
-- Census land-overlap signal stays visible next to HUD's res_ratio.
ALTER TABLE zip_counties ADD COLUMN IF NOT EXISTS area_ratio numeric(5,4);
ALTER TABLE programs ADD COLUMN IF NOT EXISTS source_name text;
ALTER TABLE programs ADD COLUMN IF NOT EXISTS source_url text;
ALTER TABLE programs ADD COLUMN IF NOT EXISTS source_retrieved_at date;
ALTER TABLE programs ADD COLUMN IF NOT EXISTS extraction_method text;
ALTER TABLE programs ADD COLUMN IF NOT EXISTS needs_source_verification boolean NOT NULL DEFAULT false;
UPDATE programs SET source_name = source
WHERE source_name IS NULL AND source IS NOT NULL AND source <> '';
