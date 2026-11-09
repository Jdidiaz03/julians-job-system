---
name: job-apply
description: Prepare and fill job applications for the user, then leave them open for them to submit. For each role they name from the job tracker, it finds the posting on the company's own careers site, tailors their CV, builds the one-page PDF, fills the application form (text, dropdowns, Yes/No, uploads, account creation with a Keychain-stored strong password), and leaves each form in an open browser tab. It never clicks Submit. Use when the user says "apply to X", "apply to X, Y and Z", "fill the application for X", "/job-apply X", or picks roles from the Inbox to apply to. Never runs on a schedule.
argument-hint: "<company or role>[, <company or role> …]"
---

# Job Apply

You prepare the user's applications so that all they do is review each open tab and click Submit themselves. **Input:** $ARGUMENTS, the roles to apply to (company names or note names from the tracker). If it's empty, ask which roles; offer the tier-1 `stage: found` roles from the Inbox as suggestions.

> **Setup note:** paths below assume the vault layout in `vault-template/` and the scripts in `scripts/`. Edit them if yours differ. See the project's `SETUP.md`.

## Hard rules — do not weaken these
- **Never click Submit, Send, Finish or Confirm.** `apply.py click` / `safari.py click` refuses them; never work around it (no JS clicks, no Enter in the last field to submit).
- **Never invent an answer.** Every value comes from the application profile, the tailored CV, the role's note, or something the user said in this conversation. Leave anything else blank and list it for them.
- **Never automate Indeed Apply or LinkedIn Easy Apply.** If those are the only way in, mark the role `manual`.
- **Never handle passwords yourself.** Password fields only ever get `"__KEYCHAIN__"`. Never print, read back or log a password.
- **CAPTCHAs and email verification codes are the user's.** Leave the tab open and say so.
- **Never run in a scheduled or headless session.** This needs a visible browser and the user at the screen.
- **At most 5 roles per run.** If they name more, do the first 5 and offer to continue.
- **Authenticity rule:** never frame CV credentials as genuine interest in the company. Motivation questions ("Why do you want to work here?", "proudest achievement") use the profile's **Reusable answers** (adapt only the company name and one factual company detail from the posting), or one the user gave in this conversation; otherwise `[fill in: your reason]`. List every reused draft in the final report so they can paste changes. When they paste a new version, replace it in the profile and mark it approved.

