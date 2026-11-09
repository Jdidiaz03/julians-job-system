#!/usr/bin/env python3
"""Browser helper for the job-apply skill: reads and fills application forms.

It never clicks a submit button. You review each tab and submit yourself.

One visible Chromium window (its own profile in ./browser-profile) stays open
between commands. Every command connects to it, does its work and disconnects,
so the tabs stay there for review.

  python3 apply.py browser                          start the window (or reuse it)
  python3 apply.py fields <tab> [<url>]             open/reread a tab, print its form fields as JSON
  python3 apply.py fill <tab> <fill.json>           fill the tab, then report what's still empty
  python3 apply.py click <tab> "<button text>"      click Apply / Next / Continue (submit is refused)
  python3 apply.py tabs                             list the tabs this helper opened
  python3 apply.py pdf <file.docx>                  convert a DOCX to PDF with Word, print page count

fill.json:
  {"fields": [
     {"selector": "...", "type": "text|textarea|select|radio|checkbox|file|combobox|password",
      "value": "...",            # text, option label, radio label, true/false, file path
      "frame": "<frame url>"},   # only when `fields` reported one
     ...]}
  For a password field use "value": "__KEYCHAIN__" and add "account": "<email>". The script
  makes or reuses a strong password in the macOS Keychain and never prints it.
  On a sign-in page also add "login": true: then it only uses a saved password and never makes one.
"""

import json
import re
import secrets
import socket
import string
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
PROFILE = HERE / "browser-profile"
TABS = HERE / "apply-tabs.json"
PORT = 9333
CDP = f"http://127.0.0.1:{PORT}"

# Button text this helper will never click.
SUBMIT_WORDS = re.compile(
    r"\b(submit|send|enviar|envoyer|finalizar|finish|confirm|confirmar|complete application|"
    r"solicitar ahora|apply now and submit)\b", re.I)

