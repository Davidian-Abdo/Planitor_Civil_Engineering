"""
Backend package initialization with safe imports and dependency management.
"""

import logging
from typing import List

# Configure package-level logger first
logger = logging.getLogger(__name__)

# Import database components with error handling
try:
    from backend.database import (
        engine, SessionLocal, get_db_session, init_db, check_database_health,
        save_discipline_zone_config, get_discipline_zone_config,
        get_database_metrics, inspect_database
    )
    DATABASE_IMPORTS_SUCCESSFUL = True
except ImportError as e:
    logger.warning(f"Database imports partially failed: {e}")
    # Define fallbacks for critical components
    engine = None
    SessionLocal = None
    DATABASE_IMPORTS_SUCCESSFUL = False
    
    # Define fallback functions
    def get_db_session():
        raise ImportError("Database not available")
    
    def init_db():
        return False
    
    def check_database_health():
        return {"status": "unavailable", "error": "Database imports failed"}

# Import database models with error handling
try:
    from backend.db_models import (
        UserDB, UserBaseTaskDB, ScheduleDB, MonitoringDB, 
        LoginAttemptDB, DisciplineZoneConfigDB
    )
    MODELS_IMPORTS_SUCCESSFUL = True
except ImportError as e:
    logger.warning(f"Models imports failed: {e}")
    MODELS_IMPORTS_SUCCESSFUL = False
    # Define fallback classes to prevent import errors
    class UserDB: pass
    class UserBaseTaskDB: pass
    class ScheduleDB: pass
    class MonitoringDB: pass
    class LoginAttemptDB: pass
    class DisciplineZoneConfigDB: pass

# Import authentication components
try:
    from backend.auth import AuthManager, require_role, hash_password, verify_password
    AUTH_IMPORTS_SUCCESSFUL = True
except ImportError as e:
    logger.warning(f"Auth imports failed: {e}")
    AUTH_IMPORTS_SUCCESSFUL = False
    
    class AuthManager:
        def login(self, username, password):
            return None
        def logout(self):
            pass
        def is_authenticated(self):
            return False
        def get_current_user(self):
            return None
    
    def require_role(*roles):
        def decorator(func):
            return func
        return decorator
    
    def hash_password(password):
        return password
    
    def verify_password(password, hashed):
        return False

# Import initialization components
try:
    from backend.init_backend import (
        init_backend, check_backend_health, get_default_resources, 
        get_default_scheduling_config, get_db_session as get_init_db_session
    )
    INIT_IMPORTS_SUCCESSFUL = True
except ImportError as e:
    logger.warning(f"Init backend imports failed: {e}")
    INIT_IMPORTS_SUCCESSFUL = False
    
    def init_backend():
        return False
    
    def check_backend_health():
        return {"status": "unavailable", "error": "Backend not initialized"}
    
    def get_default_resources():
        return {}, {}
    
    def get_default_scheduling_config():
        return {}
    
    def get_init_db_session():
        return None

# Import database operations with error handling
try:
    from backend.database_operations import (
         save_enhanced_task, duplicate_task, 
        delete_task, get_user_tasks_with_filters, get_user_task_count,
        create_default_tasks_from_defaults_py, migrate_sub_discipline_column
    )
    OPERATIONS_IMPORTS_SUCCESSFUL = True
except ImportError as e:
    logger.warning(f"Database operations imports failed: {e}")
    OPERATIONS_IMPORTS_SUCCESSFUL = False
    
    def copy_default_tasks_to_user(user_id):
        return 0
    
    def save_enhanced_task(*args, **kwargs):
        return False
    
    def duplicate_task(*args, **kwargs):
        return False
    
    def delete_task(*args, **kwargs):
        return False
    
    def get_user_tasks_with_filters(*args, **kwargs):
        return []
    
    def get_user_task_count(*args, **kwargs):
        return 0
    
    def create_default_tasks_from_defaults_py(*args, **kwargs):
        return 0
    
    def migrate_sub_discipline_column():
        return False

# Package metadata
__version__ = "1.0.0"
__author__ = "Construction Scheduling App"
__description__ = "Backend package for advanced construction scheduling application"

# Export all public components
__all__: List[str] = [
    # Database core
    'engine', 
    'SessionLocal', 
    'get_db_session', 
    'init_db', 
    'check_database_health',
    'get_database_metrics',
    'inspect_database',
    
    # Zone configuration
    'save_discipline_zone_config', 
    'get_discipline_zone_config',
    
    # Database models
    'UserDB', 
    'UserBaseTaskDB', 
    'ScheduleDB', 
    'MonitoringDB', 
    'LoginAttemptDB', 
    'DisciplineZoneConfigDB',
    
    # Authentication
    'AuthManager', 
    'require_role', 
    'hash_password', 
    'verify_password',
    
    # Backend initialization
    'init_backend', 
    'check_backend_health',
    'get_default_resources',
    'get_default_scheduling_config',
    'get_init_db_session',
    
    # Database operations
    'copy_default_tasks_to_user', 
    'save_enhanced_task', 
    'duplicate_task', 
    'delete_task', 
    'get_user_tasks_with_filters', 
    'get_user_task_count', 
    'create_default_tasks_from_defaults_py',
    'migrate_sub_discipline_column',
    
    # Logging
    'logger'
]

# Package initialization status
_PACKAGE_INITIALIZED = False

def initialize_backend_package(force: bool = False) -> bool:
    """
    Initialize the backend package and verify all dependencies.
    """
    global _PACKAGE_INITIALIZED
    
    if _PACKAGE_INITIALIZED and not force:
        logger.debug("Backend package already initialized")
        return True
    
    try:
        logger.info("Initializing backend package...")
        
        # Check if critical imports succeeded
        if not DATABASE_IMPORTS_SUCCESSFUL:
            logger.error("Critical database imports failed")
            return False
            
        if not MODELS_IMPORTS_SUCCESSFUL:
            logger.error("Critical models imports failed") 
            return False
            
        logger.info("✅ Backend package initialized successfully")
        _PACKAGE_INITIALIZED = True
        return True
        
    except Exception as e:
        logger.error(f"❌ Backend package initialization failed: {e}")
        _PACKAGE_INITIALIZED = False
        return False

def get_package_info() -> dict:
    """
    Get package information and status.
    """
    return {
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "initialized": _PACKAGE_INITIALIZED,
        "components": {
            "database": DATABASE_IMPORTS_SUCCESSFUL,
            "models": MODELS_IMPORTS_SUCCESSFUL,
            "auth": AUTH_IMPORTS_SUCCESSFUL,
            "operations": OPERATIONS_IMPORTS_SUCCESSFUL,
            "init": INIT_IMPORTS_SUCCESSFUL,
        }
    }

# Auto-initialize on import (optional - can be called explicitly)
try:
    initialize_backend_package()
except Exception as e:
    logger.warning(f"Auto-initialization failed: {e}")

logger.info(f"Backend package {__version__} loaded successfully")
