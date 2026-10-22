"""Dev helper: rasterize some PDF pages to PNG for visual checks. Needs PyMuPDF (not a project dependency):
    python -m venv /tmp/inspect && /tmp/inspect/bin/pip install pymupdf
    /tmp/inspect/bin/python backend/scripts/pdf_pages.py <in.pdf> <out-prefix> [pages=1,2,3]
"""
import sys

import pymupdf

src, prefix = sys.argv[1], sys.argv[2]
doc = pymupdf.open(src)
pages = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [1, 2, 3]
print("pages:", len(doc))
for n in pages:
    if 1 <= n <= len(doc):
        doc[n - 1].get_pixmap(dpi=80).save(f"{prefix}-{n}.png")
