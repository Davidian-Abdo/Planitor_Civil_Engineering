
"""
Backend initialization with enhanced error handling, health checks, and performance monitoring
"""

import os
import logging
import sys
import time
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, inspect

# Import backend components
from backend.database import engine, SessionLocal, check_database_health, init_db
from backend.db_models import Base, UserDB, UserBaseTaskDB, LoginAttemptDB
from backend.auth import hash_password
from backend.database_operations import create_default_tasks_from_defaults_py, check_and_migrate_database

# ----------------- Logging Configuration -----------------
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "backend.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ----------------- Configuration -----------------
DEFAULT_USERS = [
    {
        "username": "admin",
        "email": "admin@construction.com",
        "password": "admin123", 
        "full_name": "System Administrator",
        "role": "admin"
    },
    {
        "username": "manager",
        "email": "manager@construction.com",
        "password": "manager123",
        "full_name": "Project Manager", 
        "role": "manager"
    },
    {
        "username": "worker",
        "email": "worker@construction.com",
        "password": "worker123",
        "full_name": "Construction Worker",
        "role": "worker"
    },
    {
        "username": "viewer",
        "email": "viewer@construction.com",
        "password": "viewer123", 
        "full_name": "Project Viewer",
        "role": "viewer"
    }
]

ROLE_PERMISSIONS = {
    "admin": ["read", "write", "manage_users", "manage_tasks", "monitor", "export", "system_config"],
    "manager": ["read", "write", "manage_tasks", "monitor", "export"],
    "worker": ["read", "write", "monitor"],
    "viewer": ["read", "monitor"]
}


