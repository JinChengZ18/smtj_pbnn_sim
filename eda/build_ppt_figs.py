#!/usr/bin/env python3
"""Chapter-deck figure pipeline: slide position == chapter figure number.

Every numbered raster asset ``article/figs/Chapter0X_local_NN.png`` is
exported from slide ``NN`` of the hand-maintained deck
``article/ppt/Chapter0X_local.pptx``. The deck is the single place where
figure numbering and panel letters live; generator scripts only produce
raw, unnumbered plots (``figures/``, ``figures/panels/``, ``demo/figures/``).

What this script does per deck (idempotent):

  1. tag untagged hand-built slides with ``FIG:NN`` notes, in deck order
     following the manifest's ``hand_order``;
  2. rebuild the multi-panel AUTOFIG slides (letters added here, not in
     the plots) from ``figures/panels/`` exactly as before;
  3. insert missing figures: ``singles`` as one full-width raw image per
     slide, ``vector`` figures as position-holder slides carrying the
     current SVG-pipeline render (tagged ``FIG:NN:VECTOR``);
  4. refresh embedded images whose registered raw source changed
     (byte comparison);
  5. reorder slides so that slide index + 1 == figure number;
  6. render the deck via LibreOffice and export every non-vector slide,
     auto-cropped to content, to ``article/figs/<deck>_NN.png``.

Vector figures (circuit schematics / architecture SVGs) keep their
cairosvg-rendered assets; their deck slides only hold the position.

Run (Windows):  python eda/build_ppt_figs.py
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.oxml.ns import qn
from PIL import Image
import fitz

REPO = Path(__file__).resolve().parents[1]
PANELS = REPO / "figures" / "panels"
FIGS = REPO / "figures"
DEMO = REPO / "demo" / "figures"
PPT = REPO / "article" / "ppt"
OUT = REPO / "article" / "figs"
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"
MARGIN, GAP, TOP = 0.25, 0.14, 0.55
LETTER_DX, LETTER_DY = 0.05, 0.02
EXPORT_DPI = 419
CROP_PAD = 8  # px kept around the auto-cropped content

MANIFESTS = {
    "Chapter01_local": {
        "n_figs": 3,
        "hand_order": [1, 2, 3],
        "autofigs": {},
        "singles": {},
        "vector": {},
        "refresh": {},
    },
    "Chapter04_local": {
        "n_figs": 21,
        "hand_order": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        "autofigs": {15: ("ch04_15", "abc"), 16: ("ch04_16", "ab"),
                     17: ("ch04_17", "abc")},
        "singles": {19: FIGS / "waveforms_3ops.png",
                    20: FIGS / "mode_pipeline.png",
                    21: FIGS / "dual_model_consistency.png"},
        "vector": {14: OUT / "Chapter04_local_14.png",
                   18: OUT / "Chapter04_local_18.png"},
        "refresh": {13: FIGS / "13a_training_energy_breakdown.png"},
    },
    "Chapter05_local": {
        "n_figs": 10,
        "hand_order": [1, 2, 3, 4, 5, 6, 7],
        "autofigs": {9: ("ch05_09", "abc")},
        "singles": {},
        "vector": {8: OUT / "Chapter05_local_08.png",
                   10: OUT / "Chapter05_local_10.png"},
        "refresh": {6: FIGS / "18_rc_benchmarks.png"},
    },
}


# ---------------------------------------------------------------- helpers
def note_of(slide) -> str:
    return (slide.notes_slide.notes_text_frame.text.strip()
            if slide.has_notes_slide else "")


def set_note(slide, text: str) -> None:
    slide.notes_slide.notes_text_frame.text = text


def fig_of(slide):
    n = note_of(slide)
    if n.startswith("FIG:"):
        return int(n.split(":")[1])
    return None


def walk_pics(shapes):
    for sh in shapes:
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk_pics(sh.shapes)
        elif sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
            yield sh


def blank_slide(prs):
    layout = min(prs.slide_layouts, key=lambda l: len(l.placeholders))
    slide = prs.slides.add_slide(layout)
    for ph in list(slide.placeholders):
        ph._element.getparent().remove(ph._element)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                                prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    bg.line.fill.background(); bg.shadow.inherit = False
    return slide


def add_single(prs, img: Path, tag: str):
    slide = blank_slide(prs)
    im = Image.open(img)
    pw = 10.0 - 2 * MARGIN
    ph = pw * im.height / im.width
    if ph > 6.8:                       # keep tall figures inside the page
        ph = 6.8; pw = ph * im.width / im.height
    x = (10.0 - pw) / 2
    slide.shapes.add_picture(str(img), Inches(x), Inches(TOP), width=Inches(pw))
    set_note(slide, tag)
    return slide


def add_autofig(prs, stem: str, letters: str, tag: str):
    slide = blank_slide(prs)
    paths = [PANELS / f"{stem}_{c}.png" for c in letters]
    n = len(paths)
    avail = 10.0 - 2 * MARGIN - (n - 1) * GAP
    pw = avail / n
    for i, path in enumerate(paths):
        x = MARGIN + i * (pw + GAP)
        slide.shapes.add_picture(str(path), Inches(x), Inches(TOP),
                                 width=Inches(pw))
        if n > 1:
            tb = slide.shapes.add_textbox(Inches(x + LETTER_DX),
                                          Inches(TOP + LETTER_DY),
                                          Inches(0.6), Inches(0.30))
            tf = tb.text_frame; tf.word_wrap = False
            tf.margin_left = tf.margin_right = 0
            tf.margin_top = tf.margin_bottom = 0
            r = tf.paragraphs[0].add_run()
            r.text = f"({letters[i]})"
            r.font.bold = True; r.font.size = Pt(14)
            r.font.color.rgb = RGBColor(0x20, 0x20, 0x20)
    set_note(slide, tag)
    return slide


def refresh_pic(slide, src: Path) -> bool:
    """Swap the slide's single largest picture for ``src`` if bytes differ."""
    pics = list(walk_pics(slide.shapes))
    if not pics:
        return False
    pic = max(pics, key=lambda p: p.width * p.height)
    part = pic.part.related_part(pic._element.blip_rId)
    new = src.read_bytes()
    if part.blob == new:
        return False
    part._blob = new
    im = Image.open(src)
    pic.height = int(pic.width * im.height / im.width)  # keep true aspect
    return True


