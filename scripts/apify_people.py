#!/usr/bin/env python3
"""Find LinkedIn people for job-network through Apify (no LinkedIn login, your account is never touched).
The Apify token is read from the macOS Keychain (service "apify-api") and never printed.

  apify_people.py search "<query>" [--schools "Your School,Your Other School"] [--locations Madrid]
                         [--titles "Recruiter,Talent Acquisition"] [--match <company>] [--max 25]
      harvestapi/linkedin-profile-search, Short mode: one page of 25 profiles = $0.10 (check Apify's current pricing).
      Lines starting with * have --match in a current employer's name.
  apify_people.py profiles <profile id | URL | public id> ...
      harvestapi/linkedin-profile-scraper: ~$0.004 a profile. Shows the real URL, current jobs and schools,
      so you can check the person still works there and whether an alumnus is still studying or has graduated.
  apify_people.py credit

SETUP: before first use, store your Apify API token in the macOS Keychain:
  security add-generic-password -a apify -s apify-api -w "<your Apify API token>"
"""
import argparse, json, subprocess, sys

TOKEN = subprocess.run(["security", "find-generic-password", "-s", "apify-api", "-w"],
                       capture_output=True, text=True, check=True).stdout.strip()


def api(method, path, body=None):
    # curl, not urllib: some python.org builds have no CA certificates installed.
    cmd = ["curl", "-sS", "--fail", "-X", method, f"https://api.apify.com/v2/{path}",
           "-H", f"Authorization: Bearer {TOKEN}", "-H", "Content-Type: application/json"]
    if body is not None:
        cmd += ["-d", json.dumps(body)]
    return json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600).stdout)


def run(actor, body, cap):
    # The cap must stay above $0.10, or the search actor stops before its first page.
    return api("POST", f"acts/{actor}/run-sync-get-dataset-items?maxTotalChargeUsd={cap}", body)


def csv(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


def loc(p):
    l = p.get("location")
    return l.get("linkedinText") if isinstance(l, dict) else l


def search(a):
    body = {"profileScraperMode": "Short", "searchQuery": a.query, "takePages": 1, "maxItems": a.max}
    for key, val in (("schools", a.schools), ("locations", a.locations), ("currentJobTitles", a.titles)):
        if csv(val):
            body[key] = csv(val)
    for p in run("harvestapi~linkedin-profile-search", body, 0.3):
        cur = p.get("currentPositions") or []
        hit = a.match and any(a.match.lower() in (c.get("companyName") or "").lower() for c in cur)
        jobs = "; ".join(f"{c.get('title') or ''} @ {c.get('companyName') or ''}" for c in cur)[:130]
        print("*" if hit else " ", p.get("firstName"), p.get("lastName"), "|", jobs, "|", loc(p), "|", p.get("linkedinUrl"))


def profiles(a):
    ids = a.ids
    body = {"profileScraperMode": "Profile details no email ($4 per 1k)",
            "profileIds": [i for i in ids if i.startswith("ACwAA")],
            "urls": [i for i in ids if i.startswith("http") and "/in/ACwAA" not in i],
            "publicIdentifiers": [i for i in ids if not i.startswith(("http", "ACwAA"))]}
    body["profileIds"] += [i.rstrip("/").rsplit("/", 1)[1] for i in ids if "/in/ACwAA" in i]
    body = {k: v for k, v in body.items() if v}
    for p in run("harvestapi~linkedin-profile-scraper", body, 0.2):
        print("==", p.get("firstName"), p.get("lastName"), "|", p.get("linkedinUrl"), "|", loc(p))
        print("   headline:", (p.get("headline") or "")[:150])
        for e in (p.get("experience") or [])[:3]:
            dates = [d.get("text") if isinstance(d, dict) else d for d in (e.get("startDate"), e.get("endDate"))]
            print("   job:", e.get("position"), "@", e.get("companyName"), "|", " - ".join(str(d) for d in dates),
                  "|", (e.get("description") or "")[:160].replace("\n", " "))
        for s in (p.get("education") or [])[:4]:
            print("   school:", s.get("schoolName"), "|", s.get("degree") or "", "|", s.get("period") or "")


def credit(_):
    d = api("GET", "users/me/limits")["data"]
    print(f"Apify used this month: ${d['current']['monthlyUsageUsd']:.2f} of ${d['limits']['maxMonthlyUsageUsd']}")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--schools"); s.add_argument("--locations")
s.add_argument("--titles"); s.add_argument("--match"); s.add_argument("--max", type=int, default=25); s.set_defaults(f=search)
p = sub.add_parser("profiles"); p.add_argument("ids", nargs="+"); p.set_defaults(f=profiles)
sub.add_parser("credit").set_defaults(f=credit)
a = ap.parse_args()
try:
    a.f(a)
except subprocess.CalledProcessError as e:
    sys.exit(f"Apify call failed: {(e.stderr or '').replace(TOKEN, '***')[:300]}")