class BackendInitializer:
    """
    Enhanced backend initialization with comprehensive error handling and recovery
    """
    
    def __init__(self):
        self.initialized = False
        self.health_status = {}
        self.initialization_time = None
        self.version = "2.0.0"
    
    def initialize(self, force: bool = False) -> bool:
        """
        Initialize backend components with comprehensive error handling
        
        Args:
            force: If True, force reinitialization even if already initialized
            
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self.initialized and not force:
            logger.info("Backend already initialized, skipping...")
            return True
            
        logger.info(f"🚀 Starting backend initialization v{self.version}...")
        start_time = time.time()
        
        try:
            # Step 1: Database connectivity
            if not self._check_database_connection():
                return False
            
            # Step 2: Database migrations
            # if not self._run_database_migrations():
               #  return False
                
            # Step 3: Create tables
            if not self._create_database_tables():
                return False
                
            # Step 4: Initialize default data
            if not self._initialize_default_data():
                return False
                
            # Step 5: Final health check
            self.health_status = self._comprehensive_health_check()
            
            self.initialized = True
            self.initialization_time = time.time()
            
            duration = time.time() - start_time
            logger.info(f"🎉 Backend initialization completed successfully in {duration:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backend initialization failed: {e}", exc_info=True)
            self.initialized = False
            return False
    
    def _check_database_connection(self) -> bool:
        """Verify database connectivity with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                health = check_database_health()
                if health.get("status") == "healthy":
                    logger.info("✅ Database connection verified")
                    return True
                else:
                    logger.warning(f"Database health check attempt {attempt + 1} failed: {health}")
                    
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
        
        logger.error("❌ All database connection attempts failed")
        return False
    
    def _run_database_migrations(self) -> bool:
        """Run database schema migrations with validation"""
        try:
            logger.info("🔄 Checking for database migrations...")
            
            # Run database migrations
            if not check_and_migrate_database():
                logger.error("❌ Database migration failed")
                return False
                
            logger.info("✅ Database migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database migration error: {e}")
            return False
    
    def _create_database_tables(self) -> bool:
        """Create database tables with verification"""
        try:
            logger.info("Creating database tables...")
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            
            # Verify tables were created
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            expected_tables = ['users', 'user_base_tasks', 'schedules', 'monitoring', 'login_attempts']
            
            missing_tables = [table for table in expected_tables if table not in tables]
            if missing_tables:
                logger.error(f"❌ Missing tables after creation: {missing_tables}")
                return False
                
            logger.info(f"✅ Database tables created successfully: {len(tables)} tables")
            return True
            
        except Exception as e:
            logger.error(f"❌ Table creation failed: {e}")
            return False
    
    def _initialize_default_data(self) -> bool:
        """Initialize default users and tasks"""
        try:
            # Create default users
            if not self._create_default_users():
                logger.error("❌ Failed to create default users")
                return False
            
            # Create default tasks
            if not self._create_default_tasks():
                logger.warning("⚠️ Default tasks creation had issues, but continuing...")
            
            logger.info("✅ Default data initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Default data initialization failed: {e}")
            return False
    
    def _create_default_users(self) -> bool:
        """Create default users with improved error handling"""
        try:
            with SessionLocal() as session:
                user_count = session.query(UserDB).count()
                
                if user_count == 0:
                    logger.info("Creating default users...")
                    
                    created_count = 0
                    for user_data in DEFAULT_USERS:
                        try:
                            # Check for existing user
                            existing_user = session.query(UserDB).filter(
                                (UserDB.username == user_data["username"]) | 
                                (UserDB.email == user_data["email"])
                            ).first()
                            
                            if not existing_user:
                                hashed_password = hash_password(user_data["password"])
                                user = UserDB(
                                    username=user_data["username"],
                                    email=user_data["email"],
                                    hashed_password=hashed_password,
                                    full_name=user_data["full_name"],
                                    role=user_data["role"],
                                    is_active=True
                                )
                                session.add(user)
                                created_count += 1
                                logger.info(f"✅ Created user: {user_data['username']} ({user_data['role']})")
                                
                        except Exception as user_error:
                            logger.error(f"❌ Failed to create user {user_data['username']}: {user_error}")
                            continue
                    
                    session.commit()
                    logger.info(f"✅ Created {created_count} default users")
                    
                    if created_count == 0:
                        logger.warning("⚠️ No users were created (possibly all already exist)")
                        
                else:
                    logger.info(f"✅ {user_count} users already exist in database")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ User creation failed: {e}")
            return False
    
    def _create_default_tasks(self) -> bool:
        """Create default construction tasks with fallback mechanism"""
        try:
            with SessionLocal() as session:
                # Get admin user for task assignment
                admin_user = session.query(UserDB).filter_by(username="admin", is_active=True).first()
                if not admin_user:
                    logger.error("❌ Admin user not found for task assignment")
                    return False
                
                # Try to create tasks from defaults.py
                try:
                    created_count = create_default_tasks_from_defaults_py(admin_user.id)
                    
                    if created_count > 0:
                        logger.info(f"✅ Created {created_count} default tasks from defaults.py")
                        return True
                    else:
                        logger.info("ℹ️ No new tasks created (possibly already exist)")
                        return True
                        
                except Exception as defaults_error:
                    logger.warning(f"⚠️ Defaults.py integration failed: {defaults_error}")
                    # Fallback to minimal tasks
                    return self._create_fallback_tasks(session, admin_user.id)
                    
        except Exception as e:
            logger.error(f"❌ Task creation failed: {e}")
            return False
    
    def _create_fallback_tasks(self, session, user_id: int) -> bool:
        """Create minimal fallback tasks"""
        try:
            fallback_tasks = [
                UserBaseTaskDB(
                    user_id=user_id,
                    name="Préparation du Site",
                    discipline="Préliminaires",
                    sub_discipline="InstallationChantier",
                    resource_type="Maçon",
                    task_type="worker",
                    base_duration=5.0,
                    min_crews_needed=2,
                    repeat_on_floor=False,
                    included=True,
                    created_by_user=False
                ),
                UserBaseTaskDB(
                    user_id=user_id,
                    name="Excavation en Masse", 
                    discipline="Terrassement",
                    sub_discipline="Excavation",
                    resource_type="ConducteurEngins",
                    task_type="equipment",
                    base_duration=10.0,
                    min_crews_needed=3,
                    min_equipment_needed={"Pelle Hydraulique": 2, "Chargeuse": 1},
                    repeat_on_floor=False,
                    included=True,
                    created_by_user=False
                ),
                UserBaseTaskDB(
                    user_id=user_id,
                    name="Bétonnage Semelles",
                    discipline="FondationsProfondes",
                    sub_discipline="Pieux", 
                    resource_type="BétonArmé",
                    task_type="hybrid",
                    base_duration=3.0,
                    min_crews_needed=3,
                    min_equipment_needed={"Pompe à Béton": 1, "Bétonnière": 2},
                    repeat_on_floor=False,
                    included=True,
                    created_by_user=False
                )
            ]
            
            for task in fallback_tasks:
                session.add(task)
            
            session.commit()
            logger.info(f"✅ Created {len(fallback_tasks)} fallback tasks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Fallback task creation failed: {e}")
            session.rollback()
            return False
    
    def _comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        health_status = {
            "database_connection": False,
            "tables_accessible": False,
            "default_users_exist": False,
            "default_tasks_exist": False,
            "defaults_integration": False,
            "migrations_applied": False,
            "overall_healthy": False,
            "timestamp": None,
            "version": self.version
        }
        
        try:
            with SessionLocal() as session:
                # Database connection
                session.execute(text("SELECT 1"))
                health_status["database_connection"] = True
                
                # Table accessibility
                user_count = session.query(UserDB).count()
                task_count = session.query(UserBaseTaskDB).count()
                health_status["tables_accessible"] = True
                
                # Default data
                health_status["default_users_exist"] = user_count > 0
                health_status["default_tasks_exist"] = task_count > 0
                
                # Check for sub_discipline column (migration success)
                inspector = inspect(engine)
                columns = [col['name'] for col in inspector.get_columns('user_base_tasks')]
                health_status["migrations_applied"] = 'sub_discipline' in columns
                
                # Defaults integration
                try:
                    from defaults import BASE_TASKS, workers, equipment
                    health_status["defaults_integration"] = True
                    health_status["defaults_details"] = {
                        "base_tasks_count": sum(len(tasks) for tasks in BASE_TASKS.values()),
                        "workers_count": len(workers),
                        "equipment_count": len(equipment)
                    }
                except ImportError as e:
                    health_status["defaults_integration"] = False
                    health_status["defaults_error"] = str(e)
                
                # Overall health
                health_status["overall_healthy"] = all([
                    health_status["database_connection"],
                    health_status["tables_accessible"],
                    health_status["default_users_exist"],
                    health_status["migrations_applied"]
                ])
                
                health_status["details"] = {
                    "user_count": user_count,
                    "task_count": task_count,
                    "environment": os.getenv("ENVIRONMENT", "development"),
                    "initialization_time": self.initialization_time
                }
                health_status["timestamp"] = time.time()
                
        except Exception as e:
            health_status["error"] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health_status
    
    def get_status(self) -> Dict[str, Any]:
        """Get current backend status"""
        return {
            "initialized": self.initialized,
            "health_status": self.health_status,
            "version": self.version,
            "initialization_time": self.initialization_time
        }


