from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import datasets, decisions, forecasts, inventory, products
from app.core.config import settings
from app.core.db import Base, engine
from app.models import models  # noqa: F401 -- ensures models are registered on Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Decision Intelligence Platform — Phase 1: Ingestion & Forecasting",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router, prefix=settings.api_v1_prefix)
app.include_router(products.router, prefix=settings.api_v1_prefix)
app.include_router(forecasts.router, prefix=settings.api_v1_prefix)
app.include_router(inventory.router, prefix=settings.api_v1_prefix)
app.include_router(decisions.router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.app_name}
