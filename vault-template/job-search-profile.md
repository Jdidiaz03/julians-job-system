---
type: synthesis
tags: [career, applications]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Job Search Profile — what the scout looks for (template)

*The criteria the `job-scout` skill uses to find postings for you. To change what it looks for, tell Claude and this page gets updated; the skill reads it on every run. Finds land in `application-pipeline` → `applications.base`, **Inbox** view.*

**Fill in every section below with your own facts.** The structure (and the worked example in brackets) is Julian's own profile, kept as a guide to the shape and level of detail that makes the scout actually useful — vague criteria produce noisy results.

## Role families

[Example from Julian's profile: 6 families — AI implementation/automation (core), Deployment/FDE (target, mostly senior), Digital transformation/tech consulting, Strategy consulting, Tech sales/GTM, Adjacent (founder's associate, ops). Each family has a list of English keywords and (if relevant) keywords in another language.]

| # | Family | Keywords |
|---|---|---|
| 1 | <your core family> | <keyword>, <keyword>, <keyword> |
| 2 | <family> | … |

### Target-firm sweep (if relevant)

List specific large employers you don't want the scout to miss — the ones that don't use the ATS APIs the scout script reads (`scout.py`), so they need a direct search every run instead. [Julian's example: a consulting sweep covering Accenture, Deloitte, EY, KPMG, PwC, Capgemini, McKinsey, BCG, Bain and similar.]

## Industries out

List anything you know you don't want, so the scout drops it without comment instead of surfacing it every run and wasting a slot.

## Priority

If some families matter more than others, say so explicitly and give any caps (e.g. "family X capped at 3 slots per run, only after family Y is filled"). This is what keeps the scout from drowning your top choice in noise from an easier-to-find but lower-priority family.

## Seniority

- **In:** [e.g. internships, graduate programmes, junior roles, anything asking ≤2 years]
- **Parked (tier 3):** [roles that are your target but ask for more experience than you have yet — kept as spec references]
- **Out:** [e.g. senior, lead, manager, quota-carrying roles]

## Locations

List in priority order. [Julian's example: his own city first (visa/citizenship-route reasons), then two or three other target cities, then "EU hubs and remote-EU" as a looser third tier, then "US: remote only" handled by the optional job-scout-us skill.]

## US-remote scout (only if you're using the optional `job-scout-us` skill)

Define:
- **Pay floor** (the one hard rule most people want): e.g. "$3,000/month, below that is dropped".
- **Families** (can differ from your main families — e.g. ops/analyst, customer success, sales/BD, AI training/evaluation are all common additions for a remote-work income track).
- **Residence → tier** rule: which residence requirements make a role tier-1 vs tier-2-max for you.

## Language filter

State plainly which languages you don't speak at a professional level, so the scout drops roles that require them. Note any exceptions (e.g. "German or French at professional level: keep as tier 2 with a flag, because French is a possible route for me").

## Flags (information only, never filters)

List anything that should be called out in the note but never used to drop a role (e.g. "an internship that actually asks for 4+ years").

**Not flags:** anything you've explicitly decided isn't worth tracking (e.g. "low or unpaid pay: any pay is fine", "a start date earlier than I'm free: I'll negotiate").

## Sponsorship / work-authorization filter

**Only include this section if visa/work-authorization is actually a constraint for you.** If you have unrestricted work rights everywhere you're applying, delete this whole section — don't keep a filter that doesn't apply.

If it does apply: state which roles get dropped outright (e.g. "a posting that explicitly says it won't sponsor, or requires existing right to work with none offered") versus which just get a `visa_note` with no effect on tier (e.g. silent postings, postings that do offer sponsorship, internships signed through a specific legal mechanism you have access to).

## Sources the scout uses

| Source | How | Notes |
|---|---|---|
| Company watchlist | `~/Desktop/Claude Projects/job-scout/watchlist.json` (companies on public job-board APIs, checked for free) | **Clean slate:** seed it with companies, it dedupes against itself, not against the vault |
| Indeed | Claude connector, per country — optional, only if you've connected it | Noisy, so every hit gets a fit check |
| Web | LinkedIn Jobs, startup.jobs, Welcome to the Jungle, Wellfound, grad-programme pages | — |
| "We're hiring" posts | LinkedIn/X posts from founders and recruiters, last 14 days | Best effort: LinkedIn blocks scraping, so coverage is patchy |

## Log

Keep a running log here of every change you make to this profile and why — future-you (and the scout) benefit from knowing *why* a rule exists, not just what it is. [Example entries from Julian's profile: "sponsorship filter added — roles whose company states it won't sponsor are dropped", "AI implementation prioritised over SDR/BDR", "German-required roles dropped, not flagged".]

- **YYYY-MM-DD**: created.
