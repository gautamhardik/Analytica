from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    origins = settings.cors_origin_list
    if "*" in origins and settings.allow_credentials:
        raise ValueError(
            "CORS: Cannot use allow_origins=['*'] with allow_credentials=True. "
            "Set explicit origins in CORS_ORIGINS env var."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Admin-Token"],
    )
