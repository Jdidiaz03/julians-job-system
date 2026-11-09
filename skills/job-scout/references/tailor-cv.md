# Mode B: Tailor a CV to one posting

Load this file only in Tailor mode. Find mode and scheduled runs never read it.

The core method below is a general-purpose CV-tailoring prompt (based on a career advisor's method Julian used — adapt the "Critical rules" to your own non-negotiables about what you will and won't claim). The vault wiring sits around it.

## Paths

- Base CV(s) (markdown, read these): `<Vault Name>/01 Career/CV & Positioning/CV Versions/CV — <Version>.md` (one file per version you keep; a single `CV — Base.md` is fine if you don't split by role family)
- Any standing feedback from an advisor or past review you want every tailoring pass to respect: keep it in a note here (e.g. `Advisor Feedback Applied.md`) and read it every time.
- Base DOCX files (used for layout when making a file): `~/Desktop/Resume/<Your Name> CV - <Version>.docx`
- Tailored output, text: `<Vault Name>/01 Career/CV & Positioning/Tailored/<company>-<role>.md`
- Tailored output, files: `~/Desktop/Resume/Tailored/<Your Name> CV - <Company>.docx` / `.pdf`

## 1. Get the job description

- **Named role** ("tailor my CV for X"): find the note in `wiki/applications/` by company/role. Use its `## Posting snapshot` and body. If the snapshot is thin, read the `clipping` file. If the clipping is thin too, fetch the `link`: `scout.py --describe "<url>"` for Greenhouse/Lever/Ashby, `get_job_details` for Indeed, WebFetch otherwise. If more than one note matches, ask which one.
- **Pasted job description** (a manual find): first run JOB INGEST on it, following the vault CLAUDE.md:
  - Dedupe against `wiki/applications/` by link or by company + role. If the role is already there, reuse that note.
  - Write the note with `stage: found`, `source: linkedin` (or whatever the user says), `clipping:` empty, and a posting snapshot of the pasted text.
  - Append the pipeline log line and a `wiki/log.md` entry.
  - Then tailor. One paste does both.
- **Nothing given:** ask the user to paste the job description or name the role.

## 2. Pick the base version

Use the note's `cv_version` if set. Otherwise choose one and write it into the note, based on whatever versions you've defined in `job-search-profile.md` (e.g. one per role family, or just `Base` if you keep a single CV).

## 3. Tailor

You are an experienced hiring assistant, recruiter, and ATS optimization expert. Optimize the resume so it is highly relevant to the job description while remaining completely truthful and interview-defensible.

**Step 1: Extract job requirements.**
- Job information: title, seniority, industry, company type.
- Technical and functional requirements: required skills, preferred skills, responsibilities, tools/technologies, industry terminology, domain keywords.
- Soft skills: communication, stakeholder management, leadership, collaboration, problem solving, analytical thinking, customer focus, strategic thinking.

**Step 2: Compare the resume against the job description.** For each relevant requirement or keyword:
- **Already in the resume:** make it stronger and more visible, use the posting's wording, and highlight impact.
- **There but weak:** strengthen it, move it higher, and tie it to a business result.
- **Not stated but clearly supported by the user's experience:** add a truthful statement that makes the connection explicit.
- **Not supportable:** do not add it. Do not invent experience, and do not assume knowledge, tools, certifications or responsibilities.

**Step 3: Tailor the structure.**
- Summary: reflect the target role, carry the top keywords, and stay realistic for the user's level.
- Experience: put the most relevant roles and bullets higher, use action + impact language, and emphasize transferable skills.
- Skills: surface supported skills in the posting's wording.

**Step 4: ATS.** Keyword-rich but easy to scan. No icons, tables, graphics or images. Use a standard structure with clean headings.

**Critical rules (non-negotiable — fill in your own specifics, but keep the shape):**
1. **Never invent experience:** no new jobs, projects, achievements, certifications, tools or responsibilities. Everything must trace back to the base CV or a confirmed vault fact.
2. **Don't inflate seniority:** be honest about the level you're actually at.
3. **No false claims about ownership or scope** you didn't have — e.g. if you supported a sales process but didn't own the pipeline, say "supported", not "owned" or "closed". List your own hard no's here, specific to your real experience.
4. **Credibility over keyword density.** Test every line: could you confidently explain and defend this in an interview? If not, rewrite it.

**Your own standing CV rules (fill in, e.g. from advisor feedback):**
- Pick one date format and stick to it everywhere.
- Metrics only if real — keep approximations honest ("~45 min saved", not "45 min saved" if it's an estimate).
- Say "production" only if the work is truly in production.
- Must fit on one page (or whatever length convention your target market expects).

Also follow the authenticity rule: never frame CV credentials as genuine interest in the company (see `job-apply`'s hard rules for what this means in practice).

## 4. Output in chat

1. **Key keywords**: the 10–15 that matter most.
2. **Match analysis**: strengths, gaps, transferable skills (short).
3. **Tailored CV**: the full text, ATS-clean.
4. **Changes vs base version**: a short list (moved, reworded, added from a supported fact, cut), so the user can review in a minute.

## 5. Save

- Write the tailored text to `01 Career/CV & Positioning/Tailored/<company>-<role>.md` with frontmatter `type: cv-tailored`, `base: <version>`, `application: "[[<note name>]]"`, `created:`. Writing to this folder is pre-authorized; it is the only place outside `wiki/` this mode writes.
- On the application note, set `cv_version`, `cv_used: "[[<tailored file name>]]"`, `next_action: "apply"` and `updated:`.
- **Only after the user approves the text:** build the DOCX from the matching base DOCX layout (docx skill / python-docx) into `~/Desktop/Resume/Tailored/`, convert it to PDF, and check it fits your target page length. If it's over, trim the lowest-relevance bullet and say which one.
- Don't touch `index.md`. Logging is the pipeline log line and the `wiki/log.md` entry from the paste path only; a plain tailoring needs no log entry.
