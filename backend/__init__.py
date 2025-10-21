
from backend.database import (
    engine, SessionLocal, get_db_session, init_db, check_database_health,
    save_discipline_zone_config, get_discipline_zone_config
)
from backend.db_models import UserDB, UserBaseTaskDB, ScheduleDB, MonitoringDB, LoginAttemptDB, DisciplineZoneConfigDB
from backend.auth import AuthManager, require_role, hash_password, verify_password
from backend.init_backend import init_backend, check_backend_health
from backend.database_operations import (
    copy_default_tasks_to_user, save_enhanced_task, duplicate_task, 
    delete_task, get_user_tasks_with_filters, get_user_task_count,
    create_default_tasks_from_defaults_py  # ✅ ADD THIS
)

# Export logger
from utils.logger import get_logger
logger = get_logger(__name__)

__all__ = [
    # Database
    'engine', 'SessionLocal', 'get_db_session', 'init_db', 'check_database_health',
    'save_discipline_zone_config', 'get_discipline_zone_config',
    # Models
    'UserDB', 'UserBaseTaskDB', 'ScheduleDB', 'MonitoringDB', 'LoginAttemptDB', 'DisciplineZoneConfigDB',
    # Auth
    'AuthManager', 'require_role', 'hash_password', 'verify_password',
    # Initialization
    'init_backend', 'check_backend_health',
    # ✅ NEW: Database operations
    'copy_default_tasks_to_user', 'save_enhanced_task', 'duplicate_task', 
    'delete_task', 'get_user_tasks_with_filters', 'get_user_task_count', 'create_default_tasks_from_defaults_py' ,
    # Logging
    'logger'
]
