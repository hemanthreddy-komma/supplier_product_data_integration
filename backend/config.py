import os
from pathlib import Path
from typing import Dict
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    BACKEND_URL: str = "http://localhost:8000"
    
    # Primary Database: PostgreSQL (with fallback capability if Postgres service is offline)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/supplier_product_db"
    
    # Data Directories
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = BASE_DIR / "data" / "raw"
    PROCESSED_DATA_DIR: Path = BASE_DIR / "data" / "processed"
    
    # Supplier Configurations
    SUPPLIER_PRIORITIES: Dict[str, int] = {
        "supplier_a": 1,  # TechCorp Electronics (Highest)
        "supplier_b": 2,  # GlobalSupply Components
        "supplier_c": 3   # ApexGoods Consumer Tech
    }
    
    SUPPLIER_NAMES: Dict[str, str] = {
        "supplier_a": "TechCorp Electronics",
        "supplier_b": "GlobalSupply Components",
        "supplier_c": "ApexGoods Consumer Tech"
    }

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
