"""Text extraction: native PDF text (row-reconstructed) with automatic OCR fallback for scans/images."""
import io
from pathlib import Path

from PIL import Image

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def _ocr(img: Image.Image) -> str:
    import pytesseract
    return pytesseract.image_to_string(img.convert("L"), config="--psm 6")


def _rows_from_words(words) -> str:
    """Rebuild table rows from word boxes so 'Hemoglobin | 11.2 | g/dL | 13-17' stays on one line."""
    words = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    rows, cur, cur_y = [], [], None
    for w in words:
        yc, h = (w[1] + w[3]) / 2, max(w[3] - w[1], 1)
        if cur and abs(yc - cur_y) > 0.6 * h:
            rows.append(cur)
            cur = []
        if not cur:
            cur_y = yc
        cur.append(w)
    if cur:
        rows.append(cur)
    return "\n".join(" ".join(w[4] for w in sorted(r, key=lambda w: w[0])) for r in rows)


def _pdf(data: bytes):
    import pymupdf
    doc = pymupdf.open(stream=data, filetype="pdf")
    parts, ocr_pages = [], 0
    for page in doc:
        text = _rows_from_words(page.get_text("words"))
        if len(text.strip()) < 40:  # scanned page -> OCR
            pix = page.get_pixmap(dpi=200)
            text = _ocr(Image.open(io.BytesIO(pix.tobytes("png"))))
            ocr_pages += 1
        parts.append(text)
    method = "ocr" if ocr_pages == len(parts) else ("mixed" if ocr_pages else "text")
    return "\n".join(parts), {"method": method, "pages": len(parts)}


def extract_text(data: bytes, filename: str):
    ext = Path(filename or "").suffix.lower()
    if ext == ".pdf":
        return _pdf(data)
    if ext in IMG_EXT:
        return _ocr(Image.open(io.BytesIO(data))), {"method": "ocr", "pages": 1}
    if ext == ".txt":
        return data.decode("utf-8", errors="ignore"), {"method": "text", "pages": 1}
    raise ValueError("Unsupported file type. Upload a PDF, image (PNG/JPG) or TXT.")
