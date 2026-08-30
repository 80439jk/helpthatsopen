# Site architecture, content depth, and machine trust

## 1. Why deep content here, when AI Overviews killed it elsewhere

You set 65simple.com aside partly because AI Overviews eat informational healthcare traffic. That logic does not transfer to this property, and the reason matters.

AI answer engines are structurally starved for **current, local, verified status**. No model knows whether Salvation Army Harris County has funds left this week. It can't be trained in — it changes monthly. It can't be inferred. It can only be *retrieved from a source that maintains it*.

That's an unmatchable freshness moat, and it inverts the usual problem: you don't lose to the AI answer, you *become* the AI answer. The strategic job is making the citation carry your county page and your phone number with it.

Which means every architectural decision below optimizes for one thing: **being the most machine-legible, provably-fresh answer to "what assistance is open in [county] right now."**

## 2. URL architecture

```
/                                          ZIP entry + statewide status
/texas/                                    state hub
/texas/harris-county/                      county hub  ← the money page
/texas/harris-county/rent/                 county × need
/texas/harris-county/electric-bill/
/texas/harris-county/food/
/texas/77021/                              ZIP page (canonical → county for thin ZIPs)
/programs/bakerripley-ceap/                program page ← the citable atom
/how-we-verify/                            methodology ← the trust page
/corrections/                              public correction log
/for-agencies/                             supply side
/guides/what-to-bring-rent-help-texas/     evergreen depth
/data/texas.json                           machine-readable feed
/llms.txt
```

254 counties × ~8 need categories = ~2,000 county×need pages. That only survives if each carries real verified local programs with live statuses. Thin templated county pages get flattened; a page with eleven real programs and a timestamp from this morning does not.

**The program page is the unit that gets cited.** Give every program a stable URL so an AI can cite the specific program rather than the county page. That's what turns a citation into a landing.

## 3. Homepage section order

| # | Section | Job |
|---|---|---|
| 1 | ZIP entry + one-line promise | Convert the 70% who came to search |
| 2 | Live status band | "1,204 of 11,840 programs accepting today" — proof of freshness, above the fold |
| 3 | The three statuses explained | Teaches the vocabulary that makes the rest legible |
| 4 | How verification works | The differentiator, stated plainly with the phone-call detail |
| 5 | Browse by county | Internal link equity to 254 hubs |
| 6 | What to bring guides | Depth + the field nobody else publishes |
| 7 | For agencies | Supply side + trust signal (we take corrections) |
| 8 | Who runs this | Named humans. Required for E-E-A-T. |
| 9 | Non-affiliation footer | Compliance + trust, same statement |

Section 8 is not optional. A directory with anonymous data is a low-trust document to both Google and an LLM. Name the verification team.

## 4. Schema.org

### Type choices — one decision to get right

**Do not use `GovernmentService` or `GovernmentOrganization`,** even for CEAP subrecipients or PHAs. Structured data is a machine-readable *claim*. Marking these up as government services directly contradicts your non-affiliation positioning and would be the first thing a reviewer points at. Use `Service` with an `NGO` or `Organization` provider.

