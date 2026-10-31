import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db import Base
from database.models import Product, Location


@pytest.fixture
def session():
    """Creates a fresh, temporary in-memory database for a single test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestSessionLocal = sessionmaker(bind=engine)
    test_session = TestSessionLocal()

    yield test_session

    test_session.close()