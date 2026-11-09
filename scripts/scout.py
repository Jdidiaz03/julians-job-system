"""Job scout: checks the public job boards of the companies in watchlist.json
and writes new matching postings to out/candidates-YYYY-MM-DD.md.

The job-scout Claude skill then reads that file, checks fit, and adds the good
ones to the Obsidian tracker. Standard library only; no API keys.

CONFIG: the regexes below (ROLE, SENIOR, OFF_TARGET, LANGUAGE_SEAT, EXCLUDE,
EU_PLACES, US_PLACES) are Julian's own target-role filters, kept as a working
example. Edit them to match YOUR role families, locations and language
constraints — they should mirror whatever you write in
wiki/synthesis/job-search-profile.md. Keep the two files in sync.

Usage:
    python3 scout.py                   # normal run: writes candidates + updates seen.json
    python3 scout.py --dry-run         # print matches, write nothing
    python3 scout.py --describe <url>  # print a posting's full description via the
                                       # ATS API (job pages are JavaScript, WebFetch sees little)
"""

import concurrent.futures
import json
import re
import ssl
import sys
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
WATCHLIST = HERE / "watchlist.json"
SEEN = HERE / "seen.json"
OUT = HERE / "out"

# --- What counts as a match -------------------------------------------------
# EDIT THESE to your own role families, locations and language constraints.
# The patterns below are Julian's own (AI implementation, deployment,
# transformation/consulting, strategy, tech sales/GTM, adjacent), kept as a
# working example of the shape these regexes should take.

ROLE = re.compile(
    r"\b(ai|a\.i\.|genai|llm|automation|implementation|solutions?|deployment|"
    r"forward[- ]deployed|transformation|digital|strategy|strategic|consult\w*|"
    r"business analyst|business operations|bizops|sales development|sdr|bdr|"
    r"business development|(associate|junior) account executive|pre-?sales|"
    r"customer success|onboarding|gtm|go[- ]to[- ]market|revenue operations|revops|"
    r"sales operations|partnerships?|founder'?s associate|chief of staff|"
    r"product operations|becari[oa]|pr[aá]cticas|graduate|trainee)\b",
    re.I,
)

# Too senior. "Chief of staff" is re-allowed below. Enterprise/strategic AEs
# are quota-carrying roles that want years of closing experience.
SENIOR = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|head|director|manager|vp|partner|"
    r"vice president|chief|architect|phd|distinguished|expert|mid-level|"
    r"enterprise account|strategic account|mid[- ]market account)\b",
    re.I,
)

# Functions outside your target families, even as internships.
OFF_TARGET = re.compile(
    r"\b(software engineer\w*|backend|back-end|frontend|front-end|full[- ]stack|"
    r"infrastructure|sre|devops|platform engineer|research|scientist|applied science|"
    r"machine learning|\bml\b|data engineer|security|qa\b|quality assurance|"
    r"hardware|firmware|mechanical|electrical|legal|juriste|lawyer|counsel|"
    r"ux|ui\b|designer|design\b|copywriter|communication|[ée]v[ée]nementiel|events?|"
    r"it support|technician|fraud|risk|compliance|finance|financial|accounting|"
    r"accountant|payroll|tax|treasury|recruit\w*|talent|people|hr\b|"
    r"sourcing|procurement|night shift|freelance|media|affiliat\w*|crm|"
    r"field sales|aut[oó]nomo?|test|expression of interest|team lead\w*|leader)\b",
    re.I,
)

# Language/market-specific seats you can't fill — EDIT to the languages you
# don't speak at professional level.
LANGUAGE_SEAT = re.compile(
    r"\b(german|dach|italian|italy|portuguese|portugu[eê]s|mandarin|chinese|japan\w*|"
    r"korea\w*|nordics?|dutch|benelux|polish|hebrew|israel|arabic|turkish|meta|apac|"
    r"anz|singlish|french|fran[cç]ais|france|africa|latam)\b",
    re.I,
)

# Student-status contracts you can't hold (e.g. German/French enrolment required).
EXCLUDE = re.compile(
    r"\b(werkstudent|working student|alternance|alternant|apprenti\w*|co-op)\b", re.I)

