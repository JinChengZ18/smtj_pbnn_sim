#!/usr/bin/env python3
"""Route the matplotlib analysis figures through the chapter decks so the panel
letters (a)(b)(c) live in the deck, not baked into the plots (portability).

Per the user's choice, the figures are appended into the HAND-BUILT decks
article/ppt/Chapter0*_local.pptx (one deck per chapter -- no separate autofigs
deck), so all of a chapter's figures live together and order automatically. The
existing hand-built slides are never modified: this script backs each deck up
once (.bak), removes only its own previously-appended slides (tagged in the slide
notes), and re-appends. Circuit schematics are NOT routed here -- they keep their
vector .svg/.pdf pipeline.

Pipeline (python-pptx + LibreOffice + PyMuPDF):
  1. eda/gen_supplement_figs.py emits each panel WITHOUT a letter to figures/panels/;
  2. this script appends one slide per figure (panels in a row at the slide top,
     (a)(b)(c) above each) to the chapter deck;
  3. LibreOffice renders the deck to PDF and PyMuPDF exports each appended slide,
     CLIPPED to the panel row (so the 4:3 deck size is irrelevant), to
     article/figs/Chapter0*_local_NN.png.

Run (Windows):  python eda/gen_supplement_figs.py && python eda/build_ppt_figs.py
"""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from PIL import Image
import fitz

REPO = Path(__file__).resolve().parents[1]
PANELS = REPO / "figures" / "panels"
PPT = REPO / "article" / "ppt"
OUT = REPO / "article" / "figs"
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"
TAG = "AUTOFIG:"                       # marker (in slide notes) for our appended slides
MARGIN, GAP, TOP = 0.25, 0.14, 0.55    # inches, within the slide
LETTER_DX, LETTER_DY = 0.05, 0.02      # panel letter sits just inside each panel's top-left corner

# chapter deck -> list of figures (stem in figures/panels/, panel letters, output name)
DECKS = {
    "Chapter04_local.pptx": [
        {"stem": "ch04_15", "panels": "abc", "out": "Chapter04_local_15"},
        {"stem": "ch04_16", "panels": "ab", "out": "Chapter04_local_16"},
        {"stem": "ch04_17", "panels": "abc", "out": "Chapter04_local_17"},
    ],
    "Chapter05_local.pptx": [
        {"stem": "ch05_09", "panels": "abc", "out": "Chapter05_local_09"},
    ],
}


def is_auto(slide):
    return (slide.has_notes_slide
            and slide.notes_slide.notes_text_frame.text.startswith(TAG))


def remove_autoslides(prs):
    """Drop only our own previously-appended slides, removing BOTH the slide-id entry
    and its relationship so the orphaned slide part is not re-serialized (otherwise the
    package corrupts on repeated runs and LibreOffice can't load it)."""
    lst = prs.slides._sldIdLst
    for sid, slide in list(zip(list(lst), list(prs.slides))):
        if is_auto(slide):
            rId = sid.get(qn("r:id"))
            lst.remove(sid)
            prs.part.drop_rel(rId)


def append_fig(prs, fig):
    layout = min(prs.slide_layouts, key=lambda l: len(l.placeholders))  # blankest available
    slide = prs.slides.add_slide(layout)
    for ph in list(slide.placeholders):           # make it truly blank
        ph._element.getparent().remove(ph._element)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    bg.line.fill.background(); bg.shadow.inherit = False   # white backing, no border/shadow
    letters = fig["panels"]
    paths = [PANELS / f"{fig['stem']}_{c}.png" for c in letters]
    n = len(paths)
    avail = 10.0 - 2 * MARGIN - (n - 1) * GAP     # 10in usable width
    pw = avail / n
    ph_max = 0.0
    for i, path in enumerate(paths):
        im = Image.open(path)
        ph = pw * im.height / im.width
        ph_max = max(ph_max, ph)
        x = MARGIN + i * (pw + GAP)
        slide.shapes.add_picture(str(path), Inches(x), Inches(TOP), width=Inches(pw))
        if n > 1:                                 # single-panel figures get no letter
            tb = slide.shapes.add_textbox(Inches(x + LETTER_DX), Inches(TOP + LETTER_DY),
                                          Inches(0.6), Inches(0.30))
            tf = tb.text_frame; tf.word_wrap = False
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            r = tf.paragraphs[0].add_run()
            r.text = f"({letters[i]})"
            r.font.bold = True; r.font.size = Pt(14); r.font.color.rgb = RGBColor(0x20, 0x20, 0x20)
    slide.notes_slide.notes_text_frame.text = TAG + fig["stem"]
    clip = (MARGIN - 0.12, TOP - 0.06, 10.0 - MARGIN + 0.12, TOP + ph_max + 0.1)
    return clip                                   # inches: (x0, y0, x1, y1)


def main():
    for deck_name, figs in DECKS.items():
        deck = PPT / deck_name
        if not deck.exists():
            print("SKIP (missing):", deck_name); continue
        bak = deck.with_suffix(".pptx.bak")
        if not bak.exists():
            shutil.copy2(deck, bak)               # one-time backup of the hand-built deck
        prs = Presentation(str(deck))
        remove_autoslides(prs)
        base = len(prs.slides._sldIdLst)          # hand-built slide count
        clips = [append_fig(prs, f) for f in figs]
        prs.save(str(deck))
        subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(PPT), str(deck)],
                       check=True, capture_output=True)
        pdf = fitz.open(str(PPT / deck_name.replace(".pptx", ".pdf")))
        for j, fig in enumerate(figs):
            page = pdf.load_page(base + j)
            x0, y0, x1, y1 = (v * 72 for v in clips[j])    # inches -> PDF points
            pix = page.get_pixmap(clip=fitz.Rect(x0, y0, x1, y1), dpi=230)
            pix.save(str(OUT / f"{fig['out']}.png"))
            print("wrote", (OUT / f"{fig['out']}.png").relative_to(REPO))
        pdf.close()


if __name__ == "__main__":
    main()
