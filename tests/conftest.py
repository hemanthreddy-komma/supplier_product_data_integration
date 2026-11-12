import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base, Supplier
from backend.config import settings

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    engine = sa.create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    # Seed suppliers
    for s_id, prio in settings.SUPPLIER_PRIORITIES.items():
        session.add(
            Supplier(
                supplier_id=s_id,
                name=settings.SUPPLIER_NAMES.get(s_id, s_id),
                priority=prio,
                default_format="csv" if s_id == "supplier_b" else "json"
            )
        )
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
