---
name: job-scout
description: Find new job and internship postings for the user and add them to their Obsidian job tracker (vault, applications.base Inbox view). Searches the Indeed connector, the web, LinkedIn "we're hiring" posts, and the free watchlist candidates from ~/Desktop/Claude Projects/job-scout, checks fit against the user's CV, and writes one note per role with stage "found". Use when the user says "find jobs", "run the job scout", "look for internships/jobs", "any new postings?", or when invoked as /job-scout (including the scheduled headless run every 3 days). Also tailors the CV to one posting on request: use when the user says "tailor my CV for X", "/job-scout tailor X", or pastes a job description and asks to tailor their CV / adapt their resume to it.
argument-hint: "[optional focus, e.g. \"AI internships Madrid\", \"scheduled run\", or \"tailor <company>\"]"
---

# Job Scout

> **Setup note:** this file is a genericized copy of a working system. Paths below assume the vault layout in `vault-template/` — if you put your vault somewhere else or rename it, edit every path in this file (and in job-apply, job-network, job-scout-us) to match. See the project's `SETUP.md`.

## Two modes

- **Find** (default, the rest of this file): find postings and add them to the tracker.
- **Tailor**: when $ARGUMENTS starts with `tailor`, or the user asks to tailor/adapt their CV to a named role or a pasted job description. Read [references/tailor-cv.md](references/tailor-cv.md) and follow it; skip the Find workflow below. **Never tailor in a scheduled run or as part of Find.** It costs real tokens per role and needs the user to review the result, so it only runs when they ask.

# Find mode

You find new postings for the user and put them in their tracker so all they have to do is triage. **Input:** $ARGUMENTS. This is empty, a focus such as "only tech sales in Dublin" that narrows this run, or "scheduled run" (headless: nobody is watching, so never ask questions, and finish with a written report).

## Paths

- Vault: `~/Desktop/Obsidian/<Vault Name>/`
- Vault rules: `~/Desktop/Obsidian/CLAUDE.md`. **Read the JOB SCOUT, JOB INGEST and STATUS UPDATE sections plus the Golden rule before writing anything.** They govern: log newest-first, never delete, raw layers are read-only.
- Criteria: `<Vault Name>/wiki/synthesis/job-search-profile.md`. This is the single source of truth for role families, seniority, locations and flags. Read it every run.
- CV(s) for fit: `<Vault Name>/01 Career/CV & Positioning/CV Versions/`. One version is fine to start; if you keep several (one per role family), reading one is enough for fit — the version only matters for `cv_version`.
- Tracker notes: `<Vault Name>/wiki/applications/`, one note per role. The table is `<Vault Name>/01 Career/Job Applications/applications.base`.
- Watchlist candidates: `~/Desktop/Claude Projects/job-scout/out/candidates-*.md` (only the ones with `status: pending` in the frontmatter)
- Query matrix: [references/search-queries.md](references/search-queries.md). Note template: [references/note-template.md](references/note-template.md).

## Workflow

### 1. Load state
1. Read the vault rules sections, the search profile and the CV.
2. Build a **known set** from every note in `wiki/applications/`: each `link`, and each normalised `company + role` pair. **Include every stage, skipped and rejected too.** A role the user skipped must never come back, even under a slightly different URL.
3. Read the pending candidates files.

### 2. Gather (aim for about 40–80 raw leads, then filter hard)
**Every run uses all five sources below, even when the watchlist alone could fill the cap.** The watchlist only covers the companies you seed in `watchlist.json`, and the point of the other sources is to catch everything outside it. Budget roughly 15 slots per run, with a hard cap of how many come from the watchlist alone — tune these numbers to taste in [references/search-queries.md](references/search-queries.md) and `job-search-profile.md`. Give the rest to Indeed, web and "hiring" posts, unless those genuinely turn up nothing on-target; say so in the report if that happens.

1. **Watchlist candidates**: take all pending rows. They are pre-filtered on title and location only.
2. **Indeed connector** (`mcp__claude_ai_Indeed__search_jobs`, then `get_job_details` for the promising ones). These tools are often deferred, so load them first with ToolSearch `select:mcp__claude_ai_Indeed__search_jobs,mcp__claude_ai_Indeed__get_job_details`. If this connector isn't set up, skip it and say so in the report — the rest of the system still works. Use [references/search-queries.md](references/search-queries.md): families × countries. **US-remote and worldwide-remote roles belong to the optional `job-scout-us` skill**, not this one, so skip US searches here if you're using that skill. Use `job_type: "internship"` for the intern queries. Spread the queries across all families. If $ARGUMENTS gives a focus, weight toward it. Indeed returns a lot of noise, so judge every hit.
3. **Web search**: LinkedIn Jobs, startup.jobs, Welcome to the Jungle, Wellfound and grad-programme pages, using the matrix queries.
4. **"We're hiring" posts** from founders and recruiters in the last ~14 days (queries are in the matrix). Record the poster as `contact`, and use the post URL as `link` if there's no posting. This is best effort, because LinkedIn blocks scraping. Never invent a person or a post.
5. **Target-firm sweep (every run, if you have one):** large firms from the profile that don't use the ATS APIs `scout.py` reads (big consultancies, large employers in your target market), searched directly by name. **Clean slate applies only to `watchlist.json`.** Never drop a search hit because its company already appears in the vault; only drop it if the role itself is already in `wiki/applications/`.
6. If the Indeed connector isn't available (it can be missing in headless runs), carry on with the other sources and say so in the report.

