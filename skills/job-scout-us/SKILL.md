---
name: job-scout-us
description: "OPTIONAL — only install this if you also want US-remote and worldwide-remote (online) jobs. Finds remote jobs the user can do from wherever they live that clear a pay floor, across whatever role families they define, and adds them to their Obsidian job tracker. Same workflow as job-scout (dedupe, note template, log, chain into job-apply + job-network), different criteria and sources. Use when the user says 'find US jobs', 'US remote jobs', 'online jobs', 'run the US scout', or /job-scout-us (including a scheduled headless run after the main scout)."
argument-hint: "[optional focus, e.g. \"customer success\", \"AI training\", or \"scheduled run\"]"
---

# Job Scout US

> **Optional module.** Only set this up if the user wants US-remote / worldwide-remote roles in addition to the local-market search `job-scout` already does. If not, delete this skill folder — nothing else depends on it.

You find **online jobs the user can do from wherever they live, for US or worldwide-remote employers**, and put them in their tracker. **Input:** $ARGUMENTS: empty, a focus that narrows the run, or "scheduled run" (headless: never ask questions, finish with a written report).

## The base procedure

**Follow `~/.claude/skills/job-scout/SKILL.md`, Find mode, steps 1–6, exactly** (vault rules, read before writing, read the full posting, never fabricate, never touch existing notes, tiering, `gap`, `cv_version`, note template, log, report, chain). Everything below **overrides** only the parts it names. Tailor mode stays in job-scout.

## Overrides

### Criteria
Read the **"US-remote scout"** section of `<Vault Name>/wiki/synthesis/job-search-profile.md` every run (write this section yourself — see the template file, which has a worked example to copy and adapt). It is the single source of truth for this skill's families, pay floor, location classes and slot caps. The main scout's local families and location sweep do **not** apply here. Any language filter or seniority rule you've set **do** apply.

### Known set (step 1)
Build it from **every note under `wiki/applications/`, recursively** (top level, any subfolders such as `us-remote/`). The main scout and this one must never re-add each other's roles or anything the user skipped.

### Sources (step 2), all every run
1. **Board candidates:** `~/Desktop/Claude Projects/job-scout/out/us-candidates-*.md` with `status: pending`. Produced by `remote_boards.py` (Himalayas with a residence filter, Jobicy, Remote OK, Remotive — free JSON feeds). If none is pending, run `python3 "~/Desktop/Claude Projects/job-scout/remote_boards.py"` first. Its `Class` column is a hint only; confirm residence from the posting.
2. **Indeed connector:** `country_code: "US"`, `location: "remote"`, terms from [references/search-queries.md](references/search-queries.md).
3. **Web search:** worldwide/remote-friendly queries (Wellfound, We Work Remotely, Remotive, Himalayas, LinkedIn Jobs).
4. **"Hiring" posts** for remote roles. Best effort, never invent.
5. **AI-training / gig platforms** (if that's one of your families): their own careers pages. Each platform counts as a company; take only roles that name a pay rate or range.

Budget about 15 slots per run, with most from Indeed/web/posts rather than the board file alone — tune to taste.

### Filter and assess (step 3)
- **Pay floor:** define your own (e.g. $3,000/month ≈ $36k/yr ≈ $18/hr at 40h/week — convert other currencies at today's rate). Below → drop. No pay stated → keep only if a credible public range shows it clears, else drop. Commission-only → drop.
- **Location class → tier:**
  - **Open to someone in your country** (worldwide, anywhere, EMEA/Europe/your-region, contractor-anywhere, EOR in your country): eligible for **tier 1**.
  - **US residence required or implied** (or whichever country's residence the posting requires, if that's not where you live): **tier 2 max**, and `gap` starts with `"<country> residence required; …"`.
  - **A specific timezone only**, no residence rule: eligible for tier 1; note the hours in `gap`.
- Read the full posting first (scout.py `--describe` for Greenhouse/Lever/Ashby, WebFetch otherwise; most remote-board pages work with WebFetch).
- **Slot caps:** rank your top-priority family first. Cap noisier families (e.g. sales/BD, gig/annotation work) at a handful per run so they don't crowd out better fits.
- `cv_version`: whichever CV version fits the role family best (see your own `job-search-profile.md`).
- Ranking: tier, then open-to-your-country first, then freshness.

### Write (step 4)
- Notes go in **`wiki/applications/us-remote/<company>-<role>.md`** (create the folder if missing, or rename it to match whichever remote market you're targeting). Same template; `source:` is `scout-us-board`, `scout-indeed`, `scout-web`, `scout-linkedin-post` or `scout-us-platform`. `visa_note:` state your own residence/citizenship fact plainly. `work_mode: remote`. `job_type: contract` for contractor/freelance roles.
- In "Why it fits", say which family it is. In "Gaps / traps", always state the residence class and how pay was verified.
- Mark processed `us-candidates-*.md` files `status: processed` + `processed: YYYY-MM-DD`.

### Log and report (step 5)
- Pipeline log line: `- **YYYY-MM-DD**: US job scout added N roles (tier 1: a, tier 2: b). Open to <your country>: x, US residence: y. Sources: …`
- Vault log: `## [YYYY-MM-DD] scout | US job scout: N new roles`.
- The chat/report table adds a **Residence** column.

### Chain (step 6)
Same as job-scout: manual runs chain into job-apply (tier-1 roles, max 5) and job-network (1–2 people per company). Scheduled runs stop after the report.

## Rules
Same as job-scout. Write only in `wiki/applications/` (incl. `us-remote/`), the `## Log` of `wiki/synthesis/application-pipeline.md`, and `wiki/log.md`. Never claim residence, location or experience the user doesn't have on any form or note.
