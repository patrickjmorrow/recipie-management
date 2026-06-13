import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Recipie Management API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.exception_handler(ResponseValidationError)
async def response_validation_error_handler(request, exc: ResponseValidationError):
    # The response didn't match its declared response_model. Log which field(s)
    # failed — otherwise this surfaces as an opaque 500 with no traceback.
    logger.error(
        "Response validation failed for %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health():
    return {"status": "ok"}
