from __future__ import annotations

import io
import re
import unicodedata
from typing import Final

import fitz
from docx import Document as DocxDocument
import easyocr

_PDF: Final[str] = "application/pdf"
_DOCX: Final[str] = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
_IMAGE_TYPES: Final[set[str]] = {"image/png", "image/jpeg"}

_ocr_reader: easyocr.Reader | None = None


def _get_ocr_reader() -> easyocr.Reader:
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
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

    @staticmethod
    def _extract_pdf(data: bytes) -> list[str]:
        clauses: list[str] = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                blocks = page.get_text("blocks")
                for block in blocks:
                    text = _normalize(block[4])
                    if text:
                        clauses.append(text)
        return clauses

    @staticmethod
    def _extract_docx(data: bytes) -> list[str]:
        doc = DocxDocument(io.BytesIO(data))
        clauses: list[str] = []
        for para in doc.paragraphs:
            text = _normalize(para.text)
            if text:
                clauses.append(text)
        return clauses

    @staticmethod
    def _extract_image(data: bytes) -> list[str]:
        reader = _get_ocr_reader()
        results = reader.readtext(data, detail=0)
        clauses: list[str] = []
        for line in results:
            text = _normalize(line)
            if text:
                clauses.append(text)
        return clauses
