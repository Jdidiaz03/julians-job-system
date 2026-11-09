# CLAUDE.md — Job Search Vault Operating Manual (template)

## Context

This is your personal job-search vault. You curate sources and ask questions; Claude writes and maintains the application tracker and the career-related wiki pages. This file is a genericized copy of a working system (Julian's) — edit the `<Your Name>` / `<Vault Name>` placeholders and anything else specific to you.

**This template covers only the career/job-search slice of a second brain.** If you want the fuller "personal wiki" features (entities, concepts, projects, a general INGEST/QUERY/LINT workflow for non-career notes), they're straightforward to add later — this file only defines what the job-search skills need.

---

## Architecture

| Layer | Location | Purpose | Who writes |
|-------|----------|---------|------------|
| Raw sources | `<Vault Name>/raw/`, `01 Career/` | Immutable source documents | You only |
| Wiki | `<Vault Name>/wiki/` | Synthesized, interlinked knowledge (the tracker notes live here) | LLM only |
| Schema | `CLAUDE.md` (this file) | Operating rules | Both, by agreement |

**Golden rule:** Never modify files outside `<Vault Name>/wiki/` unless you explicitly ask. The raw layers (`raw/`, `01 Career/`) are read-only to the agent.

**One exception:** you may edit the properties of notes in `wiki/applications/` directly, usually by clicking a cell in the `applications.base` table. That table file lives in `01 Career/Job Applications/` at your request (Obsidian's Bases plugin needs a `.base` file; keeping it in your career folder rather than `wiki/` is just a filing preference — this is the only file the agent may edit in that folder, and only to change the table's views or columns). Always read a note's current properties before changing it, and never overwrite your edits.

---

## Wiki Structure

```
<Vault Name>/wiki/
├── log.md                # Append-only activity log
├── applications/         # One note per job application — properties are the tracker columns
│   ├── *.md
│   └── us-remote/         # only if you're using the optional job-scout-us skill
└── synthesis/
    ├── job-search-profile.md     # the scout's criteria — role families, locations, filters
    ├── application-pipeline.md  # the living tracker page (embeds applications.base views)
    └── outreach-voice.md is NOT here — it lives in 01 Career/CV & Positioning/ (see below)
```

## Raw / Career Folder Structure

```
<Vault Name>/01 Career/
├── CV & Positioning/
│   ├── application-profile.md     # standard form answers for job-apply
│   ├── outreach-voice.md          # your LinkedIn-note voice bank for job-network
│   ├── CV Versions/               # your base CV(s), markdown + docx
│   └── Tailored/                  # per-role tailored CVs (agent-writable)
└── Job Applications/
    └── applications.base          # the Obsidian Bases table (views: Inbox, Pipeline, All, Outcomes, Cards)
```

Treat `01 Career/` as a raw source — readable but never modified by the agent, except the two exceptions above (`applications.base` views/columns, and `Tailored/`).

---

## File Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Application | `company-role.md` | `acme-sdr-madrid.md` |
| Synthesis | `kebab-case-topic.md` | `job-search-profile.md` |

---

## Frontmatter Standard

Application notes use the schema in JOB INGEST below. Synthesis pages (like `job-search-profile.md`) use:

```yaml
---
type: synthesis
tags: [career]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

---

## Operations

### JOB INGEST

Triggered when you say "ingest the clippings", "ingest jobs", or clip a posting and ask to add it.

**Step-by-step:**

1. **List** `raw/jobs/` (if you use the Obsidian Web Clipper for this — optional). A clip is already processed if some note in `wiki/applications/` has it in its `clipping` property. Skip those. Also skip duplicates that have the same `link` or the same company and role, and say which ones were skipped.
2. **Read** each new clip in full.
3. **Assess** the fit against your CV and `job-search-profile.md`. Set `tier` and write the biggest `gap` in one line. **Flag traps:** years of experience required, a required language you don't speak, internships that are really senior roles.
4. **Apply your own drop rules** (e.g. a sponsorship/work-authorization filter, if that applies to you — see the Sponsorship filter section in `job-search-profile.md`, and remove it if it doesn't apply).
5. **Create** `wiki/applications/<company>-<role>.md` using the schema below, with `stage: found`.
6. **Append** one line to the `## Log` of `application-pipeline.md` and one entry to `wiki/log.md`.
7. **Report:** a short table in chat (company, role, tier, biggest gap, visa note), plus anything that was skipped.

**Application note schema:**

```yaml
---
type: application
tags: [career, application]
created: YYYY-MM-DD
updated: YYYY-MM-DD
company:
role:
stage: found         # found | applied | ongoing | accepted | rejected | skipped  (the Stage dropdown in the Base). Not `status`.
tier: 1              # 1 = apply now, 2 = clear gap, 3 = parked / too senior for now
job_type:            # internship | graduate | full-time | contract
location:
work_mode:           # onsite | hybrid | remote
salary:              # as posted, or "not listed"
source:              # linkedin | indeed | careers-page | startup-board | referral | scout-indeed | scout-web | scout-linkedin-post | scout-watchlist
link:                # posting URL
posted:              # YYYY-MM-DD if known
start_date:          # "YYYY-MM" (or "YYYY-MM-DD") if the posting states it, "ASAP" if it says so, else "not stated". Never guess.
deadline:
applied:
next_action:
next_date:
contact:
gap:                 # one line: the biggest risk to this application
visa_note:           # whatever this means for YOUR work-authorization situation
clipping: "[[raw/jobs/<clip file name>]]"   # empty for JOB SCOUT finds (no clip)
cv_version:          # whichever CV version fits the role
cv_used:             # set by TAILOR CV: "[[<tailored CV note>]]"
---
```

**Body:** a 3–5 line summary of the role, `## Why it fits`, `## Gaps / traps`, `## Visa (info only)`, `## Notes` (for interview notes later). Link to `[[application-pipeline]]`.

### STATUS UPDATE

Triggered when you say "applied to X", "rejected by X", "interview with X on…" and similar.

1. Find the note in `wiki/applications/`. If there is none, ask whether to create one.
2. Update `stage`, `updated`, and the matching date (`applied` = today on an application). "applied to X" = `applied`; an interview, screening call or case study = `ongoing`; "got the offer / accepted" = `accepted`; "rejected by X" = `rejected`.
3. Set a sensible `next_action` and `next_date`: after applying, "follow up" 7 days out. After an interview, "send thank-you / chase" 3–5 days out. After ~21 days of silence, suggest `rejected`.
4. Append one line to the `application-pipeline` log.

Also covers triage of JOB SCOUT finds: "skip X" sets `stage: skipped` (the scout will never suggest it again). "Keep X" leaves it at `found`.

### TAILOR CV

Triggered when you say "tailor my CV for X", "/job-scout tailor X", or paste a job description and ask to tailor your CV. Runs **only on request, never during a scout run** — each pass costs real tokens and needs your review.

The full method lives in the `job-scout` skill at `~/.claude/skills/job-scout/references/tailor-cv.md`. In short:

1. Take the job description from the role's note in `wiki/applications/`. A pasted job description first goes through JOB INGEST, so every tailored role is also on the board.
2. Start from the matching CV version in `01 Career/CV & Positioning/CV Versions/` (`cv_version`).
3. Never invent experience, inflate seniority or claim ownership you didn't have. Every line must be defensible in an interview.
4. Save the text to `01 Career/CV & Positioning/Tailored/<company>-<role>.md`. Set `cv_used` and `next_action: "apply"` on the note. A file (DOCX/PDF) goes to `~/Desktop/Resume/Tailored/` only after you approve the text.

### JOB SCOUT

Triggered when you say "find jobs", "run the job scout", "look for internships" and similar, or by a scheduled run if you set one up.

**The procedure lives in the Claude Code skill `job-scout`** (`~/.claude/skills/job-scout/SKILL.md`), so it works from any folder. The search criteria live in the vault at `job-search-profile.md`. Change the criteria there, not in the skill.

In short: it reads `job-search-profile.md` and the pending watchlist candidates from `~/Desktop/Claude Projects/job-scout/out/`. It searches Indeed (connector, if you've set one up) and the web, including LinkedIn "we're hiring" posts. It checks fit against the CV and adds up to ~15 notes per run to `wiki/applications/` with `stage: found`. They show up in the **Inbox** view of `applications.base`. Nothing you've already skipped is ever re-added.

**US / worldwide-remote roles** have their own optional skill, `job-scout-us` ("find US jobs"), same workflow and note schema. Criteria: the "US-remote scout" section of `job-search-profile.md`. Notes go in `wiki/applications/us-remote/`. Only set this up if you want it.

---

## Log Format

```
## [YYYY-MM-DD] operation | Title or description
- Action taken
- Pages created: X | Pages updated: Y
- Notes: ...
```

Parse last 10 entries: `grep "^## \[" "<Vault Name>/wiki/log.md" | tail -10`

---

## Principles

1. **Read before writing** — always read current page state before any update.
2. **Never delete** — deprecate stale pages with `status: deprecated` in frontmatter instead.
3. **Log everything** — every scout run, ingest and status update gets a log entry.
4. **Ask before filing a new kind of synthesis page** — you decide what gets saved beyond the application tracker.

---

## Starting State

Bootstrap this vault with:
- `wiki/log.md`, `wiki/synthesis/job-search-profile.md`, `wiki/synthesis/application-pipeline.md`
- `wiki/applications/` (empty folder)
- `01 Career/CV & Positioning/application-profile.md`, `outreach-voice.md`, your CV file(s)
- `01 Career/Job Applications/applications.base`

Templates for all of these are in this project's `vault-template/` folder — see `SETUP.md`.