FIELDS_JS = r"""
() => {
  const vis = el => {
    if (el.type === 'file') return true;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 || r.height > 0 || el.type === 'radio' || el.type === 'checkbox';
  };
  const clean = t => (t || '').replace(/\s+/g, ' ').trim().slice(0, 220);
  const INPUTS = 'input:not([type=hidden]), select, textarea';
  const byIds = ids => clean(ids.split(/\s+/).map(i => (document.getElementById(i) || {}).innerText || '').join(' '));
  // Text just before an element (walking up), stopping if we cross into another field.
  const precedingText = el => {
    let n = el;
    for (let d = 0; d < 6 && n && n !== document.body; d++, n = n.parentElement) {
      for (let s = n.previousElementSibling; s; s = s.previousElementSibling) {
        if (s.querySelector && s.querySelector(INPUTS)) return '';
        const tx = clean(s.innerText); if (tx) return tx;
      }
    }
    return '';
  };
  const labelOf = el => {
    if (el.labels && el.labels.length) {
      const t = clean([...el.labels].map(l => l.innerText).join(' ')); if (t) return t;
    }
    const al = el.getAttribute('aria-label'); if (al) return clean(al);
    const lb = el.getAttribute('aria-labelledby'); if (lb && byIds(lb)) return byIds(lb);
    return precedingText(el) || clean(el.placeholder || el.name || el.id);
  };
  const groupLabel = el => {
    const fs = el.closest('fieldset');
    if (fs) { const lg = fs.querySelector('legend'); if (lg && clean(lg.innerText)) return clean(lg.innerText); }
    const rg = el.closest('[role="radiogroup"], [role="group"]');
    if (rg) {
      const lb = rg.getAttribute('aria-labelledby'); if (lb && byIds(lb)) return byIds(lb);
      if (rg.getAttribute('aria-label')) return clean(rg.getAttribute('aria-label'));
    }
    // Smallest container holding the whole group, then its first text block before any input.
    const q = el.name ? `input[name="${CSS.escape(el.name)}"]` : null;
    const total = q ? document.querySelectorAll(q).length : 1;
    let c = el;
    while (c.parentElement && c.parentElement !== document.body && q && c.querySelectorAll(q).length < total)
      c = c.parentElement;
    for (const ch of c.children) {
      if (ch.matches(INPUTS) || ch.querySelector(INPUTS)) break;
      if (clean(ch.innerText)) return clean(ch.innerText);
    }
    return precedingText(c) || clean(el.name);
  };
  // Upload widgets label their button ("Attach"); the real question sits in a nearby label block.
  const fileLabel = el => {
    const own = labelOf(el);
    if (own && !/^(attach|upload|browse|choose|drop)/i.test(own) && own.length > 3) return own;
    let c = el.parentElement;
    for (let i = 0; i < 5 && c; i++, c = c.parentElement) {
      for (const l of c.querySelectorAll('label, legend, [id*="label" i], [class*="label" i]')) {
        const t = clean(l.innerText);
        if (t && !/^(attach|upload|browse|choose|drop|enter manually|dropbox|google drive)/i.test(t)) return t;
      }
    }
    return own || clean(el.id || el.name);
  };
  const sel = el => {
    if (el.id) return `[id="${el.id}"]`;
    if (el.name && document.querySelectorAll(`${el.tagName.toLowerCase()}[name="${CSS.escape(el.name)}"]`).length === 1)
      return `${el.tagName.toLowerCase()}[name="${CSS.escape(el.name)}"]`;
    const path = [];
    for (let n = el; n && n.nodeType === 1 && n !== document.body; n = n.parentElement) {
      let i = 1; for (let s = n.previousElementSibling; s; s = s.previousElementSibling) if (s.tagName === n.tagName) i++;
      path.unshift(`${n.tagName.toLowerCase()}:nth-of-type(${i})`);
    }
    return 'body > ' + path.join(' > ');
  };
  const req = el => el.required || el.getAttribute('aria-required') === 'true' ||
                    /[*✱]\s*$/.test(labelOf(el));
  const out = [], groups = {};
  const els = document.querySelectorAll(
    'input, select, textarea, [role="combobox"], [contenteditable="true"]');
  for (const el of els) {
    const tag = el.tagName.toLowerCase();
    let type = tag === 'input' ? (el.type || 'text').toLowerCase() : tag;
    if (['hidden', 'submit', 'button', 'reset', 'image', 'search'].includes(type)) continue;
    if (!vis(el)) continue;
    // Hidden helper inputs behind custom dropdowns (e.g. react-select's required shim).
    if (type !== 'file' && el.tabIndex === -1 && getComputedStyle(el).opacity === '0') continue;
    if (el.getAttribute('role') === 'combobox' && tag === 'input') type = 'combobox';
    else if (el.getAttribute('role') === 'combobox') type = 'combobox';
    if (type === 'radio' || (type === 'checkbox' && el.name &&
        document.querySelectorAll(`input[type=checkbox][name="${CSS.escape(el.name)}"]`).length > 1)) {
      const key = type + ':' + (el.name || groupLabel(el));
      if (!groups[key]) {
        groups[key] = {type, label: groupLabel(el), required: req(el), options: [],
          selector: el.name ? `input[type=${type}][name="${CSS.escape(el.name)}"]` : null};
        out.push(groups[key]);
      }
      groups[key].options.push({label: labelOf(el), selector: sel(el), checked: el.checked});
      if (el.required) groups[key].required = true;
      continue;
    }
    const f = {type, label: type === 'file' ? fileLabel(el) : labelOf(el), selector: sel(el)};
    if (req(el)) f.required = true;
    if (type === 'select') {
      const opts = [...el.options].map(o => clean(o.text)).filter(t => t);
      f.options = opts.slice(0, 40);
      if (opts.length > 40) f.options_total = opts.length;
      const cur = el.selectedIndex > 0 ? clean(el.options[el.selectedIndex].text) : '';
      if (cur) f.value = cur;
    } else if (type === 'checkbox') {
      f.checked = el.checked;
    } else if (type === 'file') {
      f.accept = el.accept || undefined;
      if (el.files && el.files.length) f.value = el.files[0].name;
    } else if (type === 'combobox') {
      let v = clean(el.value);
      for (let c = el.parentElement, i = 0; !v && c && i < 4; c = c.parentElement, i++) {
        const sv = c.querySelector('[class*="single-value" i], [class*="singlevalue" i], [class*="selected-value" i]');
        if (sv) v = clean(sv.innerText);
      }
      if (v) f.value = v;
    } else if (type !== 'password') {
      const v = el.value || el.innerText || '';
      if (v.trim()) f.value = clean(v);
    }
    if (el.getAttribute('autocomplete') && el.getAttribute('autocomplete') !== 'off')
      f.autocomplete = el.getAttribute('autocomplete');
    out.push(f);
  }
  // Yes/No answers drawn as buttons (Ashby and others): group them by their container.
  const seen = new Set();
  for (const b of document.querySelectorAll('button, [role="button"]')) {
    if (!/^(yes|no|s[ií])$/i.test(clean(b.innerText)) || !vis(b)) continue;
    const box = b.parentElement;
    if (!box || seen.has(box)) continue;
    seen.add(box);
    const bs = [...box.querySelectorAll('button, [role="button"]')].filter(x => clean(x.innerText));
    const label = precedingText(box);
    const entry = box.parentElement;
    const required = /[*✱]\s*$/.test(label) || !!(entry && entry.querySelector('[class*="required" i]'));
    out.push({type: 'buttons', label, required: required || undefined,
      options: bs.map(x => ({label: clean(x.innerText), selector: sel(x),
        checked: x.getAttribute('aria-pressed') === 'true' || /active|selected|checked/i.test(x.className)}))});
  }
  return out;
}
"""

