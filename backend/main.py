"""Harmonee FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.routers import birds, habitat, health, property as property_router


def create_app() -> FastAPI:
    """Create and configure the Harmonee FastAPI application."""
    application = FastAPI(title="Harmonee API", version="0.1.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(property_router.router)
    application.include_router(habitat.router)
    application.include_router(birds.router)

    return application


app = create_app()
