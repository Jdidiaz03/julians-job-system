"""US / worldwide-remote board check for the (optional) job-scout-us skill.

Pulls the free public JSON feeds of Himalayas, Jobicy, Remote OK and Remotive,
keeps titles in your own target role families (edit ROLE/OFF_TARGET/SENIOR
below to match wiki/synthesis/job-search-profile.md's "US-remote scout"
section), and writes new matches to out/us-candidates-YYYY-MM-DD.md. The
job-scout-us skill then checks fit, pay and residence before anything reaches
the tracker. Standard library only; no keys.

CONFIG: FLOOR_ANNUAL / FLOOR_HOURLY are your pay floor — edit to taste or
remove the floor entirely by making pay_ok always return True.

Usage:
    python3 remote_boards.py            # normal run: writes candidates + updates us-seen.json
    python3 remote_boards.py --dry-run  # print matches, write nothing
"""

import json
import re
import sys
import urllib.parse
from datetime import date, datetime, timezone
from pathlib import Path

from scout import OUT, fetch, fresh

HERE = Path(__file__).parent
SEEN = HERE / "us-seen.json"

# --- What counts as a match -------------------------------------------------
# EDIT to your own families. The patterns below are a working example
# (AI implementation, ops/analyst, customer success/support, sales/BD, AI
# training/annotation) — keep in sync with job-search-profile.md.

ROLE = re.compile(
    r"\bAI\b|automation|implementation|deployment|forward.deployed|solutions? (consultant|engineer|analyst)"
    r"|operations|\bops\b|bizops|revops|business analyst|data analyst|research analyst|analyst"
    r"|project (coordinator|manager)|program coordinator|chief of staff|founder'?s associate"
    r"|customer success|customer support|customer experience|support specialist|onboarding|account (manager|executive)"
    r"|technical support|client success|client services"
    r"|\bSDR\b|\bBDR\b|sales development|business development|partnerships|sales representative|inside sales"
    r"|annotat|AI trainer|AI tutor|evaluat|red.team|prompt|rater|labell?ing",
    re.I,
)
SENIOR = re.compile(r"\b(senior|sr\.?|staff|principal|lead|head|director|vp|vice president|manager of|executive)\b", re.I)
OFF_TARGET = re.compile(
    r"engineer(ing)? manager|software engineer|developer|devops|nurse|physician|clinical|therapist|driver|"
    r"warehouse|mechanic|electrician|accountant|bookkeep|tax |payroll|attorney|paralegal|teacher|"
    r"german|french|dutch|italian|japanese|korean|mandarin|polish|turkish|hebrew|arabic|greek|portuguese|"
    r"swedish|danish|norwegian|finnish|czech|romanian|hungarian|russian|ukrainian|cantonese|toisan|vietnamese|thai",
    re.I,
)
# EDIT ABROAD_OK to your own country/region of residence.
ABROAD_OK = re.compile(r"anywhere|worldwide|global|emea|europe|\beu\b|international", re.I)
US_ONLY = re.compile(r"\b(us|usa|u\.s\.|united states|canada|north america|americas)\b|us timezones", re.I)

# Pay floor: $3,000 a month. Annual equivalent, and hourly at 40 h/week. EDIT to your own floor.
FLOOR_ANNUAL = 36_000
FLOOR_HOURLY = 18

HIMALAYAS_QUERIES = [
    "AI implementation", "AI operations", "automation", "solutions consultant", "implementation specialist",
    "customer success", "customer support", "onboarding specialist", "business operations",
    "business analyst", "operations analyst", "sales development", "business development",
    "AI trainer",
]


def title_ok(title):
    if not title or OFF_TARGET.search(title):
        return False
    if SENIOR.search(title):
        return False
    return bool(ROLE.search(title))


def location_class(loc):
    """abroad-ok (open to someone where you live), us-only, or unknown."""
    if not loc:
        return "unknown"
    if ABROAD_OK.search(loc):
        return "abroad-ok"
    if US_ONLY.search(loc):
        return "us-only"
    return "unknown"


def pay_ok(lo, hi, period):
    """False only when a stated salary is clearly below the floor."""
    try:
        top = float(hi or lo or 0)
    except (TypeError, ValueError):
        return True
    if top <= 0:
        return True
    period = (period or "").lower()
    if period.startswith("hour"):
        return top >= FLOOR_HOURLY
    if period.startswith("month"):
        return top >= FLOOR_ANNUAL / 12
    return top >= FLOOR_ANNUAL


def salary_text(lo, hi, cur, period):
    try:
        lo, hi = int(float(lo or 0)), int(float(hi or 0))
    except (TypeError, ValueError):
        return ""
    if not lo and not hi:
        return ""
    rng = f"{lo:,}–{hi:,}" if lo and hi and lo != hi else f"{(hi or lo):,}"
    return f"{cur or ''} {rng} {period or ''}".strip()


def iso(ts):
    if not ts:
        return ""
    try:
        if str(ts).isdigit():
            return datetime.fromtimestamp(int(ts), timezone.utc).date().isoformat()
        return str(ts)[:10]
    except (ValueError, OSError):
        return ""


# --- Boards: each returns [dict(board, company, title, location, salary, pay_ok, posted, url)] ----