# Global initializer instance
_backend_initializer = BackendInitializer()

# ----------------- Public Interface -----------------
def init_backend(force: bool = False) -> bool:
    """
    Initialize backend components - main entry point
    
    Args:
        force: If True, force reinitialization even if already initialized
        
    Returns:
        bool: True if initialization successful, False otherwise
    """
    return _backend_initializer.initialize(force=force)

def check_backend_health() -> Dict[str, Any]:
    """
    Comprehensive backend health check
    
    Returns:
        Dict with health status and details
    """
    if not _backend_initializer.initialized:
        return {
            "status": "not_initialized", 
            "message": "Backend not initialized. Call init_backend() first."
        }
    
    return _backend_initializer.health_status

def get_backend_status() -> Dict[str, Any]:
    """
    Get detailed backend status information
    
    Returns:
        Dict with backend status details
    """
    return _backend_initializer.get_status()

def get_db_session():
    """
    Get database session for dependency injection
    
    Returns:
        SQLAlchemy session object
    """
    return SessionLocal()

def get_default_resources() -> tuple:
    """
    Get default workers and equipment from defaults.py
    
    Returns:
        Tuple of (workers_dict, equipment_dict)
    """
    try:
        from defaults import workers, equipment
        return workers, equipment
    except ImportError as e:
        logger.error(f"Could not import resources from defaults.py: {e}")
        return {}, {}

def get_default_scheduling_config() -> Dict[str, Any]:
    """
    Get default scheduling configuration from defaults.py
    
    Returns:
        Dict with scheduling configuration
    """
    try:
        from defaults import cross_floor_links, acceleration, SHIFT_CONFIG
        return {
            "cross_floor_links": cross_floor_links,
            "acceleration": acceleration, 
            "shift_config": SHIFT_CONFIG
        }
    except ImportError as e:
        logger.warning(f"Could not import scheduling config from defaults.py: {e}")
        return {
            "cross_floor_links": {},
            "acceleration": {},
            "shift_config": {"default": 1.0}
        }

# ----------------- Task Management Utilities -----------------
def get_task_by_id(task_id: int) -> Optional[UserBaseTaskDB]:
    """Get task by ID with error handling"""
    try:
        with SessionLocal() as session:
            return session.query(UserBaseTaskDB).filter(UserBaseTaskDB.id == task_id).first()
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        return None

def get_all_tasks(include_inactive: bool = False) -> List[UserBaseTaskDB]:
    """Get all tasks with optional filtering"""
    try:
        with SessionLocal() as session:
            query = session.query(UserBaseTaskDB)
            if not include_inactive:
                query = query.filter(UserBaseTaskDB.included == True)
            return query.order_by(UserBaseTaskDB.discipline, UserBaseTaskDB.sub_discipline, UserBaseTaskDB.name).all()
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return []

def get_tasks_by_discipline(discipline: str) -> List[UserBaseTaskDB]:
    """Get tasks filtered by discipline"""
    try:
        with SessionLocal() as session:
            return session.query(UserBaseTaskDB).filter(
                UserBaseTaskDB.discipline == discipline,
                UserBaseTaskDB.included == True
            ).order_by(UserBaseTaskDB.sub_discipline, UserBaseTaskDB.name).all()
    except Exception as e:
        logger.error(f"Error getting tasks for discipline {discipline}: {e}")
        return []

# ----------------- Exports -----------------
__all__ = [
    # Core functions
    "init_backend", 
    "check_backend_health",
    "get_backend_status",
    
    # Database access
    "SessionLocal", 
    "get_db_session",
    
    # Defaults integration
    "get_default_resources",
    "get_default_scheduling_config",
    
    # Task management
    "get_task_by_id",
    "get_all_tasks", 
    "get_tasks_by_discipline",
    
    # Configuration
    "ROLE_PERMISSIONS",
    "DEFAULT_USERS",
    
    # Logging
    "logger"
]

# ----------------- Module Initialization -----------------
logger.info(f"Backend initialization module v{_backend_initializer.version} ready")
logger.info("Call init_backend() explicitly in app.py to initialize the system")
