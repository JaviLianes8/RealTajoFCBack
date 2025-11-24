"""Application entry point defining the HTTP API."""
from __future__ import annotations

from typing import Callable, Protocol, Any, TypeVar

from fastapi import (
    APIRouter,
    FastAPI,
    Body,
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
    LatestMatchdayNotFoundError,
    LatestMatchdayNumberMismatchError,
    DeleteLatestMatchdayUseCase,
    DeleteMatchdayUseCase,
    MatchdayParser,
    ProcessMatchdayUseCase,
    RetrieveLatestMatchdayUseCase,
    RetrieveMatchdayUseCase,
    StoreMatchdayUseCase,
    UpdateLatestMatchdayUseCase,
)
from app.application.process_document import ProcessDocumentUseCase, RetrieveDocumentUseCase
from app.application.process_real_tajo_calendar import (
    ProcessRealTajoCalendarUseCase,
    RetrieveRealTajoCalendarUseCase,
)
from app.application.process_top_scorers import (
    ProcessTopScorersUseCase,
    RetrieveTopScorersUseCase,
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
from app.infrastructure.parsers.pdf_document_parser import PdfDocumentParser
from app.infrastructure.parsers.matchday_pdf_parser import MatchdayPdfParser
from app.infrastructure.repositories.json_classification_repository import (
    JsonClassificationRepository,
)
from app.infrastructure.repositories.json_file_repository import JsonFileRepository
from app.infrastructure.repositories.json_matchday_repository import (
    JsonMatchdayRepository,
)
from app.infrastructure.repositories.json_real_tajo_calendar_repository import (
    JsonRealTajoCalendarRepository,
)
from app.infrastructure.repositories.json_top_scorers_repository import (
    JsonTopScorersRepository,
)


REAL_TAJO_TEAM_NAME = "REAL TAJO"


def create_app(
    classification_repo: ClassificationRepository | None = None,
    classification_cup_repo: ClassificationRepository | None = None,
    schedule_repo: DocumentRepository | None = None,
    real_tajo_repo: RealTajoCalendarRepository | None = None,
    top_scorers_repo: TopScorersRepository | None = None,
    top_scorers_cup_repo: TopScorersRepository | None = None,
    matchday_parser: MatchdayParser | None = None,
    matchday_repo: MatchdayRepository | None = None,
    matchday_cup_repo: MatchdayRepository | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application instance."""

    settings = get_settings()
    pdf_parser = PdfDocumentParser()
    classification_repository = (
        classification_repo
        or JsonClassificationRepository(settings.classification_path)
    )
    classification_cup_repository = (
        classification_cup_repo
        or JsonClassificationRepository(settings.classification_cup_path)
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
    scorers_cup_repository = (
        top_scorers_cup_repo
        if top_scorers_cup_repo is not None
        else JsonTopScorersRepository(settings.top_scorers_cup_path)
    )
    matchday_repository = (
        matchday_repo
        if matchday_repo is not None
        else JsonMatchdayRepository(settings.matchdays_directory)
    )
    cup_matchday_repository = (
        matchday_cup_repo
        if matchday_cup_repo is not None
        else JsonMatchdayRepository(settings.cup_matchdays_directory)
    )

    classification_processor = ProcessClassificationUseCase(classification_repository)
    classification_retriever = RetrieveClassificationUseCase(classification_repository)

    schedule_processor = ProcessDocumentUseCase(schedule_repository)
    schedule_retriever = RetrieveDocumentUseCase(schedule_repository)
    real_tajo_calendar_processor = ProcessRealTajoCalendarUseCase(real_tajo_repository)
    real_tajo_calendar_retriever = RetrieveRealTajoCalendarUseCase(real_tajo_repository)

    top_scorers_processor = ProcessTopScorersUseCase(scorers_repository)
    top_scorers_retriever = RetrieveTopScorersUseCase(scorers_repository)

    classification_cup_processor = ProcessClassificationUseCase(
        classification_cup_repository
    )
    classification_cup_retriever = RetrieveClassificationUseCase(
        classification_cup_repository
    )

    top_scorers_cup_processor = ProcessTopScorersUseCase(scorers_cup_repository)
    top_scorers_cup_retriever = RetrieveTopScorersUseCase(scorers_cup_repository)

    matchday_parser_service = matchday_parser or MatchdayPdfParser(pdf_parser)
    matchday_processor = ProcessMatchdayUseCase(
        matchday_parser_service,
        matchday_repository,
    )
    matchday_store = StoreMatchdayUseCase(matchday_repository)
    matchday_retriever = RetrieveMatchdayUseCase(matchday_repository)
    latest_matchday_retriever = RetrieveLatestMatchdayUseCase(matchday_repository)
    matchday_deleter = DeleteMatchdayUseCase(matchday_repository)
    latest_matchday_deleter = DeleteLatestMatchdayUseCase(matchday_repository)
    latest_matchday_updater = UpdateLatestMatchdayUseCase(matchday_repository)

    cup_matchday_store = StoreMatchdayUseCase(cup_matchday_repository)
    cup_matchday_retriever = RetrieveMatchdayUseCase(cup_matchday_repository)
    cup_latest_matchday_retriever = RetrieveLatestMatchdayUseCase(
        cup_matchday_repository
    )
    cup_matchday_deleter = DeleteMatchdayUseCase(cup_matchday_repository)
    cup_latest_matchday_deleter = DeleteLatestMatchdayUseCase(
        cup_matchday_repository
    )
    cup_latest_matchday_updater = UpdateLatestMatchdayUseCase(
        cup_matchday_repository
    )

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
        response: Response, payload: dict[str, Any] = Body(...)
    ) -> dict:
        """Persist the provided classification JSON payload."""

        classification = _execute_processor(classification_processor.execute, payload)
        response.headers["Location"] = f"{settings.api_prefix}/classification"
        return classification.to_dict()

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

    @api_router.put("/classification/copa", status_code=status.HTTP_200_OK)
    async def upload_classification_cup(
        response: Response, payload: dict[str, Any] = Body(...)
    ) -> dict:
        """Persist the provided cup classification JSON payload."""

        classification = _execute_processor(
            classification_cup_processor.execute, payload
        )
        response.headers["Location"] = f"{settings.api_prefix}/classification/copa"
        return classification.to_dict()

    @api_router.get("/classification/copa", status_code=status.HTTP_200_OK)
    async def get_classification_cup() -> dict:
        """Retrieve the stored cup classification document as JSON."""

        classification_table = classification_cup_retriever.execute()
        if classification_table is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed cup classification document available.",
            )
        return classification_table.to_dict()

    @api_router.put("/schedule", status_code=status.HTTP_200_OK)
    async def upload_schedule(
        response: Response, payload: dict[str, Any] = Body(...)
    ) -> dict:
        """Persist the provided schedule JSON payload."""

        schedule_document = _execute_processor(schedule_processor.execute, payload)
        response.headers["Location"] = f"{settings.api_prefix}/schedule"
        return schedule_document.to_dict()

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
        response: Response, payload: dict[str, Any] = Body(...)
    ) -> dict:
        """Persist the provided Real Tajo calendar JSON payload."""

        calendar = _execute_processor(real_tajo_calendar_processor.execute, payload)
        response.headers["Location"] = f"{settings.api_prefix}/real-tajo/calendar"
        return calendar.to_dict()

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
    async def upload_top_scorers(
        response: Response, payload: dict[str, Any] = Body(...)
    ) -> dict:
        """Persist the provided top scorers JSON payload."""

        table = _execute_processor(top_scorers_processor.execute, payload)
        response.headers["Location"] = f"{settings.api_prefix}/top-scorers"
        return table.to_dict()

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

    @api_router.put("/top-scorers/copa", status_code=status.HTTP_200_OK)
    async def upload_top_scorers_cup(
        response: Response, payload: dict[str, Any] = Body(...)
    ) -> dict:
        """Persist the provided cup top scorers JSON payload."""

        table = _execute_processor(top_scorers_cup_processor.execute, payload)
        response.headers["Location"] = f"{settings.api_prefix}/top-scorers/copa"
        return table.to_dict()

    @api_router.get("/top-scorers/copa", status_code=status.HTTP_200_OK)
    async def get_top_scorers_cup() -> dict:
        """Retrieve the stored cup top scorers table as JSON."""

        table = top_scorers_cup_retriever.execute()
        if table is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed cup top scorers document available.",
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

    @api_router.post("/matchdays/last", status_code=status.HTTP_201_CREATED)
    async def save_latest_matchday(
        response: Response, payload: dict[str, Any] = Body(...)
    ) -> dict:
        """Persist the provided matchday JSON payload and return its serialization."""

        try:
            matchday = Matchday.from_dict(payload)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

        stored_matchday = matchday_store.execute(matchday)
        response.headers["Location"] = f"{settings.api_prefix}/matchdays/{matchday.number}"
        return _serialize_matchday(stored_matchday)

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

    @api_router.post("/matchdays/last/copa", status_code=status.HTTP_201_CREATED)
    async def save_latest_matchday_cup(
        response: Response, payload: dict[str, Any] = Body(...)
    ) -> dict:
        """Persist the provided cup matchday JSON payload and return its serialization."""

        try:
            matchday = Matchday.from_dict(payload)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

        stored_matchday = cup_matchday_store.execute(matchday)
        response.headers["Location"] = f"{settings.api_prefix}/matchdays/last/copa"
        return _serialize_matchday(stored_matchday)

    @api_router.get("/matchdays/last/copa", status_code=status.HTTP_200_OK)
    async def get_latest_matchday_cup() -> dict:
        """Retrieve the most recently processed cup matchday as JSON."""

        matchday = cup_latest_matchday_retriever.execute()
        if matchday is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed cup matchdays available.",
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

    @api_router.delete("/matchdays/last", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_latest_matchday() -> Response:
        """Delete the most recently processed matchday when available."""

        deleted = latest_matchday_deleter.execute()
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed matchdays available.",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @api_router.delete("/matchdays/last/copa", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_latest_matchday_cup() -> Response:
        """Delete the most recently processed cup matchday when available."""

        deleted = cup_latest_matchday_deleter.execute()
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed cup matchdays available.",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @api_router.put("/matchdays/last/modify", status_code=status.HTTP_200_OK)
    async def modify_latest_matchday(payload: dict) -> dict:
        """Replace the stored latest matchday with the provided payload."""

        try:
            matchday = Matchday.from_dict(payload)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

        try:
            updated_matchday = latest_matchday_updater.execute(matchday)
        except LatestMatchdayNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except LatestMatchdayNumberMismatchError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        return _serialize_matchday(updated_matchday)

    @api_router.put("/matchdays/last/modify/copa", status_code=status.HTTP_200_OK)
    async def modify_latest_matchday_cup(payload: dict) -> dict:
        """Replace the stored latest cup matchday with the provided payload."""

        try:
            matchday = Matchday.from_dict(payload)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

        try:
            updated_matchday = cup_latest_matchday_updater.execute(matchday)
        except LatestMatchdayNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except LatestMatchdayNumberMismatchError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        return _serialize_matchday(updated_matchday)

    @api_router.delete("/matchdays/{number}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_matchday(number: int) -> Response:
        """Delete the stored matchday identified by ``number`` when it exists."""

        deleted = matchday_deleter.execute(number)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed matchday found for the requested number.",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

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


class _SerializableResource(Protocol):
    """Represent an object that can be expressed as a JSON-serializable dictionary."""

    def to_dict(self) -> dict:
        """Return the dictionary representation of the resource."""


_PayloadT = TypeVar("_PayloadT")


def _execute_processor(
    processor: Callable[[_PayloadT], _SerializableResource], payload: _PayloadT
) -> _SerializableResource:
    """Execute a processor function converting domain ``ValueError`` to HTTP errors."""

    try:
        return processor(payload)
    except ValueError as processing_error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(processing_error),
        ) from processing_error
