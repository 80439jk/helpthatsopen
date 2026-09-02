-- CornerHelp schema v1
-- Supersedes the DDL in docs/03-database.md. Fixes A1-A6 and B2 from
-- docs/00-review-findings.md. Order matters: nothing forward-references.
--
-- Run: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/001_schema.sql

BEGIN;

-- ============ GEOGRAPHY ============
-- Seeded by scripts/ingest_geo.py from the Census relationship file.
-- No PostGIS: nothing in the documented queries uses a centroid, so the extension
-- is not a launch dependency (review D4). Add it, and a centroid column, if and
-- when distance sort is actually needed.
CREATE TABLE zips (
  zip           char(5) PRIMARY KEY,
  primary_state char(2) NOT NULL,
  population    integer            -- null until a Census API key backfills ZCTA population
);

CREATE TABLE counties (
  county_fips char(5) PRIMARY KEY,
  name        text  NOT NULL,
  state       char(2) NOT NULL,
  population  integer,
  slug        text  NOT NULL,
  UNIQUE (state, slug)             -- slugs need only be unique within a state
);

CREATE TABLE zip_counties (
  zip         char(5) NOT NULL REFERENCES zips,
  county_fips char(5) NOT NULL REFERENCES counties,
  res_ratio   numeric(5,4),        -- HUD household share. Preferred. Null until a HUD token.
  area_ratio  numeric(5,4),        -- Census land-area overlap. Interim, weaker (review D3).
  PRIMARY KEY (zip, county_fips)
);
CREATE INDEX ON zip_counties (county_fips);

-- ============ STAFF (A1 — was referenced but never defined) ============
CREATE TABLE staff (
  va_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name       text NOT NULL,
  email      text UNIQUE,
  role       text NOT NULL DEFAULT 'va' CHECK (role IN ('va','supervisor','admin')),
  is_active  boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ============ ORGS & PROGRAMS ============
CREATE TABLE organizations (
  org_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL,
  org_type      text NOT NULL CHECK (org_type IN
                ('caa','pha','food_bank','food_pantry','faith','municipal_utility',
                 'co_op','nonprofit','aaa','clinic','school_district','aic_211','other')),
  parent_org_id uuid REFERENCES organizations,
  website       text,
  main_phone    text,
  ein           text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  -- one org per name+type. Without this, ON CONFLICT DO NOTHING never fires and a
  -- re-run of the loader duplicates every organization.
  UNIQUE (name, org_type)
);

CREATE TABLE programs (
  program_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          uuid NOT NULL REFERENCES organizations,
  name            text NOT NULL,
  slug            text UNIQUE NOT NULL,
  volatility_tier char(1) NOT NULL CHECK (volatility_tier IN ('A','B','C','D')),

  -- practicals; superseded values are snapshotted into status_log.practicals (review B4)
  how_to_apply       text,
  documents_required text[],
  application_window text,
  hours              jsonb,
  languages          text[],
  daily_cap          integer,
  disqualifier       text,
  intake_phone       text,

  -- maintained by trigger only, never written directly
  current_status   text,
  last_verified_at timestamptz,
  next_verify_due  timestamptz,
  failed_attempts  smallint NOT NULL DEFAULT 0,

  -- provenance, carried from the ingestion contract
  source_name              text,
  source_url               text,
  source_retrieved_at      date,
  extraction_method        text,
  needs_source_verification boolean NOT NULL DEFAULT false,

  is_published         boolean NOT NULL DEFAULT true,
  removal_requested_at timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON programs (next_verify_due) WHERE is_published;

CREATE TABLE program_zips (
  program_id uuid   NOT NULL REFERENCES programs ON DELETE CASCADE,
  zip        char(5) NOT NULL REFERENCES zips,
  PRIMARY KEY (program_id, zip)
);
CREATE INDEX ON program_zips (zip);          -- hot path: ZIP -> programs

-- Counties the program DECLARES it serves, straight from the source.
-- docs/02-data-model.md calls service_counties "derived, for display and SEO only",
-- but it cannot be re-derived from program_zips: 34% of Texas ZIPs cross a county
-- line, so walking program_zips -> zip_counties picks up neighbouring counties the
-- program does not serve. Measured: that inflated population reach enough to push
-- rural multi-county providers above Harris County in the queue. Store what the
-- source said; use program_zips for lookup, program_counties for reach and for
-- deciding which county pages a program appears on (review D3).
CREATE TABLE program_counties (
  program_id  uuid   NOT NULL REFERENCES programs ON DELETE CASCADE,
  county_fips char(5) NOT NULL REFERENCES counties,
  PRIMARY KEY (program_id, county_fips)
);
CREATE INDEX ON program_counties (county_fips);

CREATE TABLE program_tags (
  program_id uuid NOT NULL REFERENCES programs ON DELETE CASCADE,
  tag        text NOT NULL,
  tag_type   text NOT NULL CHECK (tag_type IN ('need','trigger','eligibility')),
  PRIMARY KEY (program_id, tag)
);
CREATE INDEX ON program_tags (tag, tag_type);

-- ============ DIALER (A2 — must precede status_log) ============
CREATE TABLE contacts (
  contact_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          uuid NOT NULL REFERENCES organizations,
  name text, role text,
  phone           text NOT NULL,
  extension text, best_time text,
  do_not_call     boolean NOT NULL DEFAULT false,
  last_reached_at timestamptz
);

CREATE TABLE call_attempts (
  call_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  program_id     uuid NOT NULL REFERENCES programs,
  contact_id     uuid REFERENCES contacts,
  va_id          uuid REFERENCES staff,
  dialer_call_id text UNIQUE,
  started_at timestamptz, connected_at timestamptz, ended_at timestamptz,
  duration_sec   integer,
  disposition    text CHECK (disposition IN
                 ('reached','voicemail','no_answer','busy','wrong_number',
                  'callback_booked','refused','gatekeeper','disconnected')),
  recording_url  text,
  callback_at    timestamptz
);
CREATE INDEX ON call_attempts (program_id, started_at DESC);

COMMIT;
