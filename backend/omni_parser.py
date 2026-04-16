from __future__ import annotations

import io
import os
import re
import sys
import unicodedata
from typing import Final

import fitz
from docx import Document as DocxDocument
import easyocr

if sys.platform == "win32":
    # Prevent EasyOCR/tqdm from crashing on Windows when printing progress bars
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_PDF: Final[str] = "application/pdf"
_DOCX: Final[str] = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
_IMAGE_TYPES: Final[set[str]] = {"image/png", "image/jpeg"}

_ocr_reader: easyocr.Reader | None = None


def _get_ocr_reader() -> easyocr.Reader:
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(["en"], gpu=True)
    return _ocr_reader


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class DocumentIngester:
    SUPPORTED_MIMES: Final[set[str]] = {_PDF, _DOCX} | _IMAGE_TYPES

    def ingest(self, data: bytes, mime_type: str) -> list[str]:
        if mime_type == _PDF:
            return self._extract_pdf(data)
        elif mime_type == _DOCX:
            return self._extract_docx(data)
        elif mime_type in _IMAGE_TYPES:
            return self._extract_image(data)
        else:
            raise ValueError(
                f"Unsupported MIME type: {mime_type!r}. "
                f"Supported: {sorted(self.SUPPORTED_MIMES)}"
            )

    def _extract_pdf(self, data: bytes) -> list[str]:
        clauses: list[str] = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                # 1. Extract regular text blocks
                blocks = page.get_text("blocks")
                for block in blocks:
                    text = _normalize(block[4])
                    if text:
                        clauses.append(text)
                
                # 2. Extract images on the page and run OCR
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Run OCR on the extracted image bytes
                    reader = _get_ocr_reader()
                    results = reader.readtext(image_bytes, detail=0, paragraph=True)
                    if results:
                        for text_block in results:
                            text = _normalize(text_block)
                            if len(text) > 15:  # Ignore tiny fragments
                                clauses.append(text)
                            
        return clauses

    @staticmethod
    def _extract_docx(data: bytes) -> list[str]:
        doc = DocxDocument(io.BytesIO(data))
        clauses: list[str] = []
        for para in doc.paragraphs:
            text = _normalize(para.text)
            if len(text) > 15:
                clauses.append(text)
        return clauses

    @staticmethod
    def _extract_image(data: bytes) -> list[str]:
        reader = _get_ocr_reader()
        results = reader.readtext(data, detail=0, paragraph=True)
        clauses: list[str] = []
        if results:
            for text_block in results:
                text = _normalize(text_block)
                if len(text) > 15:
                    clauses.append(text)
        return clauses
