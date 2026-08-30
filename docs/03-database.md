# Database and dialer integration

Postgres. At 12k programs and ~250k service-area rows this is a small database — no sharding, no partitioning, no exotic infrastructure. The only unusual thing is that **status is never updated, only appended.**

## Part 1 — Core tables

```sql
-- ============ GEOGRAPHY ============
-- Seed from the HUD ZIP–county crosswalk + Census ZCTA population.
-- A ZIP can span counties, so this is a junction, not a column on zips.
CREATE TABLE zips (
  zip           char(5) PRIMARY KEY,
  primary_state char(2) NOT NULL,
  population    integer,
  centroid      geography(Point,4326)
);

CREATE TABLE counties (
  county_fips char(5) PRIMARY KEY,
  name        text NOT NULL,
  state       char(2) NOT NULL,
  population  integer,
  slug        text UNIQUE NOT NULL          -- 'harris-county'
);

CREATE TABLE zip_counties (
  zip         char(5) REFERENCES zips,
  county_fips char(5) REFERENCES counties,
  res_ratio   numeric(5,4),                 -- share of ZIP's households in this county
  PRIMARY KEY (zip, county_fips)
);

-- ============ ORGS & PROGRAMS ============
CREATE TABLE organizations (
  org_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name       text NOT NULL,
  org_type   text NOT NULL CHECK (org_type IN
             ('caa','pha','food_bank','food_pantry','faith','municipal_utility',
              'co_op','nonprofit','aaa','clinic','school_district','aic_211','other')),
  parent_org_id uuid REFERENCES organizations,  -- food bank → partner pantries
  website    text,
  main_phone text,
  ein        text,                              -- enables ProPublica enrichment
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE programs (
  program_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id         uuid NOT NULL REFERENCES organizations,
  name           text NOT NULL,
  slug           text UNIQUE NOT NULL,          -- 'bakerripley-ceap'
  volatility_tier char(1) NOT NULL CHECK (volatility_tier IN ('A','B','C','D')),

  -- practicals, overwritten on each verification (history lives in status_log)
  how_to_apply       text,
  documents_required text[],
  application_window text,
  hours              jsonb,
  languages          text[],
  daily_cap          integer,
  disqualifier       text,                      -- verbatim, from script step 4
  intake_phone       text,

  -- derived from status_log by trigger, never written directly
  current_status     text,
  last_verified_at   timestamptz,
  next_verify_due    timestamptz,
  failed_attempts    smallint NOT NULL DEFAULT 0,

  is_published   boolean NOT NULL DEFAULT true,
  removal_requested_at timestamptz,             -- honored same-day, kept for audit
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE program_zips (
  program_id uuid REFERENCES programs ON DELETE CASCADE,
  zip        char(5) REFERENCES zips,
  PRIMARY KEY (program_id, zip)
);
CREATE INDEX ON program_zips (zip);            -- the hot path: ZIP → programs

CREATE TABLE program_tags (
  program_id uuid REFERENCES programs ON DELETE CASCADE,
  tag        text NOT NULL,
  tag_type   text NOT NULL CHECK (tag_type IN ('need','trigger','eligibility')),
  PRIMARY KEY (program_id, tag)
);
CREATE INDEX ON program_tags (tag, tag_type);
```

## Part 2 — The append-only log

This is the table the whole product rests on. Nothing here is ever updated or deleted.

```sql
CREATE TABLE status_log (
  entry_id      bigserial PRIMARY KEY,
  program_id    uuid NOT NULL REFERENCES programs,
  observed_at   timestamptz NOT NULL DEFAULT now(),
  status        text NOT NULL CHECK (status IN
                ('accepting','waitlist','funds_exhausted','seasonal_closed',
                 'appointment_only','unknown')),
  verify_method text NOT NULL CHECK (verify_method IN
                ('phone','email','web','agency_self_report','partial','unreachable')),
  va_id         uuid REFERENCES staff,
  spoke_with    text,                           -- 'Denise, intake'
  funds_last_until text,                        -- 'around the 8th–10th'
  reopens_on    date,
  note          text,                           -- REQUIRED on status change
  call_id       uuid REFERENCES call_attempts,
  null_reasons  jsonb                           -- {"documents_required":"didn't_know"}
);
CREATE INDEX ON status_log (program_id, observed_at DESC);

-- No UPDATE, no DELETE. Ever.
REVOKE UPDATE, DELETE ON status_log FROM app_user;
```

Denormalize the latest entry onto `programs` so page reads are a single row:

```sql
CREATE OR REPLACE FUNCTION apply_status_log() RETURNS trigger AS $$
BEGIN
  UPDATE programs SET
    current_status   = NEW.status,
    last_verified_at = NEW.observed_at,
    next_verify_due  = NEW.observed_at + (
      CASE volatility_tier WHEN 'A' THEN interval '14 days'
                           WHEN 'B' THEN interval '45 days'
                           WHEN 'C' THEN interval '90 days'
                           ELSE interval '180 days' END),
    failed_attempts  = CASE WHEN NEW.verify_method = 'unreachable'
                            THEN failed_attempts + 1 ELSE 0 END
  WHERE program_id = NEW.program_id;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_status_log AFTER INSERT ON status_log
  FOR EACH ROW EXECUTE FUNCTION apply_status_log();
```

