"""Implementation of a document parser that extracts text from PDF files."""
from __future__ import annotations

import io
from typing import List

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from app.domain.models.document import DocumentPage, ParsedDocument


class PdfDocumentParser:
    """Parse PDF bytes into a structured ParsedDocument instance."""

    def parse(self, document_bytes: bytes) -> ParsedDocument:
        """Extract the textual content of each page from the provided PDF bytes."""

        try:
            reader = PdfReader(io.BytesIO(document_bytes))
        except PdfReadError as error:
            raise ValueError("The provided PDF file could not be read.") from error
        except Exception as error:  # pragma: no cover - defensive fallback
            raise ValueError("Unexpected error while reading the PDF file.") from error

        pages: List[DocumentPage] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except PdfReadError as error:
                raise ValueError("The PDF file contains unreadable pages.") from error
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            pages.append(DocumentPage(number=index, content=lines))
        return ParsedDocument(pages=pages)
