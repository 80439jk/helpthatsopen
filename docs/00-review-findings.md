# Repo review — findings

Review of the spec as it stands before any code is written. Six defects in
`03-database.md` were reproduced against a real Postgres 16 instance; those are marked
**verified**. Everything else is a documented contradiction or a gap.

Nothing here is an argument with the product thinking. The positioning, the moat, and
the VA script are sound. These are the things that will cost days if they reach code.

---

## A. Blocking — the DDL as written does not run

### A1. The `staff` table is never defined — **FIXED 2026-09-02**
Defined in db/001_schema.sql with va_id, name, email, role, is_active.

`status_log.va_id` and `call_attempts.va_id` both declare `REFERENCES staff`, and no
`CREATE TABLE staff` exists anywhere in the repo. Running Part 1 → Part 2 in order
halts here:

```
ERROR:  relation "staff" does not exist
```

Needs defining before `status_log`, with at minimum `va_id`, name, and active flag —
the QA model in `05-va-operations.md` also implies role (VA vs supervisor).

### A2. `status_log` forward-references `call_attempts` — **FIXED 2026-09-02**
contacts and call_attempts now precede status_log in db/001_schema.sql.

`status_log.call_id REFERENCES call_attempts` appears in Part 2; `call_attempts` is
created in Part 4. Move `contacts` and `call_attempts` ahead of `status_log`, or add
the FK afterward with `ALTER TABLE`.

### A3. `rebuild_queue()` does not compile — **FIXED 2026-09-02**
Cast to numeric before ROUND. Function compiles and returns a row count.

```
ERROR:  function round(double precision, integer) does not exist
```
`ln()` returns double precision, so the whole weighted sum is double, and Postgres has
no `round(double precision, integer)` — only `round(numeric, integer)`. Cast the sum:
`ROUND((0.30*reach + ...)::numeric, 2)`. The five component columns need the same cast
to land in their `numeric(5,2)` columns.

### A4. Cold-start staleness is 0, not 100 — **FIXED 2026-09-02**
Never-verified is now explicitly 100. Measured cold-start score 74.75, was 49.75.

The doc states: *"with `last_verified_at` null, staleness pins at 100."* It does not.
With both `last_verified_at` and `next_verify_due` null, the denominator
`NULLIF(EXTRACT(epoch FROM p.next_verify_due - p.last_verified_at), 0)` is NULL, so the
division is NULL — and **Postgres `GREATEST`/`LEAST` ignore NULL arguments** rather
than propagating them. `GREATEST(0, NULL)` returns `0`.

Measured, one Tier-A record covering a 35k-population ZIP, never verified:

| component | value |
|---|---|
| reach | 65.83 |
| volatility | 100.00 |
| **staleness** | **0.00**  ← doc expects 100 |
| demand | 0.00 |
| contactability | 100.00 |
| **score** | **49.75**  ← doc expects ~74.75 |

Day-one ordering survives by luck: reach + volatility still float the Tier-A records to
the top, which is why this would not be noticed in week one. The real damage is
ongoing — **a record that has never been verified never accrues staleness at all.**
The component designed to make the queue self-feeding is dead for exactly the records
that have never been touched. A low-reach Tier-C record imported on day one can sit at
the bottom forever.

Fix: coalesce the interval from the tier rather than from `next_verify_due`, so an
unverified record has a real denominator.

### A5. The three-attempt rule resets `contactability` to full — **FIXED 2026-09-02**
failed_attempts resets only on outcome reached/partial. Measured: 4 attempts -> contactability 20, was resetting to 100.

`05-va-operations.md` says: after three attempts the record drops to `unknown` with a
public note, and *"`contactability` decays so it stops recirculating."*

The trigger says:
```sql
failed_attempts = CASE WHEN NEW.verify_method = 'unreachable'
                       THEN failed_attempts + 1 ELSE 0 END
```
That final "drop to unknown" write is a VA commit, so its `verify_method` is `phone`
(or `partial`) — not `unreachable`. Measured:

| step | failed_attempts | contactability |
|---|---|---|
| after 3 × `unreachable` | 3 | 40 |
| after the documented "drop to unknown" commit | **0** | **100** |

