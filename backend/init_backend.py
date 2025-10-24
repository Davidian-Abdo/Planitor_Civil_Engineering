


import os
import logging
import sys
import time
from typing import Dict, List, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.orm import sessionmaker

# Core backend imports
from backend.database import engine, SessionLocal, check_database_health
from backend.db_models import Base, UserDB, UserBaseTaskDB
from backend.auth import hash_password
from backend.database_operations import create_default_tasks_from_defaults_py, check_and_migrate_database

# ---------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "backend.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Default Data
# ---------------------------------------------------------------------
DEFAULT_USERS = [
    {"username": "admin", "email": "admin@construction.com", "password": "admin123", "full_name": "System Administrator", "role": "admin"},
    {"username": "abdo", "email": "daoudiabdellah1999@gmail.com", "password": "1234", "full_name": "System Administrator", "role": "admin"},
    {"username": "manager", "email": "manager@construction.com", "password": "manager123", "full_name": "Project Manager", "role": "manager"},
    {"username": "worker", "email": "worker@construction.com", "password": "worker123", "full_name": "Construction Worker", "role": "worker"},
    {"username": "viewer", "email": "viewer@construction.com", "password": "viewer123", "full_name": "Project Viewer", "role": "viewer"},
]

ROLE_PERMISSIONS = {
    "admin": ["read", "write", "manage_users", "manage_tasks", "monitor", "export", "system_config"],
    "manager": ["read", "write", "manage_tasks", "monitor", "export"],
    "worker": ["read", "write", "monitor"],
    "viewer": ["read", "monitor"],
}


# ---------------------------------------------------------------------
# Backend Initializer Class
# ---------------------------------------------------------------------
class BackendInitializer:
    def __init__(self):
        self.initialized = False
        self.health_status: Dict[str, Any] = {}
        self.initialization_time = None
        self.version = "2.1.0"

    # -----------------------------------------------------------------
    def initialize(self, force: bool = False) -> bool:
        if self.initialized and not force:
            logger.info("⚙️ Backend already initialized — skipping reinit.")
            return True

        logger.info(f"🚀 Starting backend initialization v{self.version}...")
        start_time = time.time()

        try:
            # Step 1: Check DB
            if not self._check_database_connection():
                return False

            # Step 2: Apply migrations (with timeout)
            if not self._safe_migrate_database(timeout=10):
                return False

            # Step 3: Create tables (idempotent)
            if not self._create_tables():
                return False

            # Step 4: Default users & tasks
            if not self._initialize_defaults():
                return False

            # Step 5: Final health check
            self.health_status = self._health_check()
            self.initialized = True
            self.initialization_time = time.time()

            logger.info(f"✅ Backend initialized successfully in {time.time() - start_time:.2f}s")
            return True

        except Exception as e:
            logger.error(f"❌ Backend initialization failed: {e}", exc_info=True)
            self.initialized = False
            return False

    # -----------------------------------------------------------------
    def _check_database_connection(self) -> bool:
        """Verify DB connectivity with retries"""
        for attempt in range(3):
            try:
                health = check_database_health()
                if health.get("status") == "healthy":
                    logger.info("✅ Database connection verified")
                    return True
            except Exception as e:
                logger.warning(f"DB connection attempt {attempt + 1} failed: {e}")
            time.sleep(2)
        logger.error("❌ Could not connect to database after 3 retries.")
        return False

    # -----------------------------------------------------------------
    def _safe_migrate_database(self, timeout: int = 10) -> bool:
        """Run migrations safely with timeout watchdog"""
        logger.info("🔄 Checking for database migrations...")
        start = time.time()

        try:
            while True:
                if time.time() - start > timeout:
                    logger.warning("⚠️ Migration check timed out (skipping).")
                    return True  # Skip instead of blocking forever

                success = check_and_migrate_database()
                if success:
                    logger.info("✅ Database migrations applied successfully.")
                    return True

                time.sleep(0.5)
        except Exception as e:
            logger.warning(f"⚠️ Migration step failed or unavailable: {e}")
            return True  # Non-blocking fail-safe

    # -----------------------------------------------------------------
    def _create_tables(self) -> bool:
        try:
            Base.metadata.create_all(bind=engine)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            logger.info(f"✅ Tables ready ({len(tables)} total).")
            return True
        except Exception as e:
            logger.error(f"❌ Failed creating tables: {e}")
            return False

    # -----------------------------------------------------------------
    def _initialize_defaults(self) -> bool:
        try:
            with SessionLocal() as session:
                if session.query(UserDB).count() == 0:
                    logger.info("👥 Creating default users...")
                    for u in DEFAULT_USERS:
                        user = UserDB(
                            username=u["username"],
                            email=u["email"],
                            hashed_password=hash_password(u["password"]),
                            full_name=u["full_name"],
                            role=u["role"],
                            is_active=True,
                        )
                        session.add(user)
                    session.commit()
                    logger.info("✅ Default users created.")
                else:
                    logger.info("ℹ️ Default users already exist.")

            # Create default tasks
            with SessionLocal() as session:
                admin = session.query(UserDB).filter_by(username="admin").first()
                if admin:
                    create_default_tasks_from_defaults_py(admin.id)
                    logger.info("✅ Default tasks ensured.")
                else:
                    logger.warning("⚠️ Admin user not found, skipped task creation.")
            return True
        except Exception as e:
            logger.error(f"❌ Default data initialization failed: {e}")
            return False

    # -----------------------------------------------------------------
    def _health_check(self) -> Dict[str, Any]:
        status = {"database": False, "users": 0, "tasks": 0, "healthy": False}
        try:
            with SessionLocal() as session:
                session.execute(text("SELECT 1"))
                status["database"] = True
                status["users"] = session.query(UserDB).count()
                status["tasks"] = session.query(UserBaseTaskDB).count()
                status["healthy"] = status["database"] and status["users"] > 0
        except Exception as e:
            status["error"] = str(e)
        return status


# ---------------------------------------------------------------------
# Global Functions
# ---------------------------------------------------------------------
_backend = BackendInitializer()

def init_backend(force: bool = False) -> bool:
    return _backend.initialize(force)

def check_backend_health() -> Dict[str, Any]:
    return _backend.health_status or {"status": "not_initialized"}

def get_backend_status() -> Dict[str, Any]:
    return {
        "initialized": _backend.initialized,
        "health": _backend.health_status,
        "version": _backend.version,
        "time": _backend.initialization_time,
    }

def get_db_session():
    return SessionLocal()

# ---------------------------------------------------------------------
logger.info(f"Backend initialization module v{_backend.version} ready")
logger.info("Call init_backend() explicitly in app.py to initialize the system")
