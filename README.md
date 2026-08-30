# Help That's Open — handoff

Everything needed to rebuild this in Cursor. Read `.cursorrules` first; it holds the
constraints that aren't obvious from the mockups.

## What's here

```
.cursorrules              Project guardrails — Cursor reads this automatically
docs/
  01-product-brief.md     What this is, who it's for, the value prop
  02-data-model.md        Listing schema, tags, VA priority scoring
  03-database.md          Postgres DDL, queue function, dialer integration
  04-site-architecture.md URL structure, schema.org, content strategy
  05-va-operations.md     Call script and operating model
design/
  prototype.html          Consumer site — landing + results, geo-switchable
  va-console.html         Verification console — agent + supervisor
  logo-system.html        Logo lockups, colorways, status variants
data/
  SOURCES.md              Where the seed data comes from
```

## Important: the HTML is a spec, not a starting point

Do **not** ask Cursor to convert `design/prototype.html` into the app. It's a
single-file mockup with inline data and no routing. Use it the way you'd use a Figma
file — read the design tokens, copy the exact strings, match the component shapes,
then build properly in Next.js.

The copy in those files is final and considered. Reuse the strings verbatim except
where noted below.

## One thing to rewrite in your own voice

The output in this repo was drafted with Claude, and Claude now embeds a
machine-readable watermark in generated text. It doesn't matter for schema, DDL, or
code — but it matters on the pages where "a human does this work" *is* the claim.

Rewrite these in your own words before launch (~1,500 words total):
- `/how-we-verify/`
- "Who keeps this current"
- The disclosure bar and footer disclaimer
- The value-prop band ("We don't take applications…")
- `/corrections/` policy text

Everything else is fine. Listing content comes off VA phone calls and is
human-sourced by construction.

## Build order

**1. Data layer first.** Run the DDL from `docs/03-database.md`. Seed geography
(ZIP↔county crosswalk, populations) before anything else — every query depends on it.

**2. Seed the Tier-A records.** The 35 Texas CEAP subrecipients covering all 254
counties, then the PHA list. Sources in `data/SOURCES.md`. About 1,500 records for the
ten-county launch.

**3. The program page.** Build `/programs/[slug]` before the county pages. It's the
smallest complete unit and it's the thing AI answer engines cite.

**4. County and ZIP pages** with ISR + on-demand revalidation on status change.

**5. The consumer landing/results flow** from `design/prototype.html`.

**6. The VA console.** It can be ugly and internal for a while — but ship the
append-only log and the two commit gates (note required on status change, read-back
step) from day one. Retrofitting data discipline doesn't work.

**7. Dialer integration.** Preview mode only. See `docs/03-database.md`.

## Launch scope

Ten Texas counties: Harris, Dallas, Tarrant, Bexar, Travis, Collin, Denton, Hidalgo,
El Paso, Fort Bend. Roughly 60% of the state population, ~1,500 records, under one
FTE of verification. Prove the workflow before expanding.

## Useful first prompts for Cursor

> Read .cursorrules and docs/. Set up a Next.js App Router project with Drizzle and
> Postgres. Implement the schema in docs/03-database.md exactly, including the
> append-only trigger on status_log and the rebuild_queue function. Don't scaffold
> any UI yet.

> Build /programs/[slug] as a server component. Use the design tokens in .cursorrules
> and match the listing card structure in design/prototype.html. Include the Service
> JSON-LD from docs/04-site-architecture.md. dateModified must come from the real
> last_verified_at.

> Build the county page at /[state]/[county]. Static with ISR. Emit the Dataset
> JSON-LD. Add an on-demand revalidation route that fires when a status_log row is
> inserted for any program serving that county.