### Organization (site-wide)

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "@id": "https://helpthatsopen.com/#org",
  "name": "Help That's Open",
  "url": "https://helpthatsopen.com",
  "disambiguatingDescription": "An independent private company. Not a government agency, not affiliated with any government program, and not a provider of assistance.",
  "foundingDate": "2026",
  "areaServed": { "@type": "State", "name": "Texas" },
  "publishingPrinciples": "https://helpthatsopen.com/how-we-verify/",
  "correctionsPolicy": "https://helpthatsopen.com/corrections/"
}
```

`publishingPrinciples` and `correctionsPolicy` are underused and are exactly the properties that signal a maintained editorial operation rather than a scraped list.

### County page — Dataset + ItemList

Declaring the county directory as a `Dataset` is the single strongest AI-trust move available. It says: this is maintained, timestamped, geographically scoped data.

```json
{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "@id": "https://helpthatsopen.com/texas/harris-county/#dataset",
  "name": "Harris County, Texas assistance program status",
  "description": "Current application status, eligibility requirements, and required documents for rent, utility, water, and food assistance programs serving Harris County.",
  "creator": { "@id": "https://helpthatsopen.com/#org" },
  "dateModified": "2026-08-30T08:14:00-05:00",
  "temporalCoverage": "2026-08-30/..",
  "spatialCoverage": {
    "@type": "AdministrativeArea",
    "name": "Harris County, Texas"
  },
  "measurementTechnique": "Direct telephone verification with each provider",
  "isAccessibleForFree": true,
  "distribution": {
    "@type": "DataDownload",
    "encodingFormat": "application/json",
    "contentUrl": "https://helpthatsopen.com/data/texas/harris-county.json"
  }
}
```

`measurementTechnique` doing the work there is not decoration — it's the claim that separates you from every scraper in the category.

### Program page — Service

```json
{
  "@context": "https://schema.org",
  "@type": "Service",
  "@id": "https://helpthatsopen.com/programs/bakerripley-ceap/#service",
  "name": "Comprehensive Energy Assistance Program (CEAP)",
  "serviceType": "Utility bill assistance",
  "provider": {
    "@type": "NGO",
    "name": "BakerRipley",
    "url": "https://www.bakerripley.org"
  },
  "areaServed": [
    { "@type": "AdministrativeArea", "name": "Harris County, Texas" }
  ],
  "audience": {
    "@type": "Audience",
    "audienceType": "Households at or below 150% of federal poverty guidelines"
  },
  "availableChannel": {
    "@type": "ServiceChannel",
    "servicePhone": { "@type": "ContactPoint", "telephone": "+1-000-000-0000" },
    "serviceLocation": { "@type": "Place", "address": { "@type": "PostalAddress", "addressLocality": "Houston", "addressRegion": "TX" } }
  },
  "termsOfService": "Photo ID, Social Security cards for all household members, current utility bill, 30 days income for all adults",
  "isRelatedTo": { "@id": "https://helpthatsopen.com/texas/harris-county/electric-bill/#dataset" }
}
```

### Status changes — SpecialAnnouncement

When a program reopens or exhausts funds, emit one. It's a type Google actively consumes and it timestamps the change.

```json
{
  "@context": "https://schema.org",
  "@type": "SpecialAnnouncement",
  "name": "Salvation Army Greater Houston utility assistance reopens September 1",
  "datePosted": "2026-08-30T02:40:00-05:00",
  "expires": "2026-09-30",
  "category": "https://helpthatsopen.com/status/funds-reopened",
  "spatialCoverage": { "@type": "AdministrativeArea", "name": "Harris County, Texas" },
  "announcementLocation": { "@type": "Place", "name": "The Salvation Army — Greater Houston" }
}
```

### Also emit
- `FAQPage` on county pages — real questions, not padding
- `BreadcrumbList` on every page
- `WebSite` + `SearchAction` on home

## 5. AI trust — the eight signals

1. **True `dateModified`.** Visible timestamp on the page must match the markup. If they diverge, you've taught the crawler to distrust you.
2. **Named verifiers.** A bylined methodology page with real people. Anonymous data is low-trust data.
3. **`/how-we-verify/`** — what each status means, how often each tier is re-checked, what happens when an agency won't confirm. Almost nobody in this category has this page. It's the highest-leverage trust asset on the site.
4. **`/corrections/`** — public, dated log of every correction. Doubles as the supply-side hook: agencies who see it will engage.
5. **`/llms.txt`** — plain-text site map and usage terms for AI crawlers. Cheap, emerging convention.
6. **Machine-readable feed** at `/data/`. Being consumable is being citable.
7. **Citable atoms.** Stable per-program URLs with anchors.
8. **Explicit non-affiliation** in `disambiguatingDescription` and in visible footer text, worded identically.

## 6. Deep content that actually earns links

Ranked by defensibility, not volume:

1. **"What to bring" per need type.** The field nobody publishes. Ten guides, each genuinely useful, each built from your own verification calls.
2. **Funding cycle explainers.** Why utility funds run out by the 5th, how to time an application, what "crisis component" means. Nobody writes this in plain language.
3. **County status roundups, monthly.** "Harris County rent assistance: what's accepting in September." Fresh by construction, and the exact query shape AI answers get built from.
4. **Glossary.** Arrears, ledger, crisis component, recertification. Short, linkable, cited constantly.
5. **"What happens after you apply."** Realistic timelines per program type.

Skip: generic "10 ways to save money" filler. It won't rank, won't get cited, and dilutes the topical signal that makes the directory credible.
