# Verification operation — script and operating model

## Part 1 — The seven rules that make the script foolproof

These matter more than the wording. Wording changes by state; these don't.

**1. Assume and confirm. Never ask open questions about facts you already have.**
"What are your hours?" → you get sent to their website.
"I have you as walk-in, Monday to Thursday, doors at eight — still right?" → you get an instant correction or a yes.
Every field the VA already has is prefilled and read as a statement. This single rule is worth more than the rest combined.

**2. Never ask a yes/no question about status.**
"Are you still accepting applications?" gets a reflexive yes from someone who's busy. Ask instead:
> "How far into the month is the funding usually lasting right now?"
That gets the truth, and it gets the reopening date for free.

**3. Ask for the negative.**
People are far more accurate about what doesn't work than what does. The highest-value question in the entire script:
> "What's the most common reason somebody gets turned away here?"
Almost nobody asks it. The answer is the "what to bring" content and the "the catch" line — the two fields that make our listing worth reading and that no competitor can scrape.

**4. Numbers, not adjectives.**
"Is it busy?" → "Yeah, pretty busy."
"About how many people do you see on a walk-in day?" → "Forty, maybe forty-five before we cut it off."

**5. Blank beats guessed.**
If the answer wasn't given, the field stays null with a reason code (`refused`, `didn't_know`, `ran_out_of_time`). A guessed field poisons the whole freshness claim. VAs are measured on accuracy, never on field completion.

**6. Read it back, out loud, word for word.**
Catches errors, and it signals that we're going to publish this — which makes people correct themselves. Two sentences, at the end, always.

**7. Under three minutes, with the end stated at the start.**
"About two minutes of questions" is a promise. Hard stop at six minutes; if you're over, you've lost the relationship for the next call.

## Part 2 — Why they answer at all

The VA is interrupting an understaffed intake line. The pitch has to be about *their* problem in the first eight seconds.

**The real pitch:** an intake coordinator's worst day is a waiting room full of people she has to turn away. Every person who shows up after the money's gone costs her ten minutes and an unpleasant conversation. If our listing is right, that stops happening.

So the opening line is never "can we get your information." It's **"we send people to you, and I want to make sure we're sending the right ones."**

## Part 3 — The script

### Step 1 · Open (0:15)

> "Hi, this is [name] — I'm calling from <b><u style=CornerHelpcolor:#1B7A4BCornerHelp>CornerHelp</u></b>, we're the site that lists which programs are taking applications. **We send people to you.** I've got about two minutes of questions so we're not sending you folks you can't help. Is now alright, or should I call back?"

Offering the callback gets a yes more often than not offering it.

**Never say:** partner, work with, affiliated with, on behalf of, we're with the state, we're calling for a client.

### Step 2 · Status (0:40)

> "Last time we spoke someone told us you were taking walk-ins. **How far into the month is the funding usually lasting right now?**"

If they answer only "we're open," follow up once:
> "And is that likely to hold through next week?"

Capture: status, "funding lasts until," reopen date.
A status change from the last check **requires a note** before the record can commit.

### Step 3 · Confirm the practicals (0:40)

> "I have you as **[prefilled: walk-in, Mon–Thu, doors at eight]**, capping around **[40]** a day. Is that still right?"

Then, only if not already covered:
> "And what do people need to bring — is it still ID, the bill, and income for everyone in the house?"

### Step 4 · The money question (0:30)

> "Last one. **What's the most common reason somebody gets turned away here?**"

Record verbatim, in their words. "People come in without the income for everybody in the house" is worth ten paraphrased sentences.

Then:
> "Anything changing in the next month or so you'd want people to know?"

### Step 5 · Read back and close (0:25)

> "So I'll show you as **accepting, walk-in Monday to Thursday at eight**, funding usually through about the tenth, and that people need income for everyone in the household. That right?"

> "Thanks — I'll put today's date on it so people know it's current. If anything changes before we call back, there's a link on your listing to update it yourself."

That last sentence is the supply-side hook. Every call plants it.

## Part 4 — Objections, with actual answers

**"Who is this? / Are you selling something?"**
> "It's <b><u style="color:#1B7A4B">CornerHelp</u></b> — nothing to sell, we don't charge anybody and we don't do applications. We're a directory. People search for rent help, we tell them who's actually open so they don't drive to a closed door."

**"Just look at our website."**
> "I did — it says you're open, but it doesn't say whether the funding's still there this month, and that's the part people get burned on. That's really all I'm asking."

**"I'm not authorized to give out information."**
> "Totally fair. Is there someone who handles intake I could ask, or should I just confirm what we already have listed and leave it there?"
Then downgrade: confirm the public facts only, mark `verify_method: partial`.

**"Take us off your site."**
> "I can do that today if you want. One thing worth knowing first — people are going to find you through 211 and search either way, and if we drop the listing they'll show up without knowing your hours or what to bring. The alternative is we keep it accurate. Your call, and if you still want it down I'll take it down."
If they insist, **honor it same day, no second ask.** Log it. That's the reputation the whole operation runs on.

**"How did you get my number?"**
> "It's on your public program page. If there's a better line for this kind of thing I'll switch it."

## Part 5 — Hard stops

The VA must never:
- Imply government affiliation or say we're calling on behalf of anyone
- Claim a partnership, referral agreement, or relationship of any kind
- Ask for client names, case data, or anything about individuals
- Offer money, gift cards, or anything of value in exchange for information
- Promise traffic volume or leads
- Negotiate placement, ranking, or featured position
- Argue with a removal request

Any of these on a QA review is a same-day retrain, not a coaching note.

## Part 6 — Operating model

**Queue-driven, never browse.** VAs pull from the top of the priority queue. Browsing lets people cherry-pick easy calls and starves the high-reach records.

**Three-attempt rule.** Three attempts across different days and times, then the record drops to `unknown` with a public "we couldn't reach them" note, and `contactability` decays so it stops recirculating. Being honest that we couldn't confirm is better than showing a stale green.

**Every pull writes.** Success, voicemail, wrong number, refusal — all write an append-only `status_log` entry. Nothing overwrites. A record with no log entry means the VA didn't pull it.

**QA, automated first:**
- Calls under 60 seconds that produced a full record → flagged
- All fields identical to the previous check → flagged (suspicious, not wrong)
- Status downgrade (accepting → funds out) with no note → blocked from committing
- 5% random call review on top

**Throughput math, so you can staff it.**

At 12,000 records with the tier mix from the schema, that's roughly **92,000 successful contacts a year**. At a ~60% reach rate and ~4 minutes per dial including wrap, that's about **9,800 hours — call it 5 FTE** to hold the full state at full cadence.

You don't start there. **The ten-county launch is about 1,500 records, which is well under one FTE.** Prove the workflow and the QA gates at that scale, then hire against measured reach rates rather than estimated ones.

**First week of calls:** the cold-start scoring puts the 35 CEAP subrecipients covering all 254 Texas counties at the top of the queue. That's the right first week — highest population reach, highest volatility, and they're the records every county page depends on.
