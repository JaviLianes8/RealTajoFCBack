"""Application entry point defining the HTTP API."""
from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile, status

from app.application.process_document import (
    ProcessDocumentUseCase,
    RetrieveDocumentUseCase,
)
from app.config.settings import get_settings
from app.infrastructure.parsers.pdf_document_parser import PdfDocumentParser
from app.infrastructure.repositories.json_file_repository import JsonFileRepository

app = FastAPI(title="Document Processor API", version="0.1.0")

settings = get_settings()
parser = PdfDocumentParser()
classification_repository = JsonFileRepository(settings.classification_path)
classification_processor = ProcessDocumentUseCase(parser, classification_repository)
classification_retriever = RetrieveDocumentUseCase(classification_repository)

schedule_repository = JsonFileRepository(settings.schedule_path)
schedule_processor = ProcessDocumentUseCase(parser, schedule_repository)
schedule_retriever = RetrieveDocumentUseCase(schedule_repository)


async def _read_pdf_bytes(uploaded_file: UploadFile) -> bytes:
    """Ensure the provided file is a PDF and return its bytes."""
    if uploaded_file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file must be a PDF.",
        )
    file_bytes = await uploaded_file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The PDF file is empty.",
        )
    return file_bytes


@app.post("/classification/pdf", status_code=status.HTTP_201_CREATED)
async def upload_classification(file: UploadFile = File(...)) -> dict:
    """Parse and persist the uploaded classification PDF, returning its JSON form."""
    pdf_bytes = await _read_pdf_bytes(file)
    parsed_document = classification_processor.execute(pdf_bytes)
    return parsed_document.to_dict()


@app.get("/classification", status_code=status.HTTP_200_OK)
async def get_classification() -> dict:
    """Retrieve the stored classification document as JSON."""
    parsed_document = classification_retriever.execute()
    if parsed_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No processed classification document available.",
        )
    return parsed_document.to_dict()


@app.post("/schedule/pdf", status_code=status.HTTP_201_CREATED)
async def upload_schedule(file: UploadFile = File(...)) -> dict:
    """Parse and persist the uploaded schedule PDF, returning its JSON form."""
    pdf_bytes = await _read_pdf_bytes(file)
    parsed_document = schedule_processor.execute(pdf_bytes)
    return parsed_document.to_dict()


@app.get("/schedule", status_code=status.HTTP_200_OK)
async def get_schedule() -> dict:
    """Retrieve the stored schedule document as JSON."""
    parsed_document = schedule_retriever.execute()
    if parsed_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No processed schedule document available.",
        )
    return parsed_document.to_dict()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8765, reload=False)
