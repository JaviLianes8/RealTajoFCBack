"""Application entry point defining the HTTP API."""
from __future__ import annotations

from typing import Awaitable, Callable, Protocol

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
from app.application.process_matchday import (
    MatchdayParser,
    ProcessMatchdayUseCase,
    RetrieveLatestMatchdayUseCase,
    RetrieveMatchdayUseCase,
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
from app.application.process_top_scorers import (
    ProcessTopScorersUseCase,
    RetrieveTopScorersUseCase,
    TopScorersParser,
)
from app.config.settings import get_settings
from app.domain.models.matchday import Matchday
from app.domain.repositories.classification_repository import ClassificationRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.matchday_repository import MatchdayRepository
from app.domain.repositories.real_tajo_calendar_repository import (
    RealTajoCalendarRepository,
)
from app.domain.repositories.top_scorer_repository import TopScorersRepository
from app.domain.services.classification_extractor import ClassificationExtractorService
from app.infrastructure.parsers.pdf_document_parser import PdfDocumentParser
from app.infrastructure.parsers.matchday_pdf_parser import MatchdayPdfParser
from app.infrastructure.repositories.json_classification_repository import (
    JsonClassificationRepository,
)
from app.infrastructure.parsers.real_tajo_calendar_parser import (
    RealTajoCalendarPdfParser,
)
from app.infrastructure.repositories.json_file_repository import JsonFileRepository
from app.infrastructure.repositories.json_matchday_repository import (
    JsonMatchdayRepository,
)
from app.infrastructure.repositories.json_real_tajo_calendar_repository import (
    JsonRealTajoCalendarRepository,
)
from app.infrastructure.parsers.top_scorers_excel_parser import TopScorersExcelParser
from app.infrastructure.repositories.json_top_scorers_repository import (
    JsonTopScorersRepository,
)


REAL_TAJO_TEAM_NAME = "REAL TAJO"


def create_app(
    document_parser: DocumentParser | None = None,
    classification_repo: ClassificationRepository | None = None,
    schedule_repo: DocumentRepository | None = None,
    real_tajo_parser: RealTajoCalendarParser | None = None,
    real_tajo_repo: RealTajoCalendarRepository | None = None,
    top_scorers_parser: TopScorersParser | None = None,
    top_scorers_repo: TopScorersRepository | None = None,
    matchday_parser: MatchdayParser | None = None,
    matchday_repo: MatchdayRepository | None = None,
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
    scorers_repository = (
        top_scorers_repo
        if top_scorers_repo is not None
        else JsonTopScorersRepository(settings.top_scorers_path)
    )
    matchday_repository = (
        matchday_repo
        if matchday_repo is not None
        else JsonMatchdayRepository(settings.matchdays_directory)
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

    scorers_parser_service = top_scorers_parser or TopScorersExcelParser()
    top_scorers_processor = ProcessTopScorersUseCase(
        scorers_parser_service,
        scorers_repository,
    )
    top_scorers_retriever = RetrieveTopScorersUseCase(scorers_repository)

    matchday_parser_service = matchday_parser or MatchdayPdfParser(pdf_parser)
    matchday_processor = ProcessMatchdayUseCase(
        matchday_parser_service,
        matchday_repository,
    )
    matchday_retriever = RetrieveMatchdayUseCase(matchday_repository)
    latest_matchday_retriever = RetrieveLatestMatchdayUseCase(matchday_repository)

    app = FastAPI(title="Document Processor API", version=settings.app_version)

    @app.get("/", status_code=status.HTTP_200_OK)
    async def get_root() -> dict[str, str]:
        """Return a simple heartbeat response for uptime monitoring."""

        return {"message": "RUNNING REAL TAJO BACK"}

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

    @api_router.put("/top-scorers", status_code=status.HTTP_200_OK)
    async def upload_top_scorers(response: Response, file: UploadFile = File(...)) -> dict:
        """Parse and persist the uploaded top scorers Excel file, returning its JSON form."""

        return await _process_upload(
            file,
            response,
            settings.max_upload_size_bytes,
            top_scorers_processor.execute,
            f"{settings.api_prefix}/top-scorers",
            _read_excel_bytes,
        )

    @api_router.get("/top-scorers", status_code=status.HTTP_200_OK)
    async def get_top_scorers() -> dict:
        """Retrieve the stored top scorers table as JSON."""

        table = top_scorers_retriever.execute()
        if table is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed top scorers document available.",
            )
        return table.to_dict()

    def _serialize_matchday(matchday: Matchday) -> dict:
        """Return the Real Tajo-focused serialization for ``matchday``."""

        return matchday.to_dict(team_name=REAL_TAJO_TEAM_NAME)

    @api_router.put("/matchdays", status_code=status.HTTP_200_OK)
    async def upload_matchday(response: Response, file: UploadFile = File(...)) -> dict:
        """Parse and persist the uploaded matchday PDF, returning its JSON form."""

        pdf_bytes = await _read_pdf_bytes(file, settings.max_upload_size_bytes)
        matchday = _execute_processor(matchday_processor.execute, pdf_bytes)
        response.headers["Location"] = f"{settings.api_prefix}/matchdays/{matchday.number}"
        return _serialize_matchday(matchday)

    @api_router.get("/matchdays/last", status_code=status.HTTP_200_OK)
    async def get_latest_matchday() -> dict:
        """Retrieve the most recently processed matchday as JSON."""

        matchday = latest_matchday_retriever.execute()
        if matchday is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed matchdays available.",
            )
        return _serialize_matchday(matchday)

    @api_router.get("/matchdays/{number}", status_code=status.HTTP_200_OK)
    async def get_matchday(number: int) -> dict:
        """Retrieve the stored matchday identified by ``number`` as JSON."""

        matchday = matchday_retriever.execute(number)
        if matchday is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed matchday found for the requested number.",
            )
        return _serialize_matchday(matchday)

    app.include_router(api_router)
    return app


app = create_app()


async def _read_binary_file(
    uploaded_file: UploadFile,
    max_size_bytes: int,
    allowed_content_types: set[str],
    type_error_message: str,
    empty_error_message: str,
    size_error_message: str,
) -> bytes:
    """Read ``uploaded_file`` ensuring type, non-emptiness and size constraints."""

    if uploaded_file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=type_error_message,
        )

    file_bytes = await uploaded_file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=empty_error_message,
        )

    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=size_error_message,
        )

    return file_bytes


async def _read_pdf_bytes(uploaded_file: UploadFile, max_size_bytes: int) -> bytes:
    """Ensure the provided file is a PDF and return its bytes respecting size limits."""

    return await _read_binary_file(
        uploaded_file,
        max_size_bytes,
        {"application/pdf", "application/x-pdf"},
        "The uploaded file must be a PDF.",
        "The PDF file is empty.",
        "The PDF file exceeds the allowed size.",
    )


async def _read_excel_bytes(uploaded_file: UploadFile, max_size_bytes: int) -> bytes:
    """Ensure the provided file is an Excel workbook and return its bytes."""

    return await _read_binary_file(
        uploaded_file,
        max_size_bytes,
        {
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        "The uploaded file must be an Excel workbook.",
        "The Excel file is empty.",
        "The Excel file exceeds the allowed size.",
    )


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
    reader: Callable[[UploadFile, int], Awaitable[bytes]] = _read_pdf_bytes,
) -> dict:
    """Parse, persist and serialize an uploaded document with unified error handling."""

    document_bytes = await reader(file, max_size_bytes)
    resource = _execute_processor(processor, document_bytes)
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
