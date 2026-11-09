# US-remote / worldwide-remote search query matrix (template — fill in your own)

Rotate between runs: cover every family each run, weight toward $ARGUMENTS if a focus is given. Families and caps come from the "US-remote scout" section of `job-search-profile.md`; if it changes, follow it.

## Indeed connector (`search_jobs`, `country_code: "US"`, `location: "remote"`)

Build a table like this for your own families:

| Family | `search` terms (one call each) |
|---|---|
| A <your top family> | "<term 1>", "<term 2>", "<term 3>" |
| B <family> | … |
| C <family> | … |
| D <family, if capped> | … |
| E <family, if capped> | … |

## Web search: worldwide / your-region first

- `site:wellfound.com/jobs remote (worldwide OR "anywhere") ("<keyword>")`
- `site:weworkremotely.com ("anywhere in the world" OR worldwide) (<keyword>)`
- `site:remotive.com ("worldwide" OR "<your region>") (<keyword>)`
- `site:himalayas.app/companies jobs <your country> ("<keyword>")`
- `site:linkedin.com/jobs remote ("EMEA" OR "Europe" OR <your region>) ("<keyword>")`
- `"remote" "work from anywhere" ("<keyword>") <year>`

## "Hiring" posts (last ~14 days)

- `site:linkedin.com/posts "hiring" remote (worldwide OR "anywhere" OR <your region>) ("<keyword>")`
- `site:x.com "we're hiring" remote "anywhere" (<keyword>)`

## AI-training / gig platforms (careers pages via WebFetch) — only if this is one of your families

| Platform | Where to look | Notes |
|---|---|---|
| Mercor | mercor.com/careers | Rates vary widely; take only listings with a stated rate |
| Outlier (Scale AI) | outlier.ai | Lists country eligibility on signup |
| Alignerr (Labelbox) | alignerr.com | Lists pay per role |
| DataAnnotation | dataannotation.tech | Country list not published; check the posting |
| Invisible Technologies | invisibletech.ai/careers | Skip domain-expert projects outside your own skills |

Record each as `company: <platform>`, `job_type: contract`, with the hourly rate in `salary`.
