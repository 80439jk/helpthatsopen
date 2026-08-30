# Listing schema — Texas resource directory

## 1. Core record

| Field | Type | Notes |
|---|---|---|
| `listing_id` | uuid | |
| `org_name` | text | Legal/DBA name |
| `program_name` | text | The *program*, not the org. One org = many listings. |
| `parent_org_id` | uuid | For multi-site orgs (food bank → 1,600 partners) |
| `org_type` | enum | `caa` `pha` `food_bank` `food_pantry` `faith` `municipal_utility` `co_op` `nonprofit` `aaa` `clinic` `school_district` `aic_211` |
| `phone` / `url` / `address` / `lat` / `lng` | | |

## 2. Service area — ZIP, not county

County-level is wrong often enough to burn trust on the first visit.

| Field | Type |
|---|---|
| `service_zips[]` | text[] — the authoritative field |
| `service_counties[]` | text[] — derived, for display and SEO only |
| `remote_ok` | bool — phone/online application accepted |

## 3. Status layer (the moat)

| Field | Type | Notes |
|---|---|---|
| `status` | enum | `accepting` `waitlist` `funds_exhausted` `seasonal_closed` `appointment_only` `unknown` |
| `last_verified_at` | timestamptz | Rendered on the card. This is the product. |
| `verified_by` | uuid | VA id |
| `verify_method` | enum | `phone` `email` `web` `agency_self_report` |
| `next_verify_due` | timestamptz | computed from volatility tier |
| `status_log[]` | append-only | `{ts, status, method, va_id, note}` — never mutate, only append |

**Volatility tiers → refresh interval**

| Tier | What | Interval |
|---|---|---|
| A | Funds-cycling: CEAP, emergency rent, utility crisis funds | 14 days |
| B | Waitlists: PHA lists, voucher programs | 45 days |
| C | Stable: pantries, clinics, weatherization | 90 days |
| D | Static: 211 AICs, statewide hotlines | 180 days |

## 4. Practicals — the fields nobody else publishes

| Field | Type |
|---|---|
| `how_to_apply` | enum `walk_in` `phone` `online` `appointment` |
| `documents_required[]` | text[] — **highest-value field on the record** |
| `application_window` | text — "opens the 1st, funds usually gone by the 5th" |
| `hours` | jsonb |
| `languages[]` | text[] |
| `typical_wait` | text |

## 5. Tags — three layers

### 5a. `need_tags[]` — what the program provides
Drives matching. Flat, closed vocabulary.

```
rent_assistance  eviction_prevention  deposit_assistance  mortgage_assistance
electric_bill  gas_bill  water_bill  reconnect_fee  utility_deposit
food_pantry  hot_meals  groceries  formula_diapers
medical_bills  prescriptions  free_clinic  dental  vision
transportation  gas_vouchers  bus_passes  car_repair
childcare  school_supplies  holiday_assistance
internet_device  phone_service
home_repair  weatherization  hvac_repair  disaster_relief
legal_aid  id_documents  burial_assistance
```

### 5b. `trigger_tags[]` — the life event behind the search
**This is the layer that connects to intake.** Captured from the user at ZIP entry (Concept B) or inferred from which categories they open. It is the single most commercially valuable field on the site and it is honest, because the user volunteered it and it genuinely improves matching.

| Trigger | Resource match | What it opens on the call |
|---|---|---|
| `utility_shutoff_notice` | crisis utility funds, CEAP | Retail electric rate — they're on a month-to-month holdover rate |
| `eviction_notice` | emergency rent, legal aid | Nothing directly. Serve it straight. |
| `job_loss` / `hours_cut` | rent, food, utility | Tax (prior-year returns, unclaimed refund), debt |
| `income_drop` | all | Tax, debt |
| `medical_event` | medical bills, prescriptions | Medical debt → debt vertical |
| `new_lease` / `relocation` | deposit assistance | **Best energy moment** — new service address, clean enrollment |
| `new_baby` | formula, diapers, WIC referral | Internet (household need change) |
| `disaster_displacement` | disaster relief, home repair | Property restoration vertical |
| `aging_into_65` | senior programs, AAA | Medicare — **separate property, separate consent.** Flag only. |
| `death_in_family` | burial assistance | Debt, tax |
| `disability_onset` | medical, transportation | Internet (low-cost tiers), debt |
| `veteran` | VSO referral | Energy, internet |

Two hard rules on this table:
- `aging_into_65` never produces a Medicare call from this property. A phone number left on a rent-help page is not valid TPMO consent. It flags a record for the separately-consented Medicare door.
- No trigger produces an ACA path from this property, for the same reason plus the strict-responsibility rule.

### 5c. `eligibility_tags[]` — the filter
```
income_130fpl  income_150fpl  income_185fpl  income_200fpl  no_income_test
has_children  has_senior_65  has_disability  veteran
renter  homeowner  citizenship_required
county_residency  needs_disconnect_notice  needs_eviction_filing  needs_photo_id
```

## 6. VA priority score

Single integer, recomputed nightly, drives the work queue.

```
priority =  0.30 * population_reach
          + 0.25 * volatility
          + 0.25 * staleness
          + 0.15 * demand_signal
          + 0.05 * contactability
```

| Component | 0–100 scale | Why |
|---|---|---|
| `population_reach` | ZIP-population covered by `service_zips`, log-normalized | Harris County CEAP subrecipient ≫ rural church pantry |
| `volatility` | by tier: A=100, B=65, C=35, D=15 | Funds-cycling programs go stale fastest |
| `staleness` | `days_since_verified / tier_interval * 100`, capped | Makes the queue self-feeding |
| `demand_signal` | searches hitting this ZIP+need_tag in last 30d, normalized | **The queue learns from your traffic.** Real demand pulls verification forward. |
| `contactability` | `100 - (failed_attempts * 20)`, floored at 0 | Stops VAs burning hours on orgs that never answer |

**Cold start:** before any record is verified, `staleness` and `demand_signal` are null, so the score reduces to reach + volatility. That correctly puts the 35 CEAP subrecipients covering all 254 counties at the top of the queue on day one — which is where you'd want to start anyway.

**Queue mechanics:** VAs pull from the top, never browse. Every pull writes to `status_log` even when contact fails (`method: phone, status: unknown, note: no answer 3rd attempt`), which feeds `contactability` and keeps dead records from recirculating.
