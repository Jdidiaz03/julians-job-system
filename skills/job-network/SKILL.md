---
name: job-network
description: Find people to contact on LinkedIn at companies the user is applying to (their own alumni networks, the recruiter for the role, the hiring manager or team lead), draft short connection notes in their own voice from their outreach voice bank, and open each profile in Safari so they can send them themselves. It never clicks Connect or Send and never scripts LinkedIn. Also drafts follow-ups, nudges and referral asks when someone accepts or replies. Use when the user says "network X", "find people at X", "who should I reach out to at X", "outreach for X", "/job-network X", or "X accepted / X replied". Never runs on a schedule.
argument-hint: "<company or role>[, <company or role> …] | \"<name> accepted/replied\""
---

# Job Network

A referral or a hiring manager who knows the user's name does more for an application than anything else they can add. This skill finds the best one or two people at a company, writes the user a note for each in their own words, and opens their profiles. They read, edit if they want, and send.

**Input:** $ARGUMENTS, the roles (company names or note names from the tracker), or a follow-up like "Ana from Acme accepted". If it's empty, ask which roles. Suggest the ones they applied to in the last 7 days.

> **Setup note:** paths below assume the vault layout in `vault-template/` and the scripts in `scripts/`. Edit them if yours differ. See the project's `SETUP.md`.

## Hard rules — do not weaken these
- **The user sends everything.** Never click Connect, Send, Message or Follow, and never run a script on a LinkedIn page, not even to read it. LinkedIn's User Agreement bans automated activity, and the user's account is the one at risk. `safari.py` is only used to `open` profile URLs.
- **Find people with Apify first** — it's much more accurate than WebSearch and never touches the user's own account. `apify_people.py` runs no-login LinkedIn search actors from Apify's servers. WebSearch, the posting itself and company team pages are the fallback, and the way to get the company fact. Never invent a person, a title or a shared school.
- **Every note goes through the voice bank and a humanizer pass.** Start from the templates in `outreach-voice.md`, then check the result against the rules there (no em dashes, no "excited to / leverage / delve / passionate about the intersection of", no puffed-up claims). If it no longer sounds like the user's original draft, rewrite it closer to their original. (If you have Claude's `humanizer` skill available, run the note through it as the check.)
- **Notes are 300 characters max.** Check each filled note with python `len()`. Over 300: drop the "I saw…" detail first, then shorten the question.
- **Authenticity rule.** The "I saw…" line is a real fact about the company that you checked, with a source. Never frame a CV credential as interest in the company. Never say the user applied if the note's `stage` isn't `applied` or later.
- **No credential name-dropping that isn't actually shared** — e.g. don't mention your own degree/programme to people from a different school than you. Only claim a shared school, employer or background that's actually true for both of you.
- **1–2 people per company, never more.** Pick the strongest one or two: an alumnus first (shared school gets the most replies), then the recruiter for the role, then the hiring manager if neither turns up. At most 15 invites per run across all companies (LinkedIn caps invites at roughly 100 a week).
- **Never runs on a schedule.** The user has to be at the screen to send.

## Paths
- Voice bank: `~/Desktop/Obsidian/<Vault Name>/01 Career/CV & Positioning/outreach-voice.md`. **Read it every run.** It has the user's original draft, their rules, the field table, templates A–E, the follow-ups and their approved notes. Approved notes beat the templates when they disagree.
- Tracker notes: `~/Desktop/Obsidian/<Vault Name>/wiki/applications/`
- Pipeline log: `<Vault Name>/wiki/synthesis/application-pipeline.md` (the `## Log` section only, newest first)
- Safari: `python3 "~/Desktop/Claude Projects/job-scout/safari.py" open <url>`
- People search: `python3 "~/Desktop/Claude Projects/job-scout/apify_people.py"` (token in the Keychain, service `apify-api`; never print it)
- Tailored CVs (for the referral kit): `<Vault Name>/01 Career/CV & Positioning/Tailored/` and `~/Desktop/Resume/Tailored/`

## Workflow (per role)

### 1. Load the role
Find the note in `wiki/applications/` by company or role. If more than one matches, ask. If none, ask the user to paste the posting and run JOB INGEST first. Read `company`, `role`, `stage`, `location`, `link`, `cv_version`, `contact`, the posting snapshot and any `## Outreach` section. Don't contact anyone already listed there.

Set `[field]` from the role, using the voice bank's table (adapt the table to your own target role families). When the role doesn't fit a row, use the plain words from the job title.

### 2. Get one real company fact
One WebSearch for something recent and specific: a product launch, a client, an office opening, or what the team for this role works on. One short clause, true, with the source URL. If nothing solid turns up, leave the "I saw…" line out rather than padding it.

