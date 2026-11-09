# Setup: a Claude-Code job-search system

This is a genericized copy of a working system (Julian's own), stripped of his personal
data and rewritten so you can stand up the same thing for yourself. It's a Claude Code
skill-based system that **finds** jobs, **tailors** a CV to each one, **fills** application
forms (without ever submitting), and **finds LinkedIn contacts** to reach out to — backed
by an Obsidian vault that acts as the single source of truth / tracker. Nothing happens
without you reviewing it: the system never clicks Submit, never clicks Connect/Send on
LinkedIn, and never invents an answer.

**It's built for Mac + Safari + Obsidian.** If that's not your setup, read the callouts
below — the mechanism (Claude Code skills + a vault + helper scripts) is portable, but
the password handling and form-filling scripts specifically assume Safari's AutoFill and
the macOS Keychain.

Work through this in order — later steps assume earlier ones are done.

---

## 1. Prerequisites

Install/set up before touching any of the skill files:

1. **Obsidian** (desktop app), with the core **Bases** plugin enabled (Settings → Core
   plugins → Bases). This is what renders `applications.base` as the Inbox/Pipeline tables.
2. **Claude Code**, if you don't already have it running.
3. **Safari as your browser for this**, logged into the sites you'll apply through (so
   AutoFill can save new passwords and reuse existing ones). Turn on: Safari → Settings →
   Advanced → "Show features for web developers", then Safari → Settings → Developer →
   "Allow JavaScript from Apple Events". The scripts drive Safari through AppleScript's
   `do JavaScript`, which needs that switch on.
   - **Not on Mac / not using Safari?** Use the Chromium fallback instead (`apply.py`,
     already in `scripts/`) — it drives its own Playwright-controlled Chromium window and
     handles Keychain-equivalent password storage the same way. The `job-apply` SKILL.md
     calls out where to swap commands.
4. **An Apify account** (apify.com) + API token, for `job-network`'s people search. Store
   the token in the macOS Keychain so the script never has it in a file:
   ```
   security add-generic-password -a apify -s apify-api -w "<your Apify API token>"
   ```
5. **python3** with:
   ```
   pip3 install python-docx pypdf certifi
   ```
   Add `playwright` (+ `playwright install chromium`) only if you're using the Chromium
   fallback instead of Safari.
6. **Pages** (free, comes with macOS) for DOCX→PDF conversion via `pages_pdf.py` — this is
   what the system uses since Microsoft Word isn't assumed to be installed. If you do have
   Word, `apply.py pdf` uses it instead and keeps the original layout slightly more exactly.
7. **Indeed connector** (optional): if your Claude Code setup has a claude.ai Indeed
   connector available, the scout will use it as one of several sources. It works fine
   without it — just one less source.

---

## 2. Set up the vault

Create your Obsidian vault (anywhere you like) with this structure:

```
<Your Vault>/
├── CLAUDE.md                              ← from vault-template/CLAUDE.md
└── wiki/
    ├── log.md                             ← from vault-template/log.md
    ├── applications/                       ← empty folder, the scout/apply/network skills write here
    └── synthesis/
        ├── job-search-profile.md          ← from vault-template/job-search-profile.md
        └── application-pipeline.md        ← from vault-template/application-pipeline.md
01 Career/
├── CV & Positioning/
│   ├── application-profile.md             ← from vault-template/application-profile.md
│   ├── outreach-voice.md                  ← from vault-template/outreach-voice.md
│   ├── CV Versions/                        ← your own CV, see step 3
│   └── Tailored/                           ← empty folder, job-apply/job-scout write tailored CVs here
└── Job Applications/
    ├── applications.base                   ← from vault-template/applications.base
    └── Stage options.md                    ← from vault-template/Stage options.md
```

`01 Career/` can live inside the Obsidian vault folder or just outside it (Julian keeps
his inside the vault, as a "raw" layer the agent treats as read-only except for the two
named exceptions in CLAUDE.md). Either works — just be consistent, and make sure the paths
in CLAUDE.md and every SKILL.md agree with where you actually put things.

**Then fill in the three "you" files properly** — this is the part that actually makes
the system find relevant roles and sound like you, not a 10-minute copy-paste job:

- **`job-search-profile.md`**: your role families, locations, seniority range, any
  language or work-authorization filters, and (if you want it) a US/worldwide-remote
  pay floor and families. This is what the scout reads every run — vague criteria here
  means noisy, useless results.
- **`application-profile.md`**: your real contact info, education, work authorization
  per country, and the standard form answers (salary approach, EEO defaults, reusable
  "why this company" / "proudest achievement" drafts).
- **`outreach-voice.md`**: paste a real short message in your own voice as the reference
  draft, then write your own connection-note templates. This one matters more than it
  looks — it's the difference between notes that sound like you and generic LinkedIn spam.

---

## 3. Your CV

Put at least one base CV in `01 Career/CV & Positioning/CV Versions/`, as both a markdown
version (for Claude to read when tailoring) and a DOCX (for the layout job-apply/job-scout
copy when building a tailored file): `CV — Base.md` and `~/Desktop/Resume/<Your Name> CV -
Base.docx`.

One version is enough to start. Julian keeps three (one per role family he targets) because
it measurably improved fit — add more later once you know which role families you're
actually applying to.

---

## 4. Install the skills

Copy the four skill folders into `~/.claude/skills/`:

```
cp -r skills/job-scout ~/.claude/skills/
cp -r skills/job-apply ~/.claude/skills/
cp -r skills/job-network ~/.claude/skills/
cp -r skills/job-scout-us ~/.claude/skills/   # optional — see note below
```

Then **open every `SKILL.md` you copied and fix the paths**: each one has placeholders
like `~/Desktop/Obsidian/<Vault Name>/` — change `<Vault Name>` (and anything else
placeholder-shaped) to match where you actually put your vault in step 2. This is a
five-minute find-and-replace, but skipping it means the skill reads the wrong folder on
its first run.

**`job-scout-us` is optional.** Only install it if you also want US-remote / worldwide-remote
roles in addition to your local-market search. If you skip it, delete that folder — nothing
else in the system depends on it, and `job-scout`'s own SKILL.md already says to skip US
searches only "if you're using that skill."

---

## 5. Install the scripts

Copy the scripts folder somewhere stable — Julian uses `~/Desktop/Claude Projects/job-scout/`
(same name the skills reference by default):

```
mkdir -p ~/Desktop/Claude\ Projects/job-scout
cp scripts/*.py ~/Desktop/Claude\ Projects/job-scout/
cp scripts/watchlist.example.json ~/Desktop/Claude\ Projects/job-scout/watchlist.json
```

Then edit `watchlist.json`: it's the list of companies the free scout script checks every
run via their public job-board APIs (Greenhouse, Lever, Ashby, Workable, SmartRecruiters).
Add companies you care about that use one of those ATSes — find a company's `slug` by
looking at its careers page URL (e.g. `boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`,
`jobs.ashbyhq.com/<slug>`). This file can start empty (`{"companies": []}`) — the scout
still works from Indeed + web search alone, just with one less free source.

No script needs its own config edits beyond the regex filters mentioned in step 2 (they're
commented inline in `scout.py` and `remote_boards.py` — edit them to match your own
`job-search-profile.md` families and keep the two in sync).

If you're using `job-scout-us`, also note it calls `remote_boards.py`, which imports from
`scout.py` — both need to be in the same folder.

---

## 6. Test run order

Do these one at a time, in this order, so you catch setup mistakes early and cheaply:

1. **`job-scout` on a narrow focus**, e.g. tell Claude "find jobs — just test it, focus on
   one role family". Check the report: did it read your profile correctly, find anything
   real, and write notes into `wiki/applications/`? Open `applications.base` in Obsidian
   and confirm the Inbox view shows them.
2. **Review the Inbox yourself** and pick one role tier-1 enough to actually try applying to.
3. **`job-apply` on that one role.** This needs Safari open and you at the screen — it's
   never meant to run unattended. Watch it tailor the CV, open the application, and fill
   the form. Read the final report closely: it'll flag anything it couldn't answer
   truthfully. **Review the tab yourself before clicking Submit** — that's the whole point.
4. **`job-network` on the same company.** Check `apify_people.py credit` first to confirm
   the Keychain token is readable. This one hands you pre-filled LinkedIn notes to copy and
   send yourself — it never touches your LinkedIn account directly.

Only after all three work on one role should you trust a bigger batch run.

---

## 7. How to adjust this to your own job search

**Places you'll actually want to edit as you learn what works:**
- `job-search-profile.md` — loosen/tighten families, add companies to the target-firm
  sweep, adjust seniority range, change the US-remote pay floor.
- `application-profile.md` — fill in `[fill in: …]` placeholders as you discover what forms
  ask for; update your "why this company" draft once you've sent a few and know what reads
  well.
- `outreach-voice.md` — add your own edited notes to "Approved notes" every time you tweak
  one before sending; the skill reads these back to match your voice more closely over time.
- `scout.py` / `remote_boards.py` regexes — tune as you see false positives/negatives in
  what the scout surfaces.
- `watchlist.json` — add companies as you think of them.

**Parts you shouldn't touch** (they're there on purpose, and loosening them defeats the
point of letting an agent handle your job applications):
- job-apply's **never-click-Submit** rule, and the scripts' refusal to click
  submit-like buttons.
- job-apply's **never-invent-an-answer** rule.
- **Password handling** — passwords only ever flow through `__KEYCHAIN__` / Safari
  AutoFill, never typed into chat or a file.
- job-network's **LinkedIn automation ban** — it only ever opens profile URLs for you to
  read; it never scripts a Connect, Send or Follow. This protects your actual LinkedIn
  account from an Agreement violation.
- The **authenticity rule** in both job-apply and job-network: never dressing up a CV
  credential as genuine company-specific interest.

---

## A note on what's genericized here vs. what's still a judgment call

This package strips out the original owner's name, email, nationality/visa specifics,
schools and CV content, and turns his specific role-family/location/language filters into
editable templates with his versions kept as worked examples (since empty criteria produce
a useless scout). A few things were judgment calls rather than clean removals:
- The regex-based filters in `scout.py` / `remote_boards.py` are kept as *working defaults*
  rather than blanked out, since an empty regex matches nothing — you're meant to edit them,
  not delete them.
- The Obsidian Bases `Inbox` view filter was corrected to `stage == "found"` (matching what
  every skill and CLAUDE.md actually describes the Inbox as showing) rather than copied
  verbatim — the original vault's live file had drifted to `stage == "applied"`, which looks
  like a stale edit rather than the intended behavior.
- `job-scout-us` is marked clearly optional throughout, since it's a genuine judgment call
  whether a given person wants a remote-income track alongside local-market search.