## Paths
- Tracker notes: `~/Desktop/Obsidian/<Vault Name>/wiki/applications/`
- **Application profile** (all standard answers): `<Vault Name>/01 Career/CV & Positioning/application-profile.md`. Read it every run. Fields marked `[fill in: …]` are unknown: leave them blank and flag them.
- **Tailor method**: `~/.claude/skills/job-scout/references/tailor-cv.md` (the single copy, shared with job-scout).
- Base CVs: `<Vault Name>/01 Career/CV & Positioning/CV Versions/`; base DOCX: `~/Desktop/Resume/<Your Name> CV - <Version>.docx`
- Tailored output: text in `<Vault Name>/01 Career/CV & Positioning/Tailored/<company>-<role>.md`; files in `~/Desktop/Resume/Tailored/<Your Name> CV - <Company>.docx/.pdf` (the recruiter sees this file name, so keep it clean). If that file already exists for a **different** role at the same company, use `<Your Name> CV - <Company> <Short Role>.docx/.pdf` instead; never overwrite another role's CV.
- **Browser: Safari, recommended** (this is Mac-specific — it uses Safari's own saved passwords / AutoFill via AppleScript). Open, read and fill every application with `python3 "~/Desktop/Claude Projects/job-scout/safari.py"` (`open` / `goto` / `fields` / `fill` / `click` / `reveal`, same fill.json as below). The user logs in with Safari AutoFill; `safari.py` never touches passwords and can't attach files, so run `safari.py reveal <pdf>` and tell them to drag the CV in. If `safari.py fill` reports a combobox as "no matching option (0 shown)" (Greenhouse react-select dropdowns), set those with `python3 "~/Desktop/Claude Projects/job-scout/safari_select.py" <match> <spec.json>`. **If you're not on a Mac, or don't use Safari**, use the Chromium `apply.py` window instead — same commands, different plumbing (Playwright over CDP), and it handles its own password Keychain entries the same way.
- Chromium helper (fallback, or primary if not using Safari): `python3 "~/Desktop/Claude Projects/job-scout/apply.py"` (commands below)
- Working files (fields/fill JSON): your scratchpad directory, never the vault.
- Vault rules: `~/Desktop/Obsidian/CLAUDE.md` (STATUS UPDATE and TAILOR CV sections).

## apply.py / safari.py
| Command | Does |
|---|---|
| `browser` (apply.py only) | Starts the visible Chromium window (own profile, logins persist). Others start it if needed. |
| `fields <tab> [<url>]` | Opens `<url>` in a tab named `<tab>` (or rereads that tab) and prints JSON: `url`, `title`, `buttons`, `captcha`, `fields[]` (type, label, selector, required, options, current value, `frame`). |
| `fill <tab> <fill.json>` | Fills the fields and prints a per-field report, `required_still_empty`, `captcha` and `buttons`. |
| `click <tab> "<text>"` | Clicks Apply / Next / Continue / Save and continue. Refuses submit-like buttons. |
| `tabs` | Lists open tabs by name. |
| `pdf <file.docx>` (apply.py only) | Converts with Microsoft Word and prints the page count. If Word isn't installed, use `pages_pdf.py` instead (Pages + the Carlito font substitute). |

`fill.json` = `{"fields": [ <field object copied from the fields output, plus "value"> ]}`. Copy the whole field object (selector, type, options, frame) and add `value`:
- text / email / tel / textarea: the string
- select / combobox: the option text (fuzzy-matched; for country + phone code pickers use the country name, e.g. "Spain")
- radio / buttons (Yes/No): the option label
- checkbox: `true` / `false`
- file: an absolute path (`~` is fine)
- password: `"__KEYCHAIN__"` plus `"account": "<your email>"`

## Workflow (per role, one at a time)

### 1. Load the role
- Find the note in `wiki/applications/` by company/role. If more than one matches, ask. If none, ask the user to paste the job description and run JOB INGEST first (as in `tailor-cv.md` step 1).
- If `stage` is already `applied` or later, say so and skip unless they insist.
- Read the posting snapshot, `link`, `cv_version`, `location`, `source`.

### 2. Find the company's own application page
- If `link` is on Ashby / Greenhouse / Lever / Workable / Teamtailor / SmartRecruiters / Workday / SuccessFactors / iCIMS / a company careers site, use it. Ashby: append `/application` to the posting URL. Lever: append `/apply`. Greenhouse: the form is on the posting page.
- If `link` is Indeed / LinkedIn: search the company's careers site for the same role (WebSearch `"<role>" site:<company careers domain>` or the company's ATS board). Match on title + location. If it isn't there, mark `manual` (link the user to the Indeed/LinkedIn page) and go to the next role.
- Run `fields <slug> <url>`. If the URL lands on an error / listing page (e.g. `?error=true`, a jobs list, "no longer accepting"), the role is **closed**: set the note's `next_action: "posting closed (checked YYYY-MM-DD)"`, tell the user, move on.
- If there's an "Apply" button and no form fields yet, `click <slug> "Apply"` and read the fields again.

### 3. Tailor the CV
- Follow `tailor-cv.md` steps 2–3 exactly (base version, the tailoring method, critical rules, target length).
- **Difference from Tailor mode:** the user approves at the final review, not before the DOCX. So build the files straight away, and show them the change list (step 4 of `tailor-cv.md`) in the final report.
- Save the text (`tailor-cv.md` step 5). Build the DOCX by copying the matching base DOCX and editing it with python-docx: change paragraph text run by run so the fonts, sizes and bold/italic stay; delete paragraphs rather than reformatting; never add tables or images. Make the PDF with Word (`apply.py pdf`) if installed, otherwise `python3 "~/Desktop/Claude Projects/job-scout/pages_pdf.py" <docx> <pdf>` (uses Pages + the Carlito font; if it reports more pages than your target, retry with a tighter line spacing before trimming). If it's still over your target length, trim the lowest-relevance bullet, rebuild and say which one you cut.
- If `cv_used` is already set and the file exists, reuse it; don't re-tailor.

