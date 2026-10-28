"""One error shape for every failure: {"error": {"code": "<snake_case>", "message": "<plain English>"}}."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("cbyp")

_STATUS_CODES = {
    400: "invalid_request",
    404: "not_found",
    405: "method_not_allowed",
    413: "input_too_large",
    415: "unsupported_media",
    429: "rate_limited",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _describe_validation(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "The request body is not valid."
    first = errors[0]
    where = ".".join(str(p) for p in first.get("loc", ()) if p != "body") or "body"
    return f"{where}: {first.get('msg', 'is not valid')}."


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(400, "invalid_request", _describe_validation(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) and exc.status_code != 404 else "Not found."
        return error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log the type and path only: request bodies can hold personal messages.
        log.error("unhandled %s on %s %s", type(exc).__name__, request.method, request.url.path)
        return error_response(500, "internal_error", "Something went wrong on our side. Please try again.")
