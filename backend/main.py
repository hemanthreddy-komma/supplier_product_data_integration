from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import lineage, metrics, products, uploads
from backend.config import settings
from backend.database.connection import init_db

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize database schema and default suppliers
logger.info("Initializing database schema and default suppliers...")
init_db()
logger.info("Database ready.")

app = FastAPI(
    title="Supplier Product Data Integration Hub API",
    description="Enterprise REST API for supplier feed ingestion, standardization, validation, entity resolution, and lineage.",
    version="1.0.0"
)

# CORS Middleware (allowing frontend communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(uploads.router)
app.include_router(products.router)
app.include_router(lineage.router)
app.include_router(metrics.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app_env": settings.APP_ENV,
        "database_backend": str(settings.DATABASE_URL.split("://")[0])
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
