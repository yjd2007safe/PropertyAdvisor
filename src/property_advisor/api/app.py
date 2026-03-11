from __future__ import annotations

"""FastAPI application factory for the PropertyAdvisor MVP."""

from fastapi import FastAPI

from property_advisor.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="PropertyAdvisor API",
        version="0.1.0",
        description="Lightweight MVP API surface for suburb, advisory, and comparables workflows.",
    )
    app.include_router(router)
    return app


app = create_app()