EU_PLACES = re.compile(
    r"(spain|espa[nñ]a|madrid|barcelona|valencia|m[aá]laga|sevilla|bilbao|"
    r"ireland|dublin|cork|united kingdom|\buk\b|england|london|manchester|edinburgh|"
    r"netherlands|amsterdam|rotterdam|france|paris|lyon|germany|berlin|munich|"
    r"m[uü]nchen|hamburg|portugal|lisbon|lisboa|porto|sweden|stockholm|denmark|"
    r"copenhagen|belgium|brussels|austria|vienna|switzerland|zurich|italy|milan|"
    r"europe|emea|\beu\b)",
    re.I,
)
REMOTE = re.compile(r"remote|anywhere|distributed", re.I)
US_PLACES = re.compile(
    r"(united states|\busa?\b|new york|san francisco|boston|seattle|austin|"
    r"chicago|denver|los angeles|miami|atlanta|texas|california|florida|"
    r"washington|dallas|houston|north america|americas)",
    re.I,
)

# Postings older than this are usually filled or stale.
MAX_AGE_DAYS = 120


def title_ok(title):
    if EXCLUDE.search(title) or OFF_TARGET.search(title) or LANGUAGE_SEAT.search(title):
        return False
    if SENIOR.search(title) and not re.search(r"chief of staff", title, re.I):
        return False
    if re.search(r"\bintern(ship)?\b|\bstage\b", title, re.I):
        return True  # any on-target internship
    return bool(ROLE.search(title))


def location_ok(loc):
    """EU/UK locations (office or remote); US only when remote. Edit to your own regions."""
    if not loc:
        return True  # unknown: let the skill decide
    if EU_PLACES.search(loc):
        return True
    return bool(REMOTE.search(loc) and US_PLACES.search(loc))


def fresh(posted):
    if not posted:
        return True
    try:
        return (date.today() - date.fromisoformat(posted)).days <= MAX_AGE_DAYS
    except ValueError:
        return True


# --- Fetching ---------------------------------------------------------------

def _ssl_context():
    # Some Mac python3 builds ship without a CA bundle; use certifi, else macOS's own.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")


SSL_CONTEXT = _ssl_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 job-scout"})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as r:
        return json.loads(r.read())


