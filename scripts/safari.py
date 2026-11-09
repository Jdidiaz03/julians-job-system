#!/usr/bin/env python3
"""Safari helper for the job-apply skill: same idea as apply.py, but drives your own
Safari (where your saved passwords live) via AppleScript `do JavaScript`.

Needs: Safari > Settings > Advanced > "Show features for web developers", then
Developer > "Allow JavaScript from Apple Events".

It never clicks a submit button, never touches password fields (you use Safari
AutoFill), and cannot attach files (Safari blocks that for scripts; `reveal` opens the
file in Finder so you can drag it in).

  python3 safari.py tabs                              list Safari tabs (window/tab, title, url)
  python3 safari.py open <url>                        open url in a new tab of the front window
  python3 safari.py goto <match> <url>                navigate the tab whose URL contains <match>
  python3 safari.py fields <match>                    print the tab's form fields as JSON
  python3 safari.py fill <match> <fill.json>          fill fields (same fill.json as apply.py)
  python3 safari.py click <match> "<text>" [--allow]  click a button/link; submit-like text refused
                                                      (--allow only for a start-application link
                                                      you explicitly okayed)
  python3 safari.py reveal <file>                     show a file in Finder for drag-and-drop
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply import FIELDS_JS, PAGE_JS, SUBMIT_WORDS, best_match  # noqa: E402


def osa(script):
    r = subprocess.run(["osascript", "-"], input=script, capture_output=True, text=True)
    if r.returncode:
        sys.exit("AppleScript error: " + r.stderr.strip())
    return r.stdout.rstrip("\n")


def find_tab(match):
    """AppleScript reference string for the first tab whose URL contains `match`."""
    out = osa(f'''
tell application "Safari"
  repeat with wi from 1 to count of windows
    repeat with ti from 1 to count of tabs of window wi
      if (URL of tab ti of window wi) contains {json.dumps(match)} then return (id of window wi as text) & "," & ti
    end repeat
  end repeat
  return ""
end tell''')
    if not out:
        sys.exit(f"no Safari tab with {match!r} in its URL")
    wid, ti = out.split(",")
    return f"tab {ti} of (first window whose id is {wid})"


def js(match, code):
    """Run JS (an expression) in the tab and return its JSON-decoded result."""
    wrapped = f"JSON.stringify((function(){{ return ({code}); }})())"
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(wrapped)
    # Find and run in one AppleScript call: window indexes shift if you switch windows.
    out = osa(f'''
set src to read POSIX file {json.dumps(f.name)} as «class utf8»
tell application "Safari"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t) contains {json.dumps(match)} then return (do JavaScript src in t)
    end repeat
  end repeat
end tell
error "no Safari tab with {match} in its URL"''')
    Path(f.name).unlink(missing_ok=True)
    return json.loads(out) if out else None


def cmd_tabs():
    print(osa('''
tell application "Safari"
  set out to ""
  repeat with wi from 1 to count of windows
    repeat with ti from 1 to count of tabs of window wi
      set t to tab ti of window wi
      set out to out & wi & "/" & ti & "  " & (name of t) & "  " & (URL of t) & linefeed
    end repeat
  end repeat
  return out
end tell'''))


def cmd_open(url):
    osa(f'tell application "Safari" to tell front window to make new tab at end of tabs with properties {{URL:{json.dumps(url)}}}')
    print("opened")


def cmd_goto(match, url):
    js(match, f"(location.href = {json.dumps(url)}, 1)")
    time.sleep(4)
    print(json.dumps(js(url.split("?")[0][-30:], f"({PAGE_JS})()") or {}, ensure_ascii=False))


def cmd_fields(match):
    info = js(match, f"({PAGE_JS})()")
    fields = js(match, f"({FIELDS_JS})()")
    url = js(match, "location.href")
    print(json.dumps({"url": url, **info, "fields": fields}, ensure_ascii=False, indent=1))


FILL_JS = r"""
(f => {
  const q = s => document.querySelector(s);
  const fire = (el, ...evs) => evs.forEach(e => el.dispatchEvent(new Event(e, {bubbles: true})));
  const setVal = (el, v) => {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype :
                  el.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
    fire(el, 'input', 'change', 'blur');
  };
  const t = f.type, v = f.value;
  if (t === 'radio' || t === 'buttons' || (t === 'checkbox' && f.optSelector)) {
    const el = q(f.optSelector); if (!el) return 'not found';
    if (el.tagName === 'BUTTON' && el.type === 'submit') el.setAttribute('type', 'button');
    if (!el.checked) el.click(); return 'ok: ' + f.optLabel;
  }
  const el = q(f.selector); if (!el) return 'not found';
  if (t === 'checkbox') { const on = v === true || /^(true|yes|1|on)$/i.test(String(v));
    if (el.checked !== on) el.click(); return 'ok: ' + (on ? 'checked' : 'unchecked'); }
  if (t === 'select') { const o = [...el.options].find(o => o.text.replace(/\s+/g,' ').trim() === f.optLabel);
    if (!o) return 'no option'; setVal(el, o.value); return 'ok: ' + f.optLabel; }
  if (t === 'combobox') { el.focus(); el.click(); setVal(el, String(v)); return 'typed'; }
  el.focus(); setVal(el, String(v)); return 'ok';
})
"""

PICK_JS = r"""
(v => {
  const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const opts = [...document.querySelectorAll('[role="option"]')].filter(o => o.getBoundingClientRect().height > 0);
  const want = norm(v);
  const m = opts.find(o => norm(o.innerText) === want) || opts.find(o => norm(o.innerText).startsWith(want)) ||
            opts.find(o => norm(o.innerText).includes(want));
  if (!m) return 'typed, no matching option (' + opts.length + ' shown): check it';
  m.click(); return 'ok: ' + m.innerText.trim();
})
"""


def cmd_fill(match, path):
    spec = json.loads(Path(path).read_text())
    report = []
    for f in spec.get("fields", []):
        t, v = f.get("type"), f.get("value")
        label = f.get("label", f.get("selector"))
        if v is None or v == "":
            report.append({"label": label, "status": "skipped (no value)"}); continue
        if t == "password":
            report.append({"label": label, "status": "skipped: you use Safari AutoFill"}); continue
        if t == "file":
            report.append({"label": label, "status": f"needs you: drag in {Path(v).expanduser().name}"}); continue
        g = dict(f)
        if t in ("radio", "buttons") or (t == "checkbox" and f.get("options")):
            m = best_match([o["label"] for o in f.get("options", [])], str(v))
            if not m:
                report.append({"label": label, "status": f"no option matches {v!r}"}); continue
            if t == "buttons" and SUBMIT_WORDS.search(m):
                report.append({"label": label, "status": "refused: looks like submit"}); continue
            o = next(o for o in f["options"] if o["label"] == m)
            g.update(optSelector=o["selector"], optLabel=m)
        if t == "select":
            m = best_match(f.get("options", []), str(v))
            if not m:
                report.append({"label": label, "status": f"no option matches {v!r}"}); continue
            g["optLabel"] = m
        status = js(match, f"{FILL_JS}({json.dumps(g)})")
        if t == "combobox":
            time.sleep(1.2)
            status = js(match, f"{PICK_JS}({json.dumps(str(v))})")
        report.append({"label": label, "status": status})
        time.sleep(0.2)
    time.sleep(1)
    missing = []
    for f in js(match, f"({FIELDS_JS})()") or []:
        if not f.get("required") or f["type"] in ("password", "file"):
            continue
        if f["type"] in ("radio", "checkbox", "buttons") and f.get("options"):
            empty = not any(o.get("checked") for o in f["options"])
        elif f["type"] == "checkbox":
            empty = not f.get("checked")
        else:
            empty = "value" not in f
        if empty:
            missing.append(f["label"])
    info = js(match, f"({PAGE_JS})()")
    print(json.dumps({"report": report, "required_still_empty": missing, **info}, ensure_ascii=False, indent=1))


CLICK_JS = r"""
(text => {
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const els = [...document.querySelectorAll('button, [role="button"], a, input[type=submit], input[type=button]')]
    .filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  const want = text.toLowerCase();
  const m = els.find(b => clean(b.innerText || b.value).toLowerCase() === want) ||
            els.find(b => clean(b.innerText || b.value || b.getAttribute('aria-label')).toLowerCase().includes(want));
  if (!m) return {error: 'no button or link ' + text};
  const real = clean(m.innerText || m.value || m.getAttribute('aria-label'));
  return {real, idx: els.indexOf(m)};
})
"""

DO_CLICK_JS = r"""
(i => { const els = [...document.querySelectorAll('button, [role="button"], a, input[type=submit], input[type=button]')]
    .filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  els[i].click(); return 'clicked'; })
