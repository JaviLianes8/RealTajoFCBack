"""Application entry point defining the HTTP API."""
from __future__ import annotations

from typing import Callable, Protocol

from fastapi import (
    APIRouter,
    FastAPI,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from app.application.process_classification import (
    ProcessClassificationUseCase,
    RetrieveClassificationUseCase,
)
from app.application.process_document import (
    DocumentParser,
    ProcessDocumentUseCase,
    RetrieveDocumentUseCase,
)
from app.application.process_real_tajo_calendar import (
    ProcessRealTajoCalendarUseCase,
    RealTajoCalendarParser,
    RetrieveRealTajoCalendarUseCase,
)
from app.config.settings import get_settings
from app.domain.repositories.classification_repository import ClassificationRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.real_tajo_calendar_repository import (
    RealTajoCalendarRepository,
)
from app.domain.services.classification_extractor import ClassificationExtractorService
from app.infrastructure.parsers.pdf_document_parser import PdfDocumentParser
from app.infrastructure.repositories.json_classification_repository import (
    JsonClassificationRepository,
)
from app.infrastructure.parsers.real_tajo_calendar_parser import (
    RealTajoCalendarPdfParser,
)
from app.infrastructure.repositories.json_file_repository import JsonFileRepository
from app.infrastructure.repositories.json_real_tajo_calendar_repository import (
    JsonRealTajoCalendarRepository,
)


def create_app(
    document_parser: DocumentParser | None = None,
    classification_repo: ClassificationRepository | None = None,
    schedule_repo: DocumentRepository | None = None,
    real_tajo_parser: RealTajoCalendarParser | None = None,
    real_tajo_repo: RealTajoCalendarRepository | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application instance."""

    settings = get_settings()
    pdf_parser = document_parser or PdfDocumentParser()
    classification_repository = (
        classification_repo
        or JsonClassificationRepository(settings.classification_path)
    )
    schedule_repository = schedule_repo or JsonFileRepository(settings.schedule_path)
    real_tajo_repository = (
        real_tajo_repo
        if real_tajo_repo is not None
        else JsonRealTajoCalendarRepository(settings.real_tajo_calendar_path)
    )

    classification_extractor = ClassificationExtractorService()
    classification_processor = ProcessClassificationUseCase(
        pdf_parser,
        classification_extractor,
        classification_repository,
    )
    classification_retriever = RetrieveClassificationUseCase(classification_repository)

    schedule_processor = ProcessDocumentUseCase(pdf_parser, schedule_repository)
    schedule_retriever = RetrieveDocumentUseCase(schedule_repository)
    real_tajo_calendar_parser = real_tajo_parser or RealTajoCalendarPdfParser(pdf_parser)
    real_tajo_calendar_processor = ProcessRealTajoCalendarUseCase(
        real_tajo_calendar_parser,
        real_tajo_repository,
    )
    real_tajo_calendar_retriever = RetrieveRealTajoCalendarUseCase(real_tajo_repository)

    app = FastAPI(title="Document Processor API", version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = APIRouter(prefix=settings.api_prefix)

    @api_router.get("/status", status_code=status.HTTP_200_OK)
    async def get_status() -> dict:
        """Return the operational status and version of the service."""

        return {"status": "ok", "version": settings.app_version}

    @api_router.put("/classification", status_code=status.HTTP_200_OK)
    async def upload_classification(
        response: Response, file: UploadFile = File(...)
    ) -> dict:
        """Parse and persist the uploaded classification PDF, returning its JSON form."""

        return await _process_upload(
            file,
            response,
            settings.max_upload_size_bytes,
            classification_processor.execute,
            f"{settings.api_prefix}/classification",
        )

    @api_router.get("/classification", status_code=status.HTTP_200_OK)
    async def get_classification() -> dict:
        """Retrieve the stored classification document as JSON."""

        classification_table = classification_retriever.execute()
        if classification_table is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed classification document available.",
            )
        return classification_table.to_dict()

    @api_router.put("/schedule", status_code=status.HTTP_200_OK)
    async def upload_schedule(response: Response, file: UploadFile = File(...)) -> dict:
        """Parse and persist the uploaded schedule PDF, returning its JSON form."""

        return await _process_upload(
            file,
            response,
            settings.max_upload_size_bytes,
            schedule_processor.execute,
            f"{settings.api_prefix}/schedule",
        )

    @api_router.get("/schedule", status_code=status.HTTP_200_OK)
    async def get_schedule() -> dict:
        """Retrieve the stored schedule document as JSON."""

        parsed_document = schedule_retriever.execute()
        if parsed_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed schedule document available.",
            )
        return parsed_document.to_dict()

    @api_router.put("/real-tajo/calendar", status_code=status.HTTP_200_OK)
    async def upload_real_tajo_calendar(
        response: Response, file: UploadFile = File(...)
    ) -> dict:
        """Parse and persist the uploaded Real Tajo calendar PDF, returning its JSON form."""

        return await _process_upload(
            file,
            response,
            settings.max_upload_size_bytes,
            real_tajo_calendar_processor.execute,
            f"{settings.api_prefix}/real-tajo/calendar",
        )

    @api_router.get("/real-tajo/calendar", status_code=status.HTTP_200_OK)
    async def get_real_tajo_calendar() -> dict:
        """Retrieve the stored Real Tajo calendar document as JSON."""

        calendar = real_tajo_calendar_retriever.execute()
        if calendar is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed Real Tajo calendar available.",
            )
        return calendar.to_dict()

    app.include_router(api_router)
    return app


app = create_app()


async def _read_pdf_bytes(uploaded_file: UploadFile, max_size_bytes: int) -> bytes:
    """Ensure the provided file is a PDF and return its bytes respecting size limits."""

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

    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The PDF file exceeds the allowed size.",
        )

    return file_bytes


class _SerializableResource(Protocol):
    """Represent an object that can be expressed as a JSON-serializable dictionary."""

    def to_dict(self) -> dict:
        """Return the dictionary representation of the resource."""


async def _process_upload(
    file: UploadFile,
    response: Response,
    max_size_bytes: int,
    processor: Callable[[bytes], _SerializableResource],
    resource_path: str,
) -> dict:
    """Parse, persist and serialize an uploaded PDF, handling domain errors uniformly."""

    pdf_bytes = await _read_pdf_bytes(file, max_size_bytes)
    resource = _execute_processor(processor, pdf_bytes)
    response.headers["Location"] = resource_path
    return resource.to_dict()


def _execute_processor(
    processor: Callable[[bytes], _SerializableResource], document_bytes: bytes
) -> _SerializableResource:
    """Execute a processor function converting domain ``ValueError`` to HTTP errors."""

    try:
        return processor(document_bytes)
    except ValueError as processing_error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(processing_error),
        ) from processing_error