def reorder(prs, order_rids):
    lst = prs.slides._sldIdLst
    id_by_r = {sid.get(qn("r:id")): sid for sid in list(lst)}
    for sid in list(lst):
        lst.remove(sid)
    for rid in order_rids:
        lst.append(id_by_r[rid])


# ---------------------------------------------------------------- main
def process(name: str, man: dict) -> None:
    deck = PPT / f"{name}.pptx"
    bak = deck.with_suffix(".pptx.bak")
    if not bak.exists():
        shutil.copy2(deck, bak)
    prs = Presentation(str(deck))

    # 1. drop old AUTOFIG slides (they are rebuilt below at the right spot)
    lst = prs.slides._sldIdLst
    for sid, slide in list(zip(list(lst), list(prs.slides))):
        if note_of(slide).startswith("AUTOFIG:"):
            rid = sid.get(qn("r:id"))
            lst.remove(sid); prs.part.drop_rel(rid)

    # 2. tag untagged hand slides in deck order per manifest
    hand_iter = iter(man["hand_order"])
    for slide in prs.slides:
        if fig_of(slide) is None and not note_of(slide).startswith("FIG:"):
            try:
                set_note(slide, f"FIG:{next(hand_iter):02d}")
            except StopIteration:
                raise RuntimeError(f"{name}: more untagged slides than "
                                   f"hand_order entries")

    have = {fig_of(s) for s in prs.slides if fig_of(s) is not None}

    # 3. insert autofigs / singles / vector holders
    for nn, (stem, letters) in man["autofigs"].items():
        add_autofig(prs, stem, letters, f"FIG:{nn:02d}")
    for nn, img in man["singles"].items():
        if nn not in have:
            add_single(prs, img, f"FIG:{nn:02d}")
    for nn, img in man["vector"].items():
        if nn not in have:
            add_single(prs, img, f"FIG:{nn:02d}:VECTOR")

    # 4. refresh registered embeds
    for nn, src in man["refresh"].items():
        for slide in prs.slides:
            if fig_of(slide) == nn and refresh_pic(slide, src):
                print(f"  {name} fig {nn:02d}: embedded image refreshed")

    # 5. order slides by figure number
    pairs = []
    for sid, slide in zip(list(prs.slides._sldIdLst), list(prs.slides)):
        nn = fig_of(slide)
        if nn is None:
            raise RuntimeError(f"{name}: slide without FIG tag")
        pairs.append((nn, sid.get(qn("r:id"))))
    pairs.sort()
    nums = [nn for nn, _ in pairs]
    if nums != list(range(1, man["n_figs"] + 1)):
        raise RuntimeError(f"{name}: figure set {nums} != 1..{man['n_figs']}")
    reorder(prs, [rid for _, rid in pairs])
    prs.save(str(deck))

    # 6. render + export
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf",
                    "--outdir", str(PPT), str(deck)],
                   check=True, capture_output=True)
    pdf = fitz.open(str(PPT / f"{name}.pdf"))
    vector_set = set(man["vector"])
    for nn in range(1, man["n_figs"] + 1):
        if nn in vector_set:
            continue                      # asset stays with the SVG pipeline
        page = pdf.load_page(nn - 1)
        pix = page.get_pixmap(dpi=EXPORT_DPI)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        bbox = Image.eval(im.convert("L"), lambda p: 0 if p > 250 else 255).getbbox()
        if bbox:
            x0, y0, x1, y1 = bbox
            im = im.crop((max(0, x0 - CROP_PAD), max(0, y0 - CROP_PAD),
                          min(im.width, x1 + CROP_PAD),
                          min(im.height, y1 + CROP_PAD)))
        out = OUT / f"{name}_{nn:02d}.png"
        im.save(out)
        print(f"  wrote {out.relative_to(REPO)}  ({im.width}x{im.height})")
    pdf.close()


def main() -> None:
    for name, man in MANIFESTS.items():
        print(f"== {name}")
        process(name, man)


if __name__ == "__main__":
    main()