The record returns to the queue at full contactability. The mechanism does the exact
opposite of what the operating model claims. Either that final commit uses a distinct
method, or `failed_attempts` resets only on a *successful contact* status rather than
on any non-`unreachable` method.

### A6. A backfilled log entry overwrites newer status and moves freshness backwards — **FIXED 2026-09-02**
Trigger guarded on observed_at >= last_verified_at. Measured: backfilled entry is logged but does not overwrite.

`apply_status_log()` writes `NEW` unconditionally. Any entry inserted out of
chronological order — a backfill, a delayed sync, a VA correcting yesterday's call —
overwrites current state with older data. Measured:

| step | current_status | last_verified_at |
|---|---|---|
| today's call logged | `accepting` | 2026-09-02 |
| a 10-day-old call backfilled | **`funds_exhausted`** | **2026-08-23** |

`last_verified_at` travels *backwards*, and since `dateModified` in the JSON-LD is
sourced from it, the page now publishes a false freshness timestamp and a false status.
This breaks `.cursorrules` rule 7 ("Never fabricate freshness") through the mechanism
built to enforce it. Guard the UPDATE:
`AND (last_verified_at IS NULL OR NEW.observed_at >= last_verified_at)`.

---

## B. Contradictions between documents

### B1. Two different URL schemes — **RESOLVED 2026-09-02**
Settled on `/texas/`. `.cursorrules` updated: state segment is the full state name,
both feed paths documented (`/data/[state].json` roll-up, `/data/[state]/[county].json`
per county). Reason recorded in `.cursorrules`. Original finding below for history.

`.cursorrules` specifies `/tx/harris-county/`, `/tx/77021/`. `04-site-architecture.md`
specifies `/texas/harris-county/`, `/texas/77021/`, and the `@id` values in the
JSON-LD examples use `/texas/`. Cursor reads `.cursorrules` automatically, so it will
build `/tx/` and every schema example will be wrong. Pick one before the first route.

The machine-readable feed has three shapes across the docs: `/data/[state].json`,
`/data/texas.json`, and `/data/texas/harris-county.json` (in the `Dataset`
`distribution.contentUrl`). County-level feeds and a state feed are different things —
decide whether both exist.

### B2. `verify_method` has two definitions — **FIXED 2026-09-02**
Split into verify_method (channel) and verify_outcome (result) in db/002_status_log.sql.

`02-data-model.md`: `phone | email | web | agency_self_report`.
`03-database.md` CHECK: adds `partial` and `unreachable`.

Beyond the mismatch, `partial` and `unreachable` are *outcomes*, not methods. Folding
them into the same column means an unreachable attempt loses the channel — you can no
longer ask "what's our phone reach rate," which `03-database.md` itself calls the
leading indicator that drives the staffing model. Split into `verify_method` and
`verify_outcome`. That also cleanly fixes A5.

### B3. `trigger_tags` collection contradicts the data-minimization rule
`.cursorrules` rule 1: *"The only user data we collect is ZIP, an optional phone/email
for alerts, and the need category. **Nothing else.**"*

`02-data-model.md` 5b: trigger tags are *"captured from the user at ZIP entry"* and are
*"the single most commercially valuable field on the site."*

A life-event trigger is not a need category. Both positions are defensible; they cannot
both be in force. Worth resolving deliberately — see D1.

### B4. Practicals history is claimed but not stored — **FIXED 2026-09-02**
status_log.practicals jsonb snapshot; the trigger applies it to programs via COALESCE.

`programs` marks `how_to_apply`, `documents_required`, `application_window`, `hours`,
`daily_cap`, `disqualifier` as *"overwritten on each verification (history lives in
status_log)."* `status_log` has no columns for any of them. The prior values are simply
lost on overwrite. Either add a `practicals jsonb` snapshot to `status_log` or drop the
claim — the append-only guarantee is a core trust asset and shouldn't be overstated.

---

## C. Leftovers from the rename, and repo hygiene

