# backend/__init__.py
"""
Construction App Backend Package
"""

from backend.database import (
    engine, 
    SessionLocal, 
    get_db_session, 
    init_db, 
    check_database_health
)
from backend.db_models import UserDB, BaseTaskDB, ScheduleDB, MonitoringDB, LoginAttemptDB
from backend.auth import AuthManager, require_role, hash_password, verify_password
from backend.init_backend import init_backend, check_backend_health

# Export logger
from utils.logger import get_logger
logger = get_logger(__name__)

__all__ = [
    # Database
    'engine', 'SessionLocal', 'get_db_session', 'init_db', 'check_database_health',
    # Models
    'UserDB', 'BaseTaskDB', 'ScheduleDB', 'MonitoringDB', 'LoginAttemptDB',
    # Auth
    'AuthManager', 'require_role', 'hash_password', 'verify_password',
    # Initialization
    'init_backend', 'check_backend_health',
    # Logging
    'logger'
]
