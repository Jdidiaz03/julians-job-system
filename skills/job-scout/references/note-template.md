# Application note template (stage: found)

This is the same schema as JOB INGEST in the vault's CLAUDE.md. If CLAUDE.md changes, CLAUDE.md wins.

File name: `wiki/applications/<company>-<role>.md`, kebab-case and short. Example: `acme-sdr-madrid.md`.

**Put double quotes around free-text values** (`role`, `gap`, `visa_note`, `salary`, `next_action`, `start_date`, `cv_version`). A colon inside an unquoted value breaks the YAML, and the note then vanishes from the Base table.

```markdown
---
type: application
tags: [career, application]
created: YYYY-MM-DD
updated: YYYY-MM-DD
company: Acme
role: Sales Development Representative
stage: found               # found | applied | ongoing | accepted | rejected | skipped. Never `status`.
tier: 1
job_type: full-time        # internship | graduate | full-time | contract
location: Madrid, Spain
work_mode: remote          # onsite | hybrid | remote
salary: not listed
source: scout-watchlist    # scout-indeed | scout-web | scout-linkedin-post | scout-watchlist
link: https://...
posted: YYYY-MM-DD
start_date: "YYYY-MM"       # from the posting; "ASAP" if it says so; "not stated" otherwise. Never guess.
deadline:
applied:
next_action:
next_date:
contact:
gap: one line — the biggest risk to this application
visa_note: "info only (adjust this field's meaning to your own work-authorization situation)"
clipping:
cv_version: "Base"          # whatever CV versions you've defined — the CV that fits this role
cv_used:                   # set by Tailor mode: "[[<tailored CV note>]]"
---

# <Role> — <Company>

3–5 lines: what the company does, what this role does day to day, and why the scout surfaced it.

## Posting snapshot
- **Does:** …
- **Requires:** …
- **Pay / start:** … (as posted)

## Why it fits
- Tie it to specific CV evidence — name the concrete project, skill or experience that matches.

## Gaps / traps
- …

## Visa
- …

## Notes

---
Found by job scout on YYYY-MM-DD · [[application-pipeline]] · [[job-search-profile]]
```