**Why append-only matters commercially:** it's what lets you say "reopened Nov 3," emit `SpecialAnnouncement` schema on change, show an agency their own history when they dispute a listing, and prove the freshness claim to a reviewer. It's also the only defence if someone ever alleges the site published a false status.

## Part 3 — Demand signal and the priority queue

```sql
CREATE TABLE search_events (
  event_id   bigserial PRIMARY KEY,
  zip        char(5),
  need_tag   text,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON search_events (zip, occurred_at DESC);
```

Priority is recomputed nightly into a plain table — cheap, and it means the console reads one indexed table.

```sql
CREATE TABLE verification_queue (
  program_id uuid PRIMARY KEY REFERENCES programs,
  score      numeric(5,2) NOT NULL,
  reach      numeric(5,2), volatility numeric(5,2),
  staleness  numeric(5,2), demand numeric(5,2), contactability numeric(5,2),
  computed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON verification_queue (score DESC);

CREATE OR REPLACE FUNCTION rebuild_queue() RETURNS void AS $$
  TRUNCATE verification_queue;
  INSERT INTO verification_queue
  SELECT p.program_id,
         ROUND(0.30*reach + 0.25*vol + 0.25*stale + 0.15*dem + 0.05*contact, 2),
         reach, vol, stale, dem, contact, now()
  FROM programs p
  CROSS JOIN LATERAL (SELECT
    -- reach: log-normalized population of served ZIPs
    LEAST(100, 100 * ln(1 + COALESCE(
      (SELECT SUM(z.population) FROM program_zips pz
        JOIN zips z ON z.zip = pz.zip WHERE pz.program_id = p.program_id),0)) / ln(1+8000000)) AS reach,
    CASE p.volatility_tier WHEN 'A' THEN 100 WHEN 'B' THEN 65
                           WHEN 'C' THEN 35 ELSE 15 END AS vol,
    LEAST(100, GREATEST(0,
      100 * EXTRACT(epoch FROM now() - COALESCE(p.last_verified_at, now() - interval '1 year'))
          / NULLIF(EXTRACT(epoch FROM p.next_verify_due - p.last_verified_at),0))) AS stale,
    LEAST(100, COALESCE((SELECT COUNT(*)::numeric FROM search_events se
       JOIN program_zips pz ON pz.zip = se.zip
       WHERE pz.program_id = p.program_id
         AND se.occurred_at > now() - interval '30 days'),0) / 5) AS dem,
    GREATEST(0, 100 - p.failed_attempts * 20) AS contact
  ) s
  WHERE p.is_published AND p.removal_requested_at IS NULL;
$$ LANGUAGE sql;
```

Run it nightly. Cold start works correctly on its own: with `last_verified_at` null, staleness pins at 100 and the big-reach Tier A records float to the top — which is the 35 CEAP subrecipients, exactly where week one should start.

## Part 4 — Dialer integration

```sql
CREATE TABLE contacts (
  contact_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id     uuid NOT NULL REFERENCES organizations,
  name       text, role text, phone text NOT NULL, extension text,
  best_time  text,
  do_not_call boolean NOT NULL DEFAULT false,   -- honors removal requests
  last_reached_at timestamptz
);

CREATE TABLE call_attempts (
  call_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  program_id    uuid NOT NULL REFERENCES programs,
  contact_id    uuid REFERENCES contacts,
  va_id         uuid REFERENCES staff,
  dialer_call_id text UNIQUE,                   -- provider's ID, for reconciliation
  started_at    timestamptz, connected_at timestamptz, ended_at timestamptz,
  duration_sec  integer,
  disposition   text CHECK (disposition IN
                ('reached','voicemail','no_answer','busy','wrong_number',
                 'callback_booked','refused','gatekeeper','disconnected')),
  recording_url text,
  callback_at   timestamptz
);
CREATE INDEX ON call_attempts (program_id, started_at DESC);
```

### Use preview dialing, not predictive

This matters more than it sounds. The whole script depends on **assume-and-confirm** — the VA reading prefilled facts back as statements. That only works if the record is on screen *before* the agency picks up. Predictive dialing connects the agent first and loads context second, which collapses the technique into "what are your hours?" and the data quality goes with it.

These are also business lines, not consumers, so there's no volume argument for predictive. Preview costs you throughput you don't need and buys you the data quality that is the entire product.

**Flow:**

```
Nightly    rebuild_queue()
             ↓
Shift start  console pulls top N by score, locks them to the VA
             (SELECT ... FOR UPDATE SKIP LOCKED — no two VAs get the same record)
             ↓
Per call     VA clicks Dial → POST /dialer/calls {to, from, agent_id, metadata:{program_id}}
             record already rendered on screen
             ↓
Live         dialer webhook → POST /webhooks/dialer
             events: ringing / answered / ended
             ↓
Wrap         VA commits → INSERT status_log (with call_id)
             → trigger updates programs
             → if status changed, emit SpecialAnnouncement + invalidate county page cache
```

