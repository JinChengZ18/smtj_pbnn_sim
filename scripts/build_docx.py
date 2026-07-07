"""Manual .md -> .docx regeneration for the article/ chapters.

Replaces the retired local watcher (2026-07-08). Recipe (unchanged from the
watcher era): fold paired inline ``$$...$$`` math into ``$...$`` so pandoc
renders it as inline math, then convert with the article/ resource path so
relative figure links resolve.

Usage (repo root):

    python scripts/build_docx.py chapter04            # one file
    python scripts/build_docx.py                      # every article/*.md
                                                      # that has a sibling .docx
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pypandoc

REPO = Path(__file__).resolve().parents[1]
ARTICLE = REPO / "article"

INLINE_MATH = re.compile(r"\$\$(.+?)\$\$")
IMG_ALT = re.compile(r"!\[[^\]]*\]\(")


def build(stem: str) -> Path:
    src = ARTICLE / f"{stem}.md"
    out = ARTICLE / f"{stem}.docx"
    text = src.read_text(encoding="utf-8")
    # fold paired inline $$...$$ -> $...$ line by line (never across lines,
    # so a genuine display block would be left untouched); strip image alt
    # text (the caption lives in its own bold line, and the watcher-era
    # .docx carried empty alts)
    folded = "\n".join(IMG_ALT.sub("![](", INLINE_MATH.sub(r"$\1$", line))
                       for line in text.split("\n"))
    # implicit_figures is disabled: every figure already carries its own
    # bold caption line in the markdown, so pandoc must not duplicate the
    # alt text as a figure caption.
    pypandoc.convert_text(
        folded, "docx", format="markdown-implicit_figures",
        outputfile=str(out),
        extra_args=[f"--resource-path={ARTICLE}"],
    )
    print(f"wrote {out.relative_to(REPO)}")
    return out


def main() -> None:
    if len(sys.argv) > 1:
        stems = [Path(a).stem for a in sys.argv[1:]]
    else:
        stems = sorted(p.stem for p in ARTICLE.glob("*.md")
                       if (ARTICLE / f"{p.stem}.docx").exists())
    for stem in stems:
        build(stem)


if __name__ == "__main__":
    main()