def himalayas():
    out = []
    for q in HIMALAYAS_QUERIES:
        for scope in ("worldwide=true",):  # add e.g. "country=ES" for your own country filter
            d = fetch(f"https://himalayas.app/jobs/api/search?q={urllib.parse.quote(q)}&{scope}")
            for j in d.get("jobs", []):
                seniority = " ".join(j.get("seniority") or [])
                if seniority and not re.search(r"entry|junior|mid", seniority, re.I):
                    continue
                loc = ", ".join(j.get("locationRestrictions") or []) or "Worldwide"
                lo, hi, per = j.get("minSalary"), j.get("maxSalary"), j.get("salaryPeriod")
                out.append(dict(board="Himalayas", company=j.get("companyName", ""), title=j.get("title", ""),
                                location=loc, salary=salary_text(lo, hi, j.get("currency"), per),
                                pay_ok=pay_ok(lo, hi, per), posted=iso(j.get("pubDate")),
                                url=j.get("guid") or j.get("applicationLink", "")))
    return out


def jobicy():
    out = []
    for geo in ("", "&geo=emea"):  # add your own country/region geo filter if Jobicy supports it
        d = fetch(f"https://jobicy.com/api/v2/remote-jobs?count=50{geo}")
        for j in d.get("jobs", []):
            if re.search(r"senior|lead|director|executive", j.get("jobLevel") or "", re.I):
                continue
            lo, hi, per = j.get("salaryMin"), j.get("salaryMax"), j.get("salaryPeriod")
            out.append(dict(board="Jobicy", company=j.get("companyName", ""), title=j.get("jobTitle", ""),
                            location=j.get("jobGeo", ""), salary=salary_text(lo, hi, j.get("salaryCurrency"), per),
                            pay_ok=pay_ok(lo, hi, per), posted=iso(j.get("pubDate")), url=j.get("url", "")))
    return out


def remoteok():
    out = []
    for j in fetch("https://remoteok.com/api")[1:]:  # item 0 is a legal notice
        lo, hi = j.get("salary_min"), j.get("salary_max")
        out.append(dict(board="Remote OK", company=j.get("company", ""), title=j.get("position", ""),
                        location=j.get("location", ""), salary=salary_text(lo, hi, "USD", "year"),
                        pay_ok=pay_ok(lo, hi, "year"), posted=iso(j.get("date")), url=j.get("url", "")))
    return out


def remotive():
    out = []
    for j in fetch("https://remotive.com/api/remote-jobs").get("jobs", []):
        out.append(dict(board="Remotive", company=j.get("company_name", ""), title=j.get("title", ""),
                        location=j.get("candidate_required_location", ""), salary=j.get("salary", ""),
                        pay_ok=True, posted=iso(j.get("publication_date")), url=j.get("url", "")))
    return out


BOARDS = [himalayas, jobicy, remoteok, remotive]


def main():
    dry = "--dry-run" in sys.argv
    seen = set(json.loads(SEEN.read_text())) if SEEN.exists() else set()

    rows, errors, counts = {}, [], {}
    for board in BOARDS:
        try:
            jobs = board()
        except Exception as e:  # one broken board shouldn't stop the run
            errors.append(f"{board.__name__}: {type(e).__name__}: {e}")
            continue
        kept = 0
        for j in jobs:
            if not j["url"] or j["url"] in seen or j["url"] in rows:
                continue
            if not (title_ok(j["title"]) and j["pay_ok"] and fresh(j["posted"])):
                continue
            j["class"] = location_class(j["location"])
            rows[j["url"]] = j
            kept += 1
        counts[board.__name__] = (len(jobs), kept)

    order = {"abroad-ok": 0, "unknown": 1, "us-only": 2}
    new = sorted(rows.values(), key=lambda j: (order[j["class"]], j["company"].lower(), j["title"]))
    summary = ", ".join(f"{b} {n} fetched / {k} kept" for b, (n, k) in counts.items())
    print(f"{len(new)} new matches ({summary}); {len(errors)} errors")
    for e in errors:
        print("  error:", e)

    if dry:
        for j in new:
            print(f"- [{j['class']}] {j['company']} | {j['title']} | {j['location']} | {j['salary']} | {j['posted']} | {j['url']}")
        return

    if new:
        OUT.mkdir(exist_ok=True)
        today = date.today().isoformat()
        path = OUT / f"us-candidates-{today}.md"
        cell = lambda s: str(s or "").replace("|", "/").replace("\n", " ")
        table = [f"| {cell(j['board'])} | {cell(j['company'])} | {cell(j['title'])} | {cell(j['location'])} | "
                 f"{j['class']} | {cell(j['salary'])} | {j['posted']} | {j['url']} |" for j in new]
        if path.exists():  # a manual re-run on the same day appends
            path.write_text(path.read_text().rstrip("\n") + "\n" + "\n".join(table) + "\n")
        else:
            head = [
                "---", "status: pending", f"created: {today}", f"count: {len(new)}", "---", "",
                f"# US / worldwide-remote board candidates, {today}", "",
                "Title, pay-floor and freshness pre-filter only. `abroad-ok` = the posting lists worldwide, EMEA, "
                "Europe or your region; `us-only` = US/Canada only (tier 2 max). The job-scout-us skill reads each "
                "posting before anything reaches the tracker.", "",
                f"Boards: {summary}." + (f" Errors: {'; '.join(errors)}." if errors else ""), "",
                "| Board | Company | Title | Location | Class | Salary | Posted | Link |",
                "|---|---|---|---|---|---|---|---|",
            ]
            path.write_text("\n".join(head + table) + "\n")
        print(f"wrote {path}")

    seen.update(j["url"] for j in new)
    SEEN.write_text(json.dumps(sorted(seen), indent=0))


if __name__ == "__main__":
    main()