PAGE_JS = r"""
() => {
  const t = s => (s || '').replace(/\s+/g, ' ').trim();
  const btns = [...document.querySelectorAll('button, [role="button"], input[type=submit], a')]
    .filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
    .map(b => t(b.innerText || b.value || b.getAttribute('aria-label')))
    .filter(x => x && x.length < 40 &&
      /apply|next|continue|siguiente|continuar|start|sign in|log in|create account|register|submit|enviar|save|aplicar|inscri|postular/i.test(x));
  const captcha = !!document.querySelector(
    'iframe[src*="recaptcha"], iframe[src*="hcaptcha"], iframe[src*="turnstile"], .g-recaptcha, .h-captcha, .cf-turnstile');
  return {title: document.title, buttons: [...new Set(btns)].slice(0, 15), captcha};
}
"""


# ---------- browser plumbing ----------

def port_open():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def start_browser():
    if port_open():
        return "already running"
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        exe = p.chromium.executable_path
    PROFILE.mkdir(exist_ok=True)
    subprocess.Popen(
        [exe, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
         "--no-first-run", "--no-default-browser-check", "--window-size=1300,950", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(40):
        if port_open():
            return "started"
        time.sleep(0.25)
    sys.exit("browser did not start")


def load_tabs():
    try:
        return json.loads(TABS.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def target_id(page):
    s = page.context.new_cdp_session(page)
    try:
        return s.send("Target.getTargetInfo")["targetInfo"]["targetId"]
    finally:
        s.detach()


def find_tab(ctx, name):
    want = load_tabs().get(name)
    if want:
        for pg in ctx.pages:
            try:
                if target_id(pg) == want:
                    return pg
            except Exception:
                pass
    return None


def ensure_window():
    """Chromium refuses CDP clients once its last window is closed; open a blank tab first."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{CDP}/json/list", timeout=3) as r:
            pages = [t for t in json.load(r) if t.get("type") == "page"]
        if not pages:
            req = urllib.request.Request(f"{CDP}/json/new?about:blank", method="PUT")
            urllib.request.urlopen(req, timeout=5).close()
            time.sleep(0.5)
    except OSError:
        pass


def connect(p):
    if not port_open():
        start_browser()
    ensure_window()
    browser = p.chromium.connect_over_cdp(CDP)
    return browser, browser.contexts[0]


def settle(page):
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    page.wait_for_timeout(800)


def scope(page, frame_url):
    if not frame_url:
        return page
    for fr in page.frames:
        if fr.url.split("?")[0] == frame_url.split("?")[0]:
            return fr
    return page


def read_fields(page):
    result = []
    for fr in page.frames:
        try:
            fs = fr.evaluate(FIELDS_JS)
        except Exception:
            continue
        for f in fs:
            if fr != page.main_frame:
                f["frame"] = fr.url
            result.append(f)
    return result


# ---------- keychain ----------

def keychain_password(domain, account):
    """Return the stored password for domain+account, creating a strong one if missing."""
    r = subprocess.run(["security", "find-internet-password", "-s", domain, "-a", account, "-w"],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip(), False
    alphabet = string.ascii_letters + string.digits + "!#$%&*+-=?@^_"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(22))
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw) and any(c in "!#$%&*+-=?@^_" for c in pw)):
            break
    subprocess.run(["security", "add-internet-password", "-s", domain, "-a", account, "-w", pw,
                    "-r", "htps", "-l", f"{domain} (job-apply)", "-U"],
                   check=True, capture_output=True)
    return pw, True


# ---------- filling ----------

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def best_match(options, value):
    v = norm(value)
    labels = [(o, norm(o)) for o in options]
    for o, n in labels:
        if n == v:
            return o
    for o, n in labels:
        if v and n and (n.startswith(v) or v.startswith(n)):
            return o
    for o, n in labels:
        if v and v in n:
            return o
    return None


def fill_one(page, f):
    t, val, sel = f.get("type"), f.get("value"), f.get("selector")
    where = scope(page, f.get("frame"))
    if val is None or val == "":
        return "skipped (no value)"
    if t == "buttons":
        m = best_match([o["label"] for o in f.get("options", [])], str(val))
        if not m:
            return f"no button matches {val!r}"
        if SUBMIT_WORDS.search(m):
            return "refused: looks like submit"
        o = next(o for o in f["options"] if o["label"] == m)
        btn = where.locator(o["selector"]).first
        # A <button> with no type inside a form is a submit button: neutralise it before clicking.
        btn.evaluate("b => { if (b.tagName === 'BUTTON' && b.type === 'submit') b.setAttribute('type', 'button'); }")
        btn.click(timeout=4000)
        return "ok: " + m
    if t == "radio" or (t == "checkbox" and f.get("options")):
        opts = f.get("options") or []
        wanted = val if isinstance(val, list) else [val]
        done = []
        for w in wanted:
            m = best_match([o["label"] for o in opts], str(w))
            if not m:
                return f"no option matches {w!r}"
            o = next(o for o in opts if o["label"] == m)
            loc = where.locator(o["selector"]).first
            try:
                loc.check(timeout=4000)
            except Exception:
                loc.click(force=True, timeout=4000)
            done.append(m)
        return "ok: " + ", ".join(done)
    loc = where.locator(sel).first
    loc.wait_for(state="attached", timeout=6000)
    if t == "file":
        path = Path(val).expanduser()
        if not path.exists():
            return f"file not found: {path}"
        loc.set_input_files(str(path))
        return "ok: uploaded " + path.name
    if t == "checkbox":
        on = val is True or str(val).lower() in ("true", "yes", "1", "on")
        loc.set_checked(on, force=True)
        return f"ok: {'checked' if on else 'unchecked'}"
    if t == "select":
        opts = loc.evaluate("e => [...e.options].map(o => o.text.replace(/\\s+/g,' ').trim())")
        m = best_match(opts, str(val))
        if not m:
            return f"no option matches {val!r}"
        loc.select_option(label=m)
        return "ok: " + m
    if t == "combobox":
        loc.click(timeout=4000)
        try:
            loc.fill("")
            loc.type(str(val), delay=40)
        except Exception:
            page.keyboard.type(str(val), delay=40)
        page.wait_for_timeout(900)
        opts = where.locator('[role="option"]:visible')
        texts = opts.all_inner_texts()
        m = best_match(texts, str(val))
        if m:
            opts.nth(texts.index(m)).click(timeout=4000)
            return "ok: " + m.strip()
        page.keyboard.press("Enter")
        return "typed, no exact option (pressed Enter): check it"
    if t == "password":
        if val != "__KEYCHAIN__":
            return "refused: passwords only via __KEYCHAIN__"
        account = f.get("account")
        if not account:
            return "missing account (email) for keychain"
        domain = urlparse(page.url).hostname
        if f.get("login"):
            # Sign-in page: only use a saved password, never invent one for an existing account.
            r = subprocess.run(["security", "find-internet-password", "-s", domain, "-a", account, "-w"],
                               capture_output=True, text=True)
            if r.returncode != 0 or not r.stdout.strip():
                return f"no saved password for {domain}: you log in or save it to Keychain"
            loc.fill(r.stdout.strip())
            return "ok: password from Keychain"
        pw, created = keychain_password(domain, account)
        loc.fill(pw)
        return "ok: " + ("new strong password saved to Keychain" if created else "password from Keychain")
    # text-like
    loc.fill(str(val), timeout=6000)
    return "ok"


# ---------- commands ----------

def cmd_browser():
    print(start_browser())


def cmd_fields(name, url=None):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        _, ctx = connect(p)
        page = find_tab(ctx, name)
        if page is None:
            if not url:
                sys.exit(f"no tab called {name!r}; give a url")
            blank = [pg for pg in ctx.pages if pg.url == "about:blank"]
            page = blank[0] if blank else ctx.new_page()
            tabs = load_tabs()
            tabs[name] = target_id(page)
            TABS.write_text(json.dumps(tabs, indent=1))
        if url:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        settle(page)
        info = page.evaluate(PAGE_JS)
        out = {"tab": name, "url": page.url, **info, "fields": read_fields(page)}
        print(json.dumps(out, ensure_ascii=False, indent=1))


def cmd_fill(name, fill_path):
    from playwright.sync_api import sync_playwright
    spec = json.loads(Path(fill_path).read_text())
    with sync_playwright() as p:
        _, ctx = connect(p)
        page = find_tab(ctx, name)
        if page is None:
            sys.exit(f"no tab called {name!r}; run `fields` first")
        page.bring_to_front()
        report = []
        for f in spec.get("fields", []):
            try:
                status = fill_one(page, f)
            except Exception as e:
                status = f"error: {type(e).__name__}: {str(e).splitlines()[0][:120]}"
            report.append({"label": f.get("label", f.get("selector")), "status": status})
            page.wait_for_timeout(150)
        settle(page)
        missing = []
        for f in read_fields(page):
            if not f.get("required"):
                continue
            empty = ("value" not in f and f["type"] not in ("radio", "checkbox", "password", "buttons")) or \
                    (f["type"] in ("radio", "checkbox", "buttons") and f.get("options") and
                     not any(o.get("checked") for o in f["options"])) or \
                    (f["type"] == "checkbox" and not f.get("options") and not f.get("checked"))
            if empty:
                missing.append(f["label"])
        info = page.evaluate(PAGE_JS)
        print(json.dumps({"tab": name, "url": page.url, "report": report,
                          "required_still_empty": missing, "captcha": info["captcha"],
                          "buttons": info["buttons"]}, ensure_ascii=False, indent=1))


def cmd_click(name, text):
    if SUBMIT_WORDS.search(text):
        sys.exit(f"refused: {text!r} looks like a submit button. You click that yourself.")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        _, ctx = connect(p)
        page = find_tab(ctx, name)
        if page is None:
            sys.exit(f"no tab called {name!r}")
        target = None
        for fr in page.frames:
            loc = fr.get_by_role("button", name=text, exact=False)
            if loc.count() == 0:
                loc = fr.get_by_role("link", name=text, exact=False)
            if loc.count():
                target = loc.first
                break
        if target is None:
            sys.exit(f"no button or link {text!r} on the page")
        real = (target.inner_text() or "").strip()
        if SUBMIT_WORDS.search(real):
            sys.exit(f"refused: the matching button reads {real!r}.")
        target.click(timeout=6000)
        settle(page)
        print(json.dumps({"clicked": real, "url": page.url, **page.evaluate(PAGE_JS)},
                         ensure_ascii=False, indent=1))


def cmd_tabs():
    from playwright.sync_api import sync_playwright
    if not port_open():
        print("browser not running")
        return
    with sync_playwright() as p:
        _, ctx = connect(p)
        for name in load_tabs():
            pg = find_tab(ctx, name)
            print(f"{name}: {pg.url if pg else '(closed)'}")


def pdf_pages(path):
    return len(re.findall(rb"/Type\s*/Page(?!s)", Path(path).read_bytes()))


def cmd_pdf(docx):
    """DOCX -> PDF with Microsoft Word (keeps the CV layout exactly)."""
    src = Path(docx).expanduser().resolve()
    out = src.with_suffix(".pdf")
    script = f'''
with timeout of 45 seconds
  tell application "Microsoft Word"
    set d to open file name (POSIX file "{src}" as string)
    save as d file name (POSIX file "{out}" as string) file format format PDF
    close d saving no
  end tell
end timeout'''
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        sys.exit("Word could not convert the file. Most likely Word is showing a one-time "
                 "'Grant File Access' dialog for this folder: click Grant Access in Word, then run again. "
                 "If Word isn't installed, use pages_pdf.py instead.")
    print(json.dumps({"pdf": str(out), "pages": pdf_pages(out)}))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd, rest = a[0], a[1:]
    if cmd == "browser":
        cmd_browser()
    elif cmd == "fields" and rest:
        cmd_fields(rest[0], rest[1] if len(rest) > 1 else None)
    elif cmd == "fill" and len(rest) == 2:
        cmd_fill(*rest)
    elif cmd == "click" and len(rest) == 2:
        cmd_click(*rest)
    elif cmd == "tabs":
        cmd_tabs()
    elif cmd == "pdf" and rest:
        cmd_pdf(rest[0])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
