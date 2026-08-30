# Seed data sources

Ordered by how fast they turn into published records.

## Geography — do this first

| What | Source | Notes |
|---|---|---|
| ZIP ↔ county crosswalk | HUD USPS crosswalk files | Has `res_ratio` per ZIP-county pair. ZIPs cross county lines — model it as a junction table, not a column. |
| ZIP population | Census ZCTA tables | Feeds the `reach` component of the priority score. |
| County FIPS + population | Census | |

## Tier 1 — structured and published (~1,000–1,500 records, days of work)

| What | Source | Yield |
|---|---|---|
| Texas CEAP / WAP / CSBG subrecipients | TDHCA "Master List of Community Affairs Subrecipients" (PDF, updated periodically) | 35 orgs, county mappings included, covers all 254 counties |
| Public housing authorities | HUD PHA Contact Report by state | ~380–475 in TX depending on source |
| Food banks | Feeding Texas member list | 20 orgs covering all 254 counties |
| 211 Area Information Centers | Texas HHSC / United Ways of Texas | 25 AICs |
| Area Agencies on Aging | Texas HHSC | 28 |

The TDHCA subrecipient list is the single highest-value file. It gives you 35 Tier-A
orgs with authoritative county service areas, and cold-start scoring puts them at the
top of the verification queue automatically.

## Tier 2 — locator-scrapable (the real volume)

- **Food bank partner networks.** Each of the 20 Feeding Texas members publishes a
  partner/agency locator. Houston alone runs ~1,600 partners, San Antonio 530+,
  North Texas 400+. Expect 4,000–6,000 distinct sites statewide.
- **211 Texas database.** Largest single pool. Calibration point: one 19-county region
  lists 282 agencies and 722 programs. Statewide is plausibly 8,000–12,000 agencies.
  Check terms of use before bulk extraction — prefer their published API or a data
  agreement over scraping.
- **Municipal utility assistance** — Austin Energy, CPS Energy, El Paso Electric, plus
  co-op round-up funds.
- **Salvation Army corps** and **Catholic Charities** diocesan sites (15 TX dioceses).
- **McKinney-Vento homeless liaisons** — every one of 1,200+ TX districts has one, and
  essentially nobody aggregates them.

## Tier 3 — long tail

ProPublica Nonprofit Explorer API, filtered to Texas 501(c)(3)s with human-services
NTEE codes. Thousands of records, highly variable quality. Only worth mining after
Tiers 1 and 2 are live and verified.

## Rules for ingestion

- **Never publish an unverified record with a status.** Import sets `current_status`
  to `unknown` and `last_verified_at` to null. A record becomes publishable only after
  a VA confirms it.
- **Service area is ZIP-level.** If a source gives you counties, expand to ZIPs via the
  crosswalk and mark the derivation, because county-level is wrong often enough to burn
  trust on a first visit.
- **Deduplicate on org + program, not org.** One organization runs many programs with
  different statuses, funding cycles, and requirements. The program is the unit.
- **Keep the source and import date on every record.** When an agency disputes a
  listing, you need to say where it came from.
