# Product brief

## What it is

A directory of local assistance programs — rent, utility, water, food, emergency,
school — that shows whether each one is **currently accepting applications**, what
documents it requires, and when we last confirmed it by phone.

## The gap it fills

Every existing directory (211, food bank locators, aggregator sites) gives you a name
and a phone number. None of them tell you whether the money is still there this month.
Crisis funds refill on the 1st and empty within days in big metros, so a listing that
says "open" is wrong most of the time.

That freshness is the entire moat. It cannot be scraped, cannot be inferred by a
language model, and only exists if someone picks up a phone.

## Value proposition

> **We don't take applications. We tell you who's open.**

No forms, no filing, no representing anyone to any agency. This is stated on the
landing page, restated at both CTAs, and repeated in the footer disclaimer.

It does three things at once: it's the cleanest available compliance position, it
differentiates from every "get your benefits" operation in the category, and it
removes the fear that stops people from calling an unfamiliar number.

## Business model

Inbound calls to a licensed call center. The directory is the acquisition asset; the
call is a **navigation** service — which programs fit, in what order, whether your
paperwork will hold up. Commercial products are discovered in the interview, never
pre-sold on the page.

**The QA gate this creates:** the promise is printed on the site, so the call has to
deliver navigation value before anything else opens. Measure time-to-first-commercial-
mention on recordings. An agent who pivots in 45 seconds makes the page copy false.

## Audience and entry

Someone with a disconnect notice or an eviction filing on the counter. Usually on a
phone, usually stressed, often has already called 211 and gotten a busy signal.

**Most traffic lands mid-site from search** — on a county or ZIP page, never seeing
the homepage. Every geo page is therefore a complete landing page.

## Why AI search helps rather than hurts

Answer engines are structurally starved for current local status. No model knows
whether a given program has funds this week. The strategy is to *become* the cited
answer, which is why program pages are stable citable URLs and county pages emit
`Dataset` markup with a real `dateModified`.

## First market

Texas, ten counties: Harris, Dallas, Tarrant, Bexar, Travis, Collin, Denton, Hidalgo,
El Paso, Fort Bend. ~60% of state population, ~1,500 records, under one FTE of
verification. Florida second.

Texas is the first market, not the model. Nothing in the codebase is Texas-specific.
