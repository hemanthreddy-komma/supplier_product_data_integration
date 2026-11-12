import logging
from typing import Generator, Any, Dict, List
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import text

from backend.config import settings
from backend.database.models import Base, Supplier

logger = logging.getLogger(__name__)

# Connect with fallback capability
try:
    # Use short connect_timeout (1s) so if Postgres is offline, fallback is instantaneous
    connect_args = {"connect_timeout": 1} if "postgres" in settings.DATABASE_URL else {}
    engine = sa.create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=False
    )
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info(f"Connected successfully to primary database at: {settings.DATABASE_URL.split('@')[-1]}")
except Exception as ex:
    logger.warning(
        f"Could not connect to configured DATABASE_URL ({ex}). "
        f"Falling back to local SQLite database for local/isolated execution."
    )
    fallback_url = "sqlite:///./local_catalog.db"
    engine = sa.create_engine(
        fallback_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables and seed default suppliers if empty."""
    Base.metadata.create_all(bind=engine)
    
    # Seed suppliers if not already seeded
    with SessionLocal() as session:
        for s_id, prio in settings.SUPPLIER_PRIORITIES.items():
            name = settings.SUPPLIER_NAMES.get(s_id, s_id)
            fmt = "csv" if s_id == "supplier_b" else "json"
            existing = session.query(Supplier).filter(Supplier.supplier_id == s_id).first()
            if not existing:
                supplier = Supplier(
                    supplier_id=s_id,
                    name=name,
                    priority=prio,
                    default_format=fmt
                )
                session.add(supplier)
        session.commit()
    logger.info("Database initialized and default suppliers verified.")


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def execute_raw_sql(query_str: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Execute raw SQL queries where appropriate (satisfies requirement 1)."""
    with engine.connect() as conn:
        result = conn.execute(text(query_str), params or {})
        if result.returns_rows:
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
        return []
