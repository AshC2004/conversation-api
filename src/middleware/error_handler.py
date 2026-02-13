"""Global exception handler — maps exceptions to structured JSON responses."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_response(status: int, error_type: str, message: str, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "status": "error",
            "error": {
                "type": error_type,
                "message": message,
                "request_id": request_id,
            },
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        messages = "; ".join(
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        return _error_response(422, "validation_error", messages, _request_id(request))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        type_map = {
            401: "authentication_error",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            429: "rate_limit",
        }
        error_type = type_map.get(exc.status_code, "http_error")
        return _error_response(exc.status_code, error_type, exc.detail, _request_id(request))

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _error_response(500, "internal_error", "An unexpected error occurred", _request_id(request))
