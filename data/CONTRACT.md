# Ingestion contract

Every listing that enters the database passes through this contract, whoever or
whatever produced it. The validator (`scripts/validate_listings.py`) rejects rows that
fail; there is no manual override. A cooperative producer and a careless one get the
same treatment, which is the point.

## Format

JSONL — one listing object per line, UTF-8, no trailing commas.

## Required fields

| Field | Type | Rule |
|---|---|---|
| `org_name` | string | Legal or DBA name, verbatim from source. Never normalized by a model. |
| `program_name` | string | The program, not the org. One org → many rows. |
| `org_type` | enum | Must match the `organizations.org_type` CHECK constraint. |
| `volatility_tier` | `A`–`D` | Drives refresh interval. |
| `service_counties` | string[] | ≥1. Must all exist in the canonical county list for the state. |
| `current_status` | literal | **Must be `"unknown"`.** No exceptions, ever. |
| `last_verified_at` | literal | **Must be `null`.** Verification happens by phone, not by import. |
| `source_name` | string | Human name of the source document. |
| `source_url` | string | Direct URL to the document the row came from. |
| `source_retrieved_at` | ISO 8601 | When it was fetched. |
| `extraction_method` | enum | `deterministic_parse` \| `llm_pdf_extract` \| `manual` |
| `needs_source_verification` | bool | Forced `true` for any `llm_*` extraction method. |

## Optional

`city`, `phone` (E.164 or null), `url`, `service_zips` (string[], may be empty at
import), `geo_derivation` (`source_county` \| `source_zip` \| `crosswalk_expanded`),
`need_tags` (string[]).

## Rules the validator enforces

1. `current_status` is `unknown` and `last_verified_at` is null. A row arriving with a
   real status is a contract violation, not a convenience — it would publish an
   unverified claim.
2. All four provenance fields present and non-empty. When an agency disputes a listing
   you must be able to say where it came from.
3. `phone` is E.164 or null. A malformed or missing number is fine; an invented one is
   not. Nothing fills this field by inference.
4. Every county in `service_counties` exists in the canonical list for the state.
   This is the check that catches model artifacts — see below.
5. `(org_name, program_name)` is unique. Dedupe on the program, not the org.
6. `extraction_method` starting `llm_` forces `needs_source_verification: true`, and
   those rows are held out of publication until a human or a deterministic parse
   confirms them.

## Why rule 4 earns its place

The TDHCA subrecipient list was extracted from PDF by a language model. Texas has
exactly 254 counties, which makes the county list a known-truth constraint. The
extraction produced 256 distinct county names. The two extras were:

- `"Davis"` — not a Texas county. Split out of `"Jeff Davis"`, which was also present.
- `"LaSalle"` — a spelling variant of `"La Salle"`, also present.

Both came from the same row. Remove them and the set is exactly 254.

The same extraction also reported "47 of 47 organizations" while emitting 44, and
duplicated counties within three rows. None of those errors are visible by reading the
output; all of them fall out of a constraint check that takes milliseconds.

That is the general lesson and the reason this file exists: **model extraction is a
draft, and only a deterministic check makes it data.**