"""


def cmd_click(match, text, allow=False):
    if SUBMIT_WORDS.search(text) and not allow:
        sys.exit(f"refused: {text!r} looks like a submit button. You click that yourself.")
    found = js(match, f"{CLICK_JS}({json.dumps(text)})")
    if found.get("error"):
        sys.exit(found["error"])
    real = found["real"]
    if SUBMIT_WORDS.search(real) and not (allow and real.lower().startswith(text.lower())):
        sys.exit(f"refused: the matching button reads {real!r}.")
    js(match, f"{DO_CLICK_JS}({found['idx']})")
    time.sleep(4)
    print(json.dumps({"clicked": real, "tabs_now": None}, ensure_ascii=False))


def cmd_reveal(path):
    subprocess.run(["open", "-R", str(Path(path).expanduser())], check=True)
    print("revealed")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd, rest = a[0], a[1:]
    allow = "--allow" in rest
    rest = [x for x in rest if x != "--allow"]
    if cmd == "tabs":
        cmd_tabs()
    elif cmd == "open" and rest:
        cmd_open(rest[0])
    elif cmd == "goto" and len(rest) == 2:
        cmd_goto(*rest)
    elif cmd == "fields" and rest:
        cmd_fields(rest[0])
    elif cmd == "fill" and len(rest) == 2:
        cmd_fill(*rest)
    elif cmd == "click" and len(rest) == 2:
        cmd_click(*rest, allow=allow)
    elif cmd == "reveal" and rest:
        cmd_reveal(rest[0])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