### C1. Corrupted markup in the opening script line
`05-va-operations.md` step 1 contains a botched find-and-replace:
```
<b><u style=CornerHelpcolor:#1B7A4BCornerHelp>CornerHelp</u></b>
```
The correct form appears later in Part 4. This is the *first sentence a VA reads aloud*
— worth fixing before anyone is trained on it.

Separately: why is there HTML in the script at all? And the brand is styled
`#1B7A4B`, which is `--open`, the status green. `.cursorrules` is explicit that crimson
is brand and green means "accepting." The script docs contradict the token rules.

### C2. Stale brand in the CNAM section
`03-database.md` still argues the caller-ID name at length using `"HELP THATS OPEN"`,
including *"is exactly 15 with spaces, so it fits."* `CORNERHELP` is 10 characters, so
the constraint that drives the paragraph no longer binds. The branded-calling advice
underneath it is still correct and worth keeping.

### C3. `design/` and `preview/` have drifted
Two copies of every mockup, and they differ:

| file | difference |
|---|---|
| `prototype.html` | 185 changed lines |
| `logo-system.html` | 62 changed lines |
| `va-console.html` | 2 changed lines |

`README.md` documents `design/` only and never mentions `preview/`. Whichever is
canonical, the other should go — "the HTML is a spec, not a starting point" only works
if there is one spec.

### C4. The watermark claim in the README
The README instructs rewriting ~1,500 words because *"Claude now embeds a
machine-readable watermark in generated text."* I don't believe that is true of text
output, and it should be checked before the effort is spent. The underlying instinct —
that pages claiming *"a human does this work"* should be in your own voice — stands on
its own as an authenticity argument, and probably applies to fewer pages than the list.

---

## D. Gaps worth closing before code

### D1. The commercial layer needs a written boundary — **RESOLVED 2026-09-02**
Settled: energy allowed on `new_lease`/`relocation`, ruled out on
`utility_shutoff_notice`, plus a timing gate (two specific referrals with what-to-bring
before any commercial mention). Now `.cursorrules` rule 5, with the reasoning attached.
Original finding below for history.

