# backend/__init__.py
"""
Construction App Backend Package
"""

from backend.database import (
    engine, 
    SessionLocal, 
    get_db_session, 
    init_db, 
    save_discipline_zone_config,
    get_discipline_zone_config,
    check_database_health
)
from backend.db_models import UserDB, UserBaseTaskDB, ScheduleDB, MonitoringDB, LoginAttemptDB, DisciplineZoneConfigDB
from backend.auth import AuthManager, require_role, hash_password, verify_password
from backend.database_operations import (
    save_enhanced_task, duplicate_task, delete_task, get_user_tasks_with_filters
)
from backend.init_backend import init_backend, check_backend_health

# Export logger
from utils.logger import get_logger
logger = get_logger(__name__)

__all__ = [
    # Database
    'engine', 'SessionLocal', 'get_db_session', 'init_db', 'check_database_health','save_discipline_zone_config', 'get_discipline_zone_config',
    # Models
    'UserDB', 'UserBaseTaskDB', 'ScheduleDB', 'MonitoringDB', 'LoginAttemptDB', 'DisciplineZoneConfigDB',
    'save_enhanced_task', 'duplicate_task', 'delete_task', 'get_user_tasks_with_filters',
    # Auth
    'AuthManager', 'require_role', 'hash_password', 'verify_password',
    # Initialization
    'init_backend', 'check_backend_health',
    # Logging
    'logger'
]
