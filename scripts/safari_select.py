#!/usr/bin/env python3
"""Pick options in react-select dropdowns (Greenhouse etc.) in Safari, which safari.py fill can't open.
Calls the React Select component's own selectOption(). Usage: python3 safari_select.py <tab-url-match> <spec.json>
spec.json = [{"id": "<input id from fields>", "value": "<option label>"}, ...]"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import safari
match, spec = sys.argv[1], json.load(open(sys.argv[2]))
PICK = r"""((id,want) => {
  const i=document.getElementById(id); if(!i) return 'no input';
  const k=Object.keys(i).find(k=>k.startsWith('__reactFiber')); let f=i[k];
  while(f && !(f.stateNode && typeof f.stateNode.selectOption==='function')) f=f.return;
  if(!f) return 'no select component';
  const sel=f.stateNode; const n=s=>String(s).replace(/\s+/g,' ').trim().toLowerCase();
  const flat=[]; (sel.props.options||[]).forEach(o=>o.options?flat.push(...o.options):flat.push(o));
  const lab=o=>sel.props.getOptionLabel?sel.props.getOptionLabel(o):o.label;
  const o=flat.find(o=>n(lab(o))===n(want))||flat.find(o=>n(lab(o)).startsWith(n(want)));
  if(!o) return 'no option: '+flat.slice(0,8).map(lab).join(' / ');
  sel.selectOption(o); sel.blurInput && sel.blurInput(); return 'picked '+lab(o); })"""
for f in spec:
    print(f["id"], "|", safari.js(match, f"{PICK}({json.dumps(f['id'])},{json.dumps(f['value'])})"))
    time.sleep(0.4)