`01-product-brief.md` promises commercial products are *"discovered in the interview,
never pre-sold on the page,"* and proposes measuring time-to-first-commercial-mention
on recordings. `02-data-model.md` builds the trigger→product mapping that makes the
call commercially efficient. The Medicare and ACA carve-outs are handled well and for
the right reason (consent doesn't travel).

The unguarded case is energy. `utility_shutoff_notice` and `new_lease` both map to a
retail electric pitch, and those are the two highest-volume triggers on a site about
utility shutoffs. Nothing in `.cursorrules` constrains it. If the answer is "energy is
fine, Medicare and ACA are not," that belongs in the non-negotiables with the reason,
because the distinction is not self-evident to whoever staffs this in a year.

### D2. No launch gate
Cold start sets every record to `unknown`. The homepage spec calls for a live status
band reading *"1,204 of 11,840 programs accepting today"* above the fold, and
`.cursorrules` rule 7 says unpublish a county rather than serve stale statuses. On day
one that band reads *"0 of 1,500."*

Missing rule: what fraction of a county's records must be verified before that county
page ships? It determines the whole launch sequence — the first week of calls is a
gating dependency, not a parallel workstream.

### D3. County derivation is unspecified — **FIXED 2026-09-02**
program_counties table stores the declared counties. Re-deriving them from program_zips inflated reach enough to rank rural multi-county providers above Harris County; measured and fixed.

`SOURCES.md` says to expand county-level sources to ZIPs *"and mark the derivation."*
`program_zips` has no derivation column and no `res_ratio`. Since county pages are
built by joining through `zip_counties`, a program serving one edge ZIP that clips a
county appears on that county's page as a local program. `zip_counties.res_ratio`
exists to threshold this; no rule uses it. The county page is called "the money page" —
worth getting right.

### D4. PostGIS is a hidden dependency
`zips.centroid` is `geography(Point,4326)`, which requires `CREATE EXTENSION postgis`.
Not mentioned in the stack or the DDL. Both Neon and Supabase support it, but it is a
provisioning step. Nothing in the documented queries actually uses the centroid — if
distance sort isn't in scope for v1, dropping the column removes the dependency.

### D5. `rebuild_queue()` empties the queue while it runs — **FIXED 2026-09-02**
Builds into a temp table and swaps inside one transaction.

`TRUNCATE` then `INSERT` in a plain SQL function. Between the two, `verification_queue`
is empty. It runs nightly, so a VA on a late shift can pull an empty queue. Build into
a temp table and swap, or run inside an explicit transaction. Also worth confirming the
interaction with the `FOR UPDATE SKIP LOCKED` pull described in Part 4 — `TRUNCATE`
takes an `ACCESS EXCLUSIVE` lock and will block behind an open shift lock.

---

## Suggested order

1. A1–A3 — the schema won't run without them.
2. B1 — decide the URL scheme before any route exists. Cheapest now, most expensive later.
3. A4–A6 — the three correctness bugs. A6 is the one with compliance exposure.
4. B2 — split method from outcome; it fixes A5 properly rather than patching it.
5. C1–C3 — cheap, and C1 is customer-facing via the VA.
6. D1, D2 — decisions, not code, but they gate the build.

---

## E. Google Ads policy — checked 2026-09-02

The Government documents and services policy restricts ads promoting **"direct
acquisition or access to"** government documents and services. CornerHelp does not
facilitate acquisition — no forms, no filing, no representation — so it sits outside
the restriction. `.cursorrules` rules 1 and 3 are what keep it there.

**The October 5, 2026 change is an allowance, not a tightening.** It opens a path for
*authorized* providers to advertise acquisition. The bar: the advertiser's domain must
be linked from an official, publicly accessible government website and explicitly
referenced as authorized. Commercial contracts, business licenses, and registrations
are explicitly invalid forms of authorization.

**Consequence worth recording: that safe harbor is unavailable to this property.**
CornerHelp will never be linked from a TDHCA or HUD page as an authorized provider. So
if the site ever drifted into looking like direct acquisition, there would be no
certification path back. The banned-CTA list in rule 3 is therefore load-bearing
compliance infrastructure, not tone guidance — every phrase on it ("see if you
qualify", "apply now", "claim your benefits") moves the property toward acquisition.

**The residual risk is Misrepresentation, not this policy** — the same family that
produced the cloaking suspension on the sister property. That one is settled by
enforcement rather than by reading, which means a live test:

1. Build one county page completely — real listings, real statuses, disclosure bar.
2. Run a small campaign at it before building the remaining 253.
3. **Separate Google Ads account, separate billing profile.** Policy strikes cascade
   across accounts sharing a payment profile, and there is existing suspension history
   on the sister property. The experiment does not sit next to the earner.

Sources: support.google.com/adspolicy/answer/17260489, support.google.com/adspolicy/answer/13156083

---

## F. Fixes applied 2026-09-02

`db/001_schema.sql` and `db/002_status_log.sql` supersede the DDL in
`03-database.md`. Loaded clean against Postgres 16 and regression-tested: every
defect above reproduces on the old DDL and does not on the new.

Two problems the seed load surfaced that no amount of reading would have:

**Organizations duplicated on every run.** `ON CONFLICT DO NOTHING` needs a
uniqueness key to conflict against. Without `UNIQUE (name, org_type)` the loader
produced 119 organizations from 44. Fixed and confirmed idempotent — a second run
inserts zero.

**Reach could not be computed, then computed wrongly.** `zips.population` is null
until a Census API key is available, so `SUM(z.population)` was 0 and every record
scored an identical 55.00 — the queue could not rank at all. Falling back to county
population fixed the tie, but walking `program_zips -> zip_counties -> counties`
re-expanded through cross-county ZIPs and picked up neighbouring counties the
program does not serve. With 34% of Texas ZIPs crossing a line, that inflated reach
enough to rank rural multi-county providers above Harris County. `program_counties`
now stores what the source declared. The queue's top eight now match the standalone
call-sheet ranking exactly, which is the cross-check that says both are right.

Still open: `res_ratio` (HUD token) and ZCTA population (Census key). Both free.
