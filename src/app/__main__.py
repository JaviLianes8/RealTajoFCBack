"""Command-line entry point for running the Document Processor API server."""
from __future__ import annotations

import uvicorn


def main() -> None:
    """Start a Uvicorn server serving the FastAPI application."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8765, reload=False)


if __name__ == "__main__":
    main()
