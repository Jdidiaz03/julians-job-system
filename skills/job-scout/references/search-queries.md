# Search query matrix (template — fill in your own)

You don't need to run every cell each time. Rotate between runs: cover each family at least once per run, always cover your top-priority location, and spread the rest across the rest. If `job-search-profile.md` adds or removes a family, follow the profile.

This file is the EU/general version. If you're also running `job-scout-us`, its own matrix lives at `~/.claude/skills/job-scout-us/references/search-queries.md` — don't duplicate US searches here.

## Indeed connector (`search_jobs`)

Build a table like this for your own role families. Example shape (replace with your own families, terms and locations):

| Family | `search` terms (one call each) | Countries (`country_code` + `location`) | `job_type` |
|---|---|---|---|
| 1 <your family name> | "<term 1>", "<term 2>", "<term 3>" | <country> <city>, <country> <city> | internship for intern terms, otherwise none |
| 2 <your family name> | … | … | … |

## Target-firm sweep (every run, if you have target employers who don't use ATS APIs)

List the specific firms you want covered every run (e.g. large consultancies, specific target companies). These firms often don't use Greenhouse/Lever/Ashby, so `scout.py --describe` won't work on them — search them directly instead.

- Indeed, one call per term, in your target locations:
  - "<role term 1>", "<role term 2>" …
  - Firm-named searches: "<firm> graduate", "<firm> intern"
- Web:
  - `"<firm>" graduate programme <year> (<keyword>) <city>`
  - `site:linkedin.com/jobs "<firm>" (intern OR graduate OR analyst) <city>`
  - The firm's own early-careers page via WebFetch.
- Graduate programmes often have one yearly intake and a fixed deadline. Put the deadline in `deadline` and the intake date in `start_date`.

## Web search

- `site:linkedin.com/jobs ("<keyword>") (intern OR junior OR graduate) <city>`
- `site:startup.jobs <keyword> <region>` · `site:welcometothejungle.com <keyword> <city>`
- `site:wellfound.com <keyword> <region>`
- `"graduate programme" <year> ("<keyword>") <city1> OR <city2>`

## "We're hiring" posts (last ~14 days)

- `site:linkedin.com/posts ("we're hiring" OR "we are hiring") (intern OR internship) <keyword> <city>`
- `site:linkedin.com/posts "hiring" "<role>" <region>`
- `site:x.com "we're hiring" <keyword> <region>`

Keep only posts that name a concrete role and company. Record the poster in `contact`.
