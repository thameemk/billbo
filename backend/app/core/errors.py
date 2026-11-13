from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    """Raised when a record doesn't exist or isn't owned by the caller."""


class ConflictError(Exception):
    """Raised when a change clashes with an existing record."""


class InvalidCursorError(Exception):
    """Raised when a pagination cursor can't be decoded."""


def register_error_handlers(app: FastAPI) -> None:
    def respond(status_code: int):
        async def handler(request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse({"detail": str(exc)}, status_code=status_code)

        return handler

    app.add_exception_handler(InvalidCursorError, respond(400))
    app.add_exception_handler(NotFoundError, respond(404))
    app.add_exception_handler(ConflictError, respond(409))