def jobs_for(company):
    """Return [(title, location, url, posted)] for one company."""
    ats, slug = company["ats"], company["slug"]
    if ats == "greenhouse":
        d = fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        return [(j["title"], (j.get("location") or {}).get("name", ""),
                 j["absolute_url"], (j.get("updated_at") or "")[:10]) for j in d["jobs"]]
    if ats == "lever":
        d = fetch(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        out = []
        for j in d:
            cats = j.get("categories") or {}
            loc = ", ".join(cats.get("allLocations") or [cats.get("location") or ""])
            if j.get("workplaceType") == "remote":
                loc += " (remote)"
            posted = date.fromtimestamp(j["createdAt"] / 1000).isoformat() if j.get("createdAt") else ""
            out.append((j["text"], loc, j["hostedUrl"], posted))
        return out
    if ats == "ashby":
        d = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        out = []
        for j in d["jobs"]:
            locs = [j.get("location") or ""] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
            loc = ", ".join(l for l in locs if l)
            if j.get("isRemote"):
                loc += " (remote)"
            out.append((j["title"], loc, j["jobUrl"], (j.get("publishedAt") or "")[:10]))
        return out
    if ats == "workable":
        d = fetch(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
        return [(j["title"], ", ".join(filter(None, [j.get("city"), j.get("country")])) +
                 (" (remote)" if j.get("telecommuting") else ""),
                 j["url"], (j.get("published_on") or "")[:10]) for j in d["jobs"]]
    if ats == "smartrecruiters":
        d = fetch(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100")
        out = []
        for j in d.get("content", []):
            l = j.get("location") or {}
            loc = ", ".join(filter(None, [l.get("city"), l.get("country")])) + (" (remote)" if l.get("remote") else "")
            out.append((j["name"], loc, f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
                        (j.get("releasedDate") or "")[:10]))
        return out
    raise ValueError(f"unknown ats {ats}")


def check(company):
    try:
        jobs = jobs_for(company)
    except Exception as e:  # one broken board shouldn't stop the run
        return company, [], f"{type(e).__name__}: {e}"
    return company, [j for j in jobs if title_ok(j[0]) and location_ok(j[1]) and fresh(j[3])], None


def strip_html(text):
    import html
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text or "", flags=re.I)
    text = re.sub(r"<li[^>]*>", "- ", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", html.unescape(text)))
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def describe(url):
    """Full posting text for a Greenhouse, Lever or Ashby URL."""
    m = re.search(r"greenhouse\.io/(\w[\w-]*)/jobs/(\d+)", url)
    if m:
        d = fetch(f"https://boards-api.greenhouse.io/v1/boards/{m[1]}/jobs/{m[2]}")
        return d["title"], (d.get("location") or {}).get("name", ""), strip_html(d.get("content"))
    m = re.search(r"gh_jid=(\d+)", url)
    if m:  # company-hosted Greenhouse page: find the board via the watchlist
        for c in json.loads(WATCHLIST.read_text())["companies"]:
            if c["ats"] == "greenhouse":
                try:
                    d = fetch(f"https://boards-api.greenhouse.io/v1/boards/{c['slug']}/jobs/{m[1]}")
                    return d["title"], (d.get("location") or {}).get("name", ""), strip_html(d.get("content"))
                except Exception:
                    continue
    m = re.search(r"lever\.co/([\w-]+)/([\w-]+)", url)
    if m:
        d = fetch(f"https://api.lever.co/v0/postings/{m[1]}/{m[2]}")
        lists = "\n\n".join(f"{l['text']}\n{strip_html(l['content'])}" for l in d.get("lists", []))
        return d["text"], (d.get("categories") or {}).get("location", ""), \
            strip_html(d.get("description", "")) + "\n\n" + lists + "\n\n" + strip_html(d.get("additional", ""))
    m = re.search(r"ashbyhq\.com/([\w-]+)/([\w-]+)", url)
    if m:
        d = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{m[1]}?includeCompensation=true")
        for j in d["jobs"]:
            if j["id"] == m[2] or j["jobUrl"].rstrip("/").endswith(m[2]):
                comp = (j.get("compensation") or {}).get("compensationTierSummary") or ""
                body = j.get("descriptionPlain") or strip_html(j.get("descriptionHtml"))
                return j["title"], j.get("location", ""), (f"Compensation: {comp}\n\n" if comp else "") + body
        raise LookupError("posting not on the board any more (probably closed)")
    raise ValueError("not a Greenhouse, Lever or Ashby URL; use WebFetch instead")


def main():
    if "--describe" in sys.argv:
        url = sys.argv[sys.argv.index("--describe") + 1]
        try:
            title, loc, text = describe(url)
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            sys.exit(1)
        print(f"# {title}\nLocation: {loc}\n\n{text}")
        return

    dry = "--dry-run" in sys.argv
    companies = json.loads(WATCHLIST.read_text())["companies"]
    seen = set(json.loads(SEEN.read_text())) if SEEN.exists() else set()

    new, errors = [], []
    with concurrent.futures.ThreadPoolExecutor(12) as ex:
        for company, matches, err in ex.map(check, companies):
            if err:
                errors.append(f"{company['name']}: {err}")
            for title, loc, url, posted in matches:
                if url not in seen:
                    new.append((company, title, loc, url, posted))

    new.sort(key=lambda r: (r[0]["name"].lower(), r[1]))
    print(f"{len(companies)} boards checked, {len(new)} new matches, {len(errors)} errors")
    for e in errors:
        print("  error:", e)

    if dry:
        for c, title, loc, url, posted in new:
            print(f"- {c['name']} | {title} | {loc} | {posted} | {url}")
        return

    if new:
        OUT.mkdir(exist_ok=True)
        path = OUT / f"candidates-{date.today().isoformat()}.md"
        lines = [
            "---",
            "status: pending",
            f"created: {date.today().isoformat()}",
            f"count: {len(new)}",
            "---",
            "",
            f"# Watchlist candidates, {date.today().isoformat()}",
            "",
            "Title/location pre-filter only. The job-scout skill checks fit before anything reaches the tracker.",
            "",
            "| Company | Title | Location | Posted | Link |",
            "|---|---|---|---|---|",
        ]
        for c, title, loc, url, posted in new:
            cell = lambda s: s.replace("|", "/")
            lines.append(f"| {c['name']} | {cell(title)} | {cell(loc)} | {posted} | {url} |")
        # Append if a file for today already exists (e.g. a manual re-run).
        if path.exists():
            existing = path.read_text()
            path.write_text(existing.rstrip("\n") + "\n" + "\n".join(lines[12:]) + "\n")
        else:
            path.write_text("\n".join(lines) + "\n")
        print(f"wrote {path}")

    seen.update(r[3] for r in new)
    SEEN.write_text(json.dumps(sorted(seen), indent=0))


if __name__ == "__main__":
    main()