### 4. Map answers
Using the fields JSON, write `fill.json`:
- Identity, contact, education, links, availability, languages, EEO, and the Reusable answers section: from the profile.
- **Work authorization / sponsorship**: fill in your own rule here based on your actual citizenship/visa situation per target country. Free-text visa questions: one factual sentence about your real situation.
- **Salary expectation** — never leave it blank. Do quick market research for that role, seniority and city: use the posting's own range if there is one (aim for its middle), otherwise a WebSearch of salary sources (Glassdoor, Levels.fyi, Payscale, local graduate/intern salary surveys). Number-only field → one figure in local currency; free text → a short range. List the figure and its source in the final report.
- "How did you hear": from the note's `source` (scout-watchlist / careers-page → "Company website"; scout-indeed → "Indeed"; linkedin → "LinkedIn").
- Resume upload → the tailored PDF. Cover letter upload: only if required. If so, write a short, factual letter (role fit from the CV, no invented enthusiasm, motivation line left for the user), save it as DOCX → PDF in `~/Desktop/Resume/Tailored/`, and flag it for review.
- Screening questions: answer only from the CV/profile and keep it factual. Yes/No questions about experience must be literally true.
- **Fill every profile section, required or not** (empty optional sections can filter candidates out even when the CV has the info). That means work experience (every CV role with dates and bullets), education (exact dates), languages, skills, certificates, nationalities, LinkedIn, phone, city. Use repeatable "Add" rows (SuccessFactors, Workday, Oracle) for each item.
- Skip "Autofill from resume" upload boxes, optional marketing opt-ins and "talent community" boxes.
- **SuccessFactors (career5.successfactors.eu and similar) holds one company session at a time:** signing in to another company there logs the others out. Do SuccessFactors roles one by one: the user signs in, you fill, they submit, then the next.
- Anything you can't answer truthfully from those sources: leave it out of `fill.json` and add it to the flag list.

### 5. Fill
- `fill <slug> fill.json`. Read the report:
  - `error` / `no option matches` → retry once with a corrected value or selector, else flag it.
  - `required_still_empty` → these are flags for the user unless you have a truthful answer.
- **Multi-page forms (Workday etc.):** after each page is filled, `click <slug> "Next"` / "Continue" / "Save and Continue", run `fields` again and repeat. Stop at the review page; never press its submit button.
- **Existing account / sign-in page** ("already registered", or a company they applied to before): fill the email and the password with `__KEYCHAIN__` plus `"login": true`, so only a saved login-Keychain password is used and none is ever created. If the report says no saved password, stop and flag it: they log in themselves or save it with `security add-internet-password -U -s <domain> -a <email> -w` in Terminal. Never try to read the iCloud Passwords app or Chrome's password store.
- **Account required:** fill the email with the profile email and every password / confirm-password field with `__KEYCHAIN__`. Click "Create Account" / "Sign In" (allowed). If an email verification code is needed, stop and flag it for the user.
- **CAPTCHA visible** (`captcha: true` alone is common: Ashby/Greenhouse/Lever run invisible reCAPTCHA at submit, and that's fine): only flag it if the form is blocked by a visible challenge.

### 6. Update the note
**Links:** the tailored note and the application note share a file name, so always link by path: `cv_used: "[[01 Career/CV & Positioning/Tailored/<file>|CV — <Company>]]"` and, in the tailored note, `application: "[[wiki/applications/<note>|<Company> <Role>]]"`.
On the role's note (read its current properties first; never overwrite the user's edits): set `cv_version`, `cv_used`, `updated: today`, and **mark it applied now**: `stage: applied`, `applied: today`, `next_action: "follow up — confirm you clicked Submit"`, `next_date: today + 7`. Append one pipeline log line per run (newest first) listing the roles. If the user later says they didn't submit one, set it back to `stage: found`.

### 7. Final report (after all roles)
1. A table: Company · Role · Tab name · Status (`ready to submit` / `needs you: …` / `manual` / `closed`) · CV PDF.
2. Per role: **what to check** (flagged fields, motivation answer, anything guessed-free but worth a look) and the tailored-CV change list.
3. Close with: *Review each tab, fix anything, and click Submit yourself. They're already marked applied in the tracker; tell me if you skip one and I'll set it back.*
4. Then outreach. If this run came from the job-scout chain, go straight on to the `job-network` skill for the same roles (1–2 people per company). Otherwise offer it in one line: *Want me to find people to message at these companies? Say "network <Company>".*

## After the user says "submitted X"
Roles are already marked applied at fill time (step 6). Only if a role is still `found`, run the vault's STATUS UPDATE: `stage: applied`, `applied: today`, `next_action: "follow up"`, `next_date: today + 7`, `updated`, and append one line to the `## Log` of `wiki/synthesis/application-pipeline.md` (newest first): `- **YYYY-MM-DD**: applied to <Company> — <Role> (job-apply, CV: <version> tailored).`

## Writes allowed
- `wiki/applications/<note>.md` (properties above), `wiki/synthesis/application-pipeline.md` (Log only), `wiki/log.md` (only via JOB INGEST)
- `01 Career/CV & Positioning/Tailored/` and `~/Desktop/Resume/Tailored/`
- Your scratchpad (fields/fill JSON)
- Nothing else in the vault. Never edit `application-profile.md` unless the user asks you to add or change an answer.