### 3. Filter and assess
For each lead that isn't in the known set:
- Check it against the profile's families, seniority and locations. Drop anything off-target without comment.
- **Read the full posting** before writing a note. Never write a note from a title or search snippet alone.
  - **Greenhouse, Lever and Ashby URLs** (including company pages with `gh_jid=`): run `python3 "~/Desktop/Claude Projects/job-scout/scout.py" --describe "<url>"`. It returns the full text from the ATS API. WebFetch only sees an empty JavaScript shell on these pages.
  - **Indeed:** `get_job_details`. **Anything else:** WebFetch.
  - If the posting is closed or gone (the helper says "not on the board any more"), drop it. Also drop **internal-only** postings ("internal job board", "current employees", "must have been in your current role").
  - Use the real requirements for `gap`, not guesses.
- Set `tier`:
  - **1** = apply now: real fit, no hard blocker.
  - **2** = worth it with a clear gap.
  - **3** = parked: the target role but too senior.
- Write `gap` as one line naming the biggest risk.
- Set `cv_version` to whichever CV version fits the role best (edit `job-search-profile.md` to define your own versions — e.g. one per role family, or just `Base` if you only keep one CV).
- **Flags** go in the note's "Gaps / traps" section. Edit `job-search-profile.md`'s language/location filter to your own constraints — e.g. "drop roles that require a language I don't speak at professional level" — rather than reusing someone else's. Common flag types to adapt: a required language you don't speak, an "internship" that asks for years of experience, a work-authorization filter if that applies to you (see the Sponsorship filter section in the template `job-search-profile.md` — **remove it entirely if visa/sponsorship isn't a constraint for you**).
- **Never flag or down-tier for:** low or unpaid pay, or anything you've explicitly decided isn't a filter (set that decision down in `job-search-profile.md`'s Log so you don't re-litigate it every run).
- **Rank** by tier, then your top-priority location first, then freshness. **Keep at most ~15 per run.** If more tier-1 roles remain, say how many in the report and offer to add them.

### 4. Write
- One note per kept role: `wiki/applications/<company>-<role>.md` (kebab-case, short). Follow [references/note-template.md](references/note-template.md) exactly, with `stage: found` and a `start_date` taken from the posting ("not stated" if it doesn't say).
- Snapshot the posting in the body (what the job does, what it requires, pay and the start date if stated), because postings disappear.
- Link to an existing entity page if the company has one. **Never create entity pages** from the scout.
- Update each processed candidates file's frontmatter to `status: processed` and add `processed: YYYY-MM-DD`. That file is the scout tool's output, not a vault raw layer, so editing it is fine.

### 5. Log and report
1. Prepend one line to the `## Log` of `wiki/synthesis/application-pipeline.md`, newest first: `- **YYYY-MM-DD**: job scout added N roles (tier 1: a, tier 2: b, tier 3: c). Sources: …`
2. Add an entry at the top of `wiki/log.md` in the vault's log format (`## [YYYY-MM-DD] scout | Job scout: N new roles`). Don't add individual roles to `index.md`.
3. Report in chat: a table of company, role, location, tier, gap and link. Then list which sources worked and which failed, how many leads were dropped and the main reasons.

### 6. Chain into job-apply and job-network (adapt to your own rule)
Decide for yourself whether every manual Find run should chain straight into the other two skills, or whether you'd rather review the Inbox first and say "apply to X, Y" yourself. Julian's own rule (optional to copy):
1. **job-apply** on this run's tier-1 roles, best-ranked first, at most 5 (job-apply's own cap). Invoke it with the Skill tool, passing the role note names. If there are no tier-1 roles, ask which tier-2 roles to apply to, if any.
2. **job-network** on the same companies once the forms are filled: **1–2 people per company at most**. Invoke it with the Skill tool, passing the same roles.
3. Tell the user the remaining roles are still in the Inbox (*set Stage to `applied` or `skipped`, or say "apply to X"*).

**Scheduled / headless runs stop after step 5.** Both skills need a visible browser and the user at the screen. End the written report with something like: *Say "apply to X, Y" (or just "go") and I'll fill the forms and line up the LinkedIn outreach.*

## Rules
- The scout itself never applies to anything or contacts anyone. It finds and records, then hands off to job-apply and job-network (step 6), which keep their own rules (the user clicks Submit and Send).
- Never fabricate postings, pay, contacts or dates. Leave a field empty if unknown.
- Don't touch notes that already exist. The user may have edited them by hand.
- Don't write anywhere in the vault except `wiki/applications/`, `wiki/synthesis/application-pipeline.md` (the Log section only) and `wiki/log.md`. Tailor mode may also write to `01 Career/CV & Positioning/Tailored/` and `~/Desktop/Resume/Tailored/` (see references/tailor-cv.md).
