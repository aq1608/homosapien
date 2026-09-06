"""Load images and rasterize PDFs into PNG bytes ready for a Bedrock image block.

Keeps every page under Bedrock's image guidance (longest side ~1568px) so the
vision call doesn't choke on oversized scans. PyMuPDF and Pillow are optional
deps (the ``vision`` extra); this module raises a clear message if they're
missing rather than failing obscurely.
"""
from __future__ import annotations

import importlib
import io
from pathlib import Path

_MAX_SIDE = 1568  # Anthropic's recommended max image dimension
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def _require(mod: str):
    """Import a module (or submodule, e.g. 'PIL.Image') with a helpful error."""
    try:
        return importlib.import_module(mod)
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            f"'{mod}' is needed to read scans. Install the vision extra: "
            'pip install -e ".[vision]"'
        ) from exc


def to_png_pages(path: str | Path) -> list[bytes]:
    """Return a list of PNG byte blobs, one per page of the scan.

    Images yield a single page; PDFs yield one PNG per page. Every page is
    re-encoded as PNG and downscaled to fit ``_MAX_SIDE``.
    """
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return [_downscale_png(p) for p in _pdf_to_pngs(path)]
    if path.suffix.lower() in _IMAGE_EXTS:
        return [_downscale_png(path.read_bytes())]
    raise ValueError(f"Unsupported scan type: {path.suffix!r} ({path.name})")


def preview_png(path: str | Path) -> bytes:
    """A single PNG for display/embedding (first page of a PDF)."""
    return to_png_pages(path)[0]


# --------------------------------------------------------------------------- #
def _pdf_to_pngs(path: Path) -> list[bytes]:
    pymupdf = _require("pymupdf")  # modern import name (was 'fitz')
    out: list[bytes] = []
    with pymupdf.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            out.append(pix.tobytes("png"))
    return out


def _downscale_png(data: bytes) -> bytes:
    Image = _require("PIL.Image")  # noqa: N806
    img = Image.open(io.BytesIO(data))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    longest = max(img.size)
    if longest > _MAX_SIDE:
        scale = _MAX_SIDE / longest
        img = img.resize((int(img.width * scale), int(img.height * scale)))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
