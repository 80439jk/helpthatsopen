# Database

## Two schemas existed, and this is how they were reconciled

`001_schema.sql`–`003_call_import.sql` were written from `docs/03-database.md` and tested
against a local Postgres 16. Separately, the Supabase project **helpthatsopen**
(`vdursgkijnoqjprkbojo`) had already been built from its own `init_schema` migration on
2026-08-31, carrying the 18 Harris programs and the research behind the call sheet.

The live schema turned out to have every defect from `docs/00-review-findings.md`: no
`verify_outcome`, no `practicals`, no `program_counties`, and the trigger missing both
the contactability fix and the `observed_at` guard.

Rather than overwrite a database holding work this repo did not have, `004`–`007` upgrade
the live schema in place. They are additive: no table dropped, no row deleted. `status_log`
was empty, so reshaping it cost nothing.

`001`–`003` remain the reference schema for a clean install.

| Migration | What it does |
|---|---|
| `004_fix_review_defects.sql` | A5, A6, B2, B4, D3 — outcome split, practicals snapshot, `program_counties`, `stated_service_area`, `blocked` disposition, guarded trigger, append-only enforcement |
| `005_fix_rebuild_queue.sql` | A3, A4, D5 — numeric cast, never-verified is maximal staleness, transactional swap |
| `006_queue_includes_unpublished.sql` | The deadlock: the queue filtered on `is_published`, but nothing is published until verified and nothing is verified until it comes off the queue |
| `007_launch_gate.sql` | D2 — `program_freshness`, `zip_publish_status`, `county_publish_status`, and `min_verified_to_publish()` |

## The launch gate

A ZIP or county is live when **at least 3 of its programs carry a status confirmed inside
that program's tier interval, on a service area the provider has confirmed**.

Two facts, not one. Status verification and service-area verification are separate, and
the first run proved why: the gate initially passed 130 ZIPs, every one a false positive,
because all 18 programs carried an identical blanket assignment of 130 ZIPs. WHAM serves
five. Publishing on that would have put agencies in front of people 40 miles outside their
catchment — the exact failure this product exists to prevent, wearing the costume of
coverage.

Change the threshold by replacing `min_verified_to_publish()`. Nothing else needs to move.