### 3. Find people
Search with `python3 "~/Desktop/Claude Projects/job-scout/apify_people.py"`. Each search has a small cost (check current Apify pricing — the script's own docstring has ballpark figures), so run `apify_people.py credit` first and keep a run under a sensible budget (e.g. $1.50). Rows marked `*` have the company in a **current** job; keep only those, in or near the role's country or team.

| Type | Search |
|---|---|
| Your alumni network (school A) | `search "<Company>" --schools "<Your School>" --match "<Company>"` |
| Your alumni network (school B, if any) | `search "<Company>" --schools "<Other School>" --match "<Company>"` |
| Recruiter | First any name in the posting. Then `search "<Company>" --titles "Recruiter,Talent Acquisition" --locations <city or country> --match "<Company>"` |
| Hiring manager / team lead | First "reports to…" in the posting and the company's team page. Then `search "<Company> <team>" --locations <country> --match "<Company>"` |
| A named person (founder, someone in the posting) | `search "<Full Name> <Company>" --max 10` |

Searching by company name plus a filter works better than `currentCompanies`, which needs LinkedIn company URLs. If Apify finds nobody, try WebSearch (`site:linkedin.com/in "<Company>" …`) before saying a type found nobody.

Then run `apify_people.py profiles <id> …` on your picks (much cheaper per profile than a search — check the script's docstring). It gives the real profile URL (use that, not any obfuscated id URL), current jobs and schools. Check they still work there and in that team. For alumni, the education dates tell you whether they're still studying or have graduated — phrase the note accordingly (see the voice bank's B1/B2 split). If you can't tell, assume graduated.

For each person note the name, title, URL, the type, one line on why them, and whether they're based in your target location. If a type finds nobody, say so; don't stretch to a weak match.

### 4. Draft
Pick the template from the voice bank — the exact letters depend on how you set up your own `outreach-voice.md`, but the shape (from Julian's version, adapt freely) is:
- Your alumni, still studying → one template. Your alumni, graduated → another.
- Recruiter → one template. Hiring manager or team lead → another. Anyone else worth it → a general one.
- A language/location variant if you'd message some contacts in a different language.

Fill the brackets, run the voice/humanizer checks, check the length. Also draft the "after they accept" message for each person, so the user has it ready.

**Order:** send both now. Never add a third person later; if someone doesn't answer, they get the one nudge (see Follow-ups) and that's it.

### 5. Hand off
Show one table per role: Person · Type · Why them · Profile · Note (with its character count).

Then, one person at a time:
1. `printf '%s' "<note>" | pbcopy`
2. `safari.py open <profile URL>`
3. Tell the user: *Connect → Add a note → paste → Send.* Wait for them to say done (or "skip", or their edited version) before the next one.

If they edit a note before sending, add their version to the voice bank under `## Approved notes` (newest first, with the date and the template letter) and update its `updated:` date. Use their version as the base for that type from then on.

### 6. Track
On the role's note (read the current properties first; never overwrite their edits):
- `contact:` set it only if it's empty, as `"<Name> (<type>)"` for the first person they sent to.
- `next_action: "follow up on LinkedIn outreach"` and `next_date:` today + 7, unless there's already an earlier `next_date`.
- `updated:` today.
- Add or extend a `## Outreach` section above `## Notes`, one line per person they sent to: `- YYYY-MM-DD · <Name> · <type> · <profile URL> · sent (template <letter>)`

Prepend one line to the pipeline log: `- **YYYY-MM-DD**: job-network: LinkedIn notes sent for <Company> (<n>: <types>).`

### 7. Report
A summary table (Company · People found · Sent · Waiting a week), the types that found nobody, and the reminder: *When someone accepts or replies, tell me "<name> accepted" and I'll draft the next message.*

## Follow-ups ("<name> accepted / replied / no reply")
Find the person in an `## Outreach` section and add a line for each step.
- **Accepted:** draft the "after they accept" message from the voice bank (under ~100 words, one question, a 15-minute call offer). Same hand-off: `pbcopy` and open their profile. The user sends it.
- **Replied, and it went well:** draft the referral ask from the voice bank. If they say yes, build the **referral kit**: the posting link, two lines about the user taken from the tailored CV for that role (no new claims), and the CV PDF path. Run `safari.py reveal <pdf>` so they can drag it into the chat.
- **No reply after 7 days:** the one-line nudge, once. After that, move on.
- Recruiter or hiring manager offers an interview: run the vault's STATUS UPDATE (`stage: ongoing`).

## Writes allowed
- `wiki/applications/<note>.md`: the properties above and the `## Outreach` section
- `wiki/synthesis/application-pipeline.md`: the Log only
- `01 Career/CV & Positioning/outreach-voice.md`: only `## Approved notes` and `updated:`, or a change the user asks for
- Nothing else in the vault.
