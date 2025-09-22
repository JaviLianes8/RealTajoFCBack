"""Command-line entry point for running the Document Processor API server."""
from __future__ import annotations

import uvicorn


def main() -> None:
    """Run the API server using Uvicorn."""

    uvicorn.run("app.main:app", host="0.0.0.0", port=8765, reload=False)


if __name__ == "__main__":
    main()
