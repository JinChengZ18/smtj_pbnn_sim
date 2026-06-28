#!/usr/bin/env python3
"""Route the direct-gen analysis figures through a PPT so the panel letters
(a)(b)(c) and the figure number live in the deck, not baked into the plots
(portability; see project figure-norm memory).

Pipeline (python-pptx + LibreOffice, per the user's choice):
  1. eda/gen_supplement_figs.py emits each panel WITHOUT a letter to figures/panels/;
  2. this script builds a clean auto-deck article/ppt/autofigs_<chap>.pptx (rebuilt
     from scratch each run, so it never disturbs the hand-built Chapter0*_local.pptx),
     one slide per figure: panels placed in a row, (a)(b)(c) added above each, and a
     "图 X.Y" number;
  3. LibreOffice renders the deck to PDF and PyMuPDF saves each slide to
     article/figs/Chapter0*_local_NN.png (the numbered article figure).

Run (Windows):  python eda/build_ppt_figs.py
Requires: python-pptx, PyMuPDF (fitz), LibreOffice (soffice).
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image
import fitz

REPO = Path(__file__).resolve().parents[1]
PANELS = REPO / "figures" / "panels"
PPT = REPO / "article" / "ppt"
OUT = REPO / "article" / "figs"
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"
TITLE_RGB = RGBColor(0x3F, 0x2A, 0x7A)

# figures routed through the PPT: which panels, the figure number, the output name
FIGS = {
    "ch04": [
        {"stem": "ch04_16", "panels": ["a", "b", "c"], "num": "图 4.16", "out": "Chapter04_local_16"},
        {"stem": "ch04_18", "panels": ["a", "b", "c"], "num": "图 4.18", "out": "Chapter04_local_18"},
    ],
    "ch05": [
        {"stem": "ch05_09", "panels": ["a", "b", "c"], "num": "图 5.9", "out": "Chapter05_local_09"},
    ],
}
SLIDE_W, SLIDE_H = Inches(13.33), Inches(4.4)   # wide slide sized to a 3-panel row


def build_slide(prs, fig):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    paths = [PANELS / f"{fig['stem']}_{p}.png" for p in fig["panels"]]
    n = len(paths)
    margin, gap, top = 0.25, 0.12, 0.45
    avail = SLIDE_W.inches - 2 * margin - (n - 1) * gap
    pw = avail / n
    for i, path in enumerate(paths):
        im = Image.open(path)
        ph = pw * im.height / im.width
        x = margin + i * (pw + gap)
        slide.shapes.add_picture(str(path), Inches(x), Inches(top), width=Inches(pw))
        tb = slide.shapes.add_textbox(Inches(x), Inches(top - 0.42), Inches(0.7), Inches(0.4))
        r = tb.text_frame.paragraphs[0].add_run()
        r.text = f"({'abcdef'[i]})"
        r.font.bold = True; r.font.size = Pt(15); r.font.color.rgb = TITLE_RGB
    # NOTE: the deck adds only the (a)(b)(c) panel letters; the figure NUMBER
    # (图 X.Y) lives in the markdown caption, so it is intentionally NOT baked in.


def main():
    PPT.mkdir(parents=True, exist_ok=True)
    for chap, figs in FIGS.items():
        prs = Presentation()
        prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H
        for fig in figs:
            build_slide(prs, fig)
        deck = PPT / f"autofigs_{chap}.pptx"
        prs.save(deck)
        # LibreOffice -> PDF
        subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf",
                        "--outdir", str(PPT), str(deck)],
                       check=True, capture_output=True)
        pdf = fitz.open(str(PPT / f"autofigs_{chap}.pdf"))
        for i, fig in enumerate(figs):
            pix = pdf.load_page(i).get_pixmap(dpi=200)
            pix.save(str(OUT / f"{fig['out']}.png"))
            print("wrote", (OUT / f"{fig['out']}.png").relative_to(REPO))
        pdf.close()


if __name__ == "__main__":
    main()
