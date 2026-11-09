#!/usr/bin/env python3
"""DOCX -> one-page PDF without Microsoft Word (useful if Word isn't installed).
Swaps Calibri for the metric-identical Carlito font (~/Library/Fonts), tightens line
spacing (default 0.97; Pages leads lines a bit taller than Word) and exports with Pages.
Needs the free Carlito font installed, and macOS Pages. Usage:
  python3 pages_pdf.py <in.docx> <out.pdf> [line_spacing]"""
import sys, os, zipfile, subprocess, docx
src0, out = sys.argv[1], sys.argv[2]
LS=float(sys.argv[3]) if len(sys.argv)>3 else 0.97
d0=docx.Document(src0)
for p in d0.paragraphs: p.paragraph_format.line_spacing=LS
src=out[:-4]+"-ls.docx"; d0.save(src)
tmp = out[:-4] + "-carlito.docx"
with zipfile.ZipFile(src) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
    for it in zi.infolist():
        data = zi.read(it.filename)
        if it.filename.endswith(".xml"):
            data = data.replace(b"Calibri Light", b"Carlito").replace(b"Calibri", b"Carlito")
        zo.writestr(it, data)
scr = f'''tell application "Pages"
set d to open POSIX file "{tmp}"
export d to file ((POSIX file "{out}") as text) as PDF
close d saving no
end tell'''
subprocess.run(["osascript", "-e", scr], check=True)
os.remove(tmp); os.remove(src)
from pypdf import PdfReader
print(len(PdfReader(out).pages), "page(s):", out)
