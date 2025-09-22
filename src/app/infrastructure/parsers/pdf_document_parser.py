"""Implementation of a document parser that extracts text from PDF files."""
from __future__ import annotations

import io
from typing import List

from PyPDF2 import PdfReader

from app.domain.models.document import DocumentPage, ParsedDocument


class PdfDocumentParser:
    """Parse PDF bytes into a structured ParsedDocument instance."""

    def parse(self, document_bytes: bytes) -> ParsedDocument:
        """Extract the textual content of each page from the provided PDF bytes."""
        reader = PdfReader(io.BytesIO(document_bytes))
        pages: List[DocumentPage] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            pages.append(DocumentPage(number=index, content=lines))
        return ParsedDocument(pages=pages)