**Webhook contract:**

```json
POST /webhooks/dialer
{
  "dialer_call_id": "CA9f2...",
  "event": "ended",
  "metadata": { "program_id": "uuid", "va_id": "uuid" },
  "disposition": "reached",
  "duration_sec": 168,
  "recording_url": "https://.../CA9f2.mp3",
  "occurred_at": "2026-08-30T14:12:04Z"
}
```

Verify the signature, upsert on `dialer_call_id`, and **never** let a webhook write to `status_log` — only a VA commit does that. The dialer records what happened on the phone; the VA records what was said.

**Two operational things that will bite you:**

Register your outbound number properly — STIR/SHAKEN attestation and branded caller ID. A call-center number cold-dialing nonprofits gets flagged "Scam Likely" within weeks, and your reach rate is the input to the entire staffing model. A 60% reach rate becoming 35% doubles your headcount.

Set `contacts.do_not_call` on any removal request and enforce it at the dialer push, not just in the UI. These are business lines so the DNC registry doesn't apply, but honoring it anyway is what makes the claim-your-listing supply side possible.

## Part 5 — Corrections (public)

```sql
CREATE TABLE corrections (
  correction_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  program_id  uuid NOT NULL REFERENCES programs,
  reported_by text CHECK (reported_by IN ('agency','user','internal')),
  reported_at timestamptz NOT NULL DEFAULT now(),
  field       text, was text, now_is text,
  resolved_at timestamptz,
  is_public   boolean NOT NULL DEFAULT true
);
```

Renders `/corrections/` — dated, public, and the single strongest trust signal on the site. It's what `correctionsPolicy` in the schema.org markup points at.

## Part 6 — Which dialer, and the number strategy

### The recommendation

**Don't reuse the lead-gen dialer's numbers.** Whatever platform runs the consumer outbound side has a number reputation profile built by high-volume consumer dialing. Verification calls to nonprofit intake lines need the opposite reputation, and the two will contaminate each other. Separate numbers at minimum; separate platform is cleaner.

Three viable paths, in order of how fast you'd be live:

**1. JustCall or Kixie — fastest.** Working softphone, click-to-dial, call recording, webhooks, and a REST API out of the box. You'd be dialing in days rather than weeks, and at 1–5 seats the cost is noise. The trade is that you're embedding their dialer next to the console rather than inside it.

**2. Twilio Voice + Voice JS SDK — most control.** This is what the console mock actually depicts: the dialer bar is part of the app, `program_id` rides in the call metadata, and every event hits your own webhook. Preview dialing is trivial to build because you're just placing one outbound call at a time. Twilio also has the cleanest path to branded calling. Budget a couple of weeks of dev.

**3. Telnyx — same shape as Twilio, usually cheaper,** with better number-reputation tooling. Worth a look if per-minute cost matters, though at ~148k dials a year it won't.

**Skip:** Five9, Genesys, NICE. Enterprise contact-center suites priced and scoped for hundreds of seats.

At your volume the platform decision is low-stakes. **The number decision is not.**

### Vanity number vs. branded caller ID — two different things

A vanity number is a memorable digit string (1-800-FLOWERS). Branded caller ID is the **name that displays** when the phone rings. You asked for the first; the thing that actually fixes reach rate is the second.

**Outbound verification calls:** the display name is worth more than any other single investment in this operation. An unlabeled 713 number reads as spam to an intake coordinator who's been dodging robocalls all morning. "HELP THATS OPEN" reads as a real organization and gets picked up.

Practical constraints:
- **CNAM is 15 characters, and mobile carriers largely ignore it.** "HELP THATS OPEN" is exactly 15 with spaces, so it fits — but only on landlines, and half your targets answer on mobile.
- For mobile you need a branded calling program: Twilio Branded Calls, First Orion, Hiya Connect, or TransUnion/Neustar BCD. These are per-carrier deals; the aggregators cover several at once.
- All of it requires **STIR/SHAKEN A-attestation**, which requires you own the number and have a verified business identity on file. Do this before the first dial, not after the reputation is damaged.

**Use local numbers for outbound, not toll-free.** A Houston nonprofit answers a 713 number materially more often than an 800 number. One local presence number per metro you're verifying — that's what the outbound lines table in the supervisor view is tracking.

**The vanity number belongs on the consumer inbound line.** That's where memorability pays: the "Or call ___" on every listing page, the sticky mobile bar, the text-me-this-list flow. One toll-free vanity number inbound, local DIDs outbound.

### Monitoring it

Reach rate per outbound line is the leading indicator, and it degrades before anyone notices. Check spam labeling monthly across the major carriers, and treat a line dropping below ~45% as a number to retire rather than a problem to argue with. Rotating a burned number is cheap; discovering it after a quarter of missed verifications is not.
