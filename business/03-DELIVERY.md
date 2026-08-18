# Delivering It

Target: full backlog cleared in under 3 hours. After the first client it's under 2.

## Step 1 — Pull the reviews (15 min)

Copy the review text from their Google Business Profile into a text file.
One review per block: reviewer name, star rating, date, text.

## Step 2 — Establish the voice (10 min, once per client)

```
Here is a business: {name}, a {niche} in {city}.
Here is their website About page: {paste}
Here are 3 reviews the owner DID reply to: {paste, if any exist}

Describe their voice in 5 bullets — formality, warmth, length,
whether they use the patient's name, whether they sign off with a
person's name. If they have never replied, infer the voice from
the website copy instead.
```

Save the answer. It goes at the top of every batch prompt below.

## Step 3 — Draft the replies (60–90 min for a full backlog)

Work in batches of 15. Never do all 40 in one prompt — quality collapses.

```
VOICE: {paste the 5 bullets from step 2}

Write owner replies to these {niche} reviews. Rules:
- 2–3 sentences maximum. Nobody reads long replies.
- Use the reviewer's first name.
- Name the specific thing they mentioned. Never generic thanks.
- Never repeat an opening phrase across replies — vary every one.
- Never use: "we appreciate your feedback", "we strive to", "thank you
  for taking the time", "we're thrilled", "valued patient".
- For anything under 4 stars: acknowledge without admitting fault, do
  not discuss any medical or personal detail publicly, move it offline
  with a name and a phone number.
- No emoji unless their existing replies use them.

REVIEWS:
{paste 15}
```

## Step 4 — Read every single one before it ships

**This is the step that decides whether you have a business.** You are personally
liable for what gets published under a client's name.

Check every reply for:
- [ ] Any clinical, medical, or personal detail about the reviewer → **delete it**, this is a privacy breach
- [ ] Any promise you cannot keep ("we'll refund you", "that won't happen again")
- [ ] Any admission of fault on a negative review
- [ ] Wrong name, wrong service, hallucinated detail that isn't in the review
- [ ] Repeated phrasing across the batch

Rewrite by hand anything that fails. Budget 30 minutes for this. Do not skip it.

## Step 5 — Profile rewrite (30 min)

```
Rewrite this Google Business Profile description for {business}, a {niche} in {city}.
750 characters max. Lead with what they actually do and where. Work in the
services they list on their website. No marketing adjectives — no "premier",
"state-of-the-art", "passionate". Plain and specific.

Current: {paste}
Website services: {paste}
```

Also fix, and list as findings: categories, hours, missing photos, missing services,
no posts. Every one of those is a visible win you can point at.

## Step 6 — Four Google Posts (20 min)

```
Write 4 Google Posts for {business} — one per week for a month.
Each: 100 words max, one clear call to action, no hashtags.
Topics from their actual services: {list}. Seasonal where it fits ({month}).
```

## Step 7 — Deliver

A single Google Doc, share link, three sections: **Replies** (ready to paste),
**Profile rewrite**, **Posts (scheduled dates)**. Plus a 4-line email listing what
changed. No PDF report. No dashboard. They want the work, not a document about the work.

## Monthly, after that (~40 min)

Check for new reviews weekly. Draft, check, send. Post the four posts. Send a
one-paragraph monthly note: reviews answered, current rating, anything worth flagging.
That note is what stops churn — it is the only proof they have that you exist.
