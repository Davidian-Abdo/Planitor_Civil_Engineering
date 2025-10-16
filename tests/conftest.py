import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db_models import Base, UserDB, BaseTaskDB
from backend.auth import AuthManager

@pytest.fixture(scope="function")
def test_session():
    """Create a fresh database session for each test"""
    # Use SQLite in-memory database for tests
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    yield session
    
    session.close()

@pytest.fixture
def sample_user_data():
    return {
        "username": "testuser",
        "email": "test@construction.com",
        "hashed_password": "hashed_test_password",
        "full_name": "Test User",
        "role": "worker"
    }

@pytest.fixture
def sample_task_data():
    return {
        "name": "Test Construction Task",
        "discipline": "Structure",
        "resource_type": "worker",
        "task_type": "worker",
        "base_duration": 5.0,
        "min_crews_needed": 2,
        "min_equipment_needed": {},
        "predecessors": [],
        "repeat_on_floor": True,
        "included": True
    }

@pytest.fixture
def auth_manager(test_session):
    return AuthManager(test_session)