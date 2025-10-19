"""
Advanced backend initialization for Construction Management App
- Initializes database engine and session  
- Sets up authentication manager with roles
- Provides shared utilities for the backend
- Direct integration with defaults.py for task definitions
"""

import os
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Import carefully to avoid circular dependencies
from backend.database import engine, SessionLocal
from backend.db_models import Base, UserDB, UserBaseTaskDB, LoginAttemptDB
from backend.auth import hash_password  # Use corrected hash_password function

# ----------------- Logging Setup -----------------
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "backend.log")),
        logging.StreamHandler()  # Also output to console
    ]
)

logger = logging.getLogger(__name__)
logger.info("Backend initialization module loaded.")

# ----------------- Database Setup -----------------
# Session factory is already imported from database.py

# ----------------- Role Permissions -----------------
ROLE_PERMISSIONS = {
    "admin": ["read", "write", "manage_users", "manage_tasks", "monitor", "export"],
    "manager": ["read", "write", "manage_tasks", "monitor", "export"],
    "worker": ["read", "write", "monitor"],
    "viewer": ["read", "monitor"]
}

# ----------------- Core Initialization Function -----------------
def init_backend():
    """
    Initialize backend components - call this explicitly in app.py
    This function is safe to call multiple times (idempotent)
    """
    logger.info("🚀 Starting backend initialization...")
    
    try:
        # Create database tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
        
        # Test database connection
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        logger.info("✅ Database connection test passed")
        
        # Initialize default data
        _create_default_users()
        _create_default_tasks_from_defaults()
        
        logger.info("🎉 Backend initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Backend initialization failed: {e}")
        raise

def _create_default_users():
    """Create default users if none exist"""
    try:
        with SessionLocal() as session:
            # Check if any users exist
            user_count = session.query(UserDB).count()
            
            if user_count == 0:
                logger.info("Creating default users...")
                
                default_users = [
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
                
                for user_data in default_users:
                    # Check if user already exists
                    existing_user = session.query(UserDB).filter(
                        (UserDB.username == user_data["username"]) | 
                        (UserDB.email == user_data["email"])
                    ).first()
                    
                    if not existing_user:
                        # Use corrected hash_password function
                        hashed_password = hash_password(user_data["password"])
                        user = UserDB(
                            username=user_data["username"],
                            email=user_data["email"],
                            hashed_password=hashed_password,  # Correct field name
                            full_name=user_data["full_name"],
                            role=user_data["role"],
                            is_active=True
                        )
                        session.add(user)
                        logger.info(f"✅ Created user: {user_data['username']} ({user_data['role']})")
                
                session.commit()
                logger.info("✅ Default users created successfully")
            else:
                logger.info(f"✅ {user_count} users already exist in database")
                
    except Exception as e:
        logger.warning(f"Could not create default users: {e}")

def _create_default_tasks_from_defaults():
    """Create default construction tasks directly from defaults.py BASE_TASKS"""
    try:
        # Import defaults.py directly
        from defaults import BASE_TASKS
        
        with SessionLocal() as session:
            task_count = session.query(UserBaseTaskDB).count()  # ✅ FIXED: Changed from BaseTaskDB to UserBaseTaskDB
            
            if task_count == 0:
                logger.info("Creating default construction tasks from defaults.py BASE_TASKS...")
                
                created_tasks = 0
                for discipline, tasks in BASE_TASKS.items():
                    logger.info(f"Processing {discipline} discipline with {len(tasks)} tasks")
                    
                    for base_task in tasks:
                        # Skip if task is not included
                        if not getattr(base_task, 'included', True):
                            logger.debug(f"Skipping excluded task: {base_task.name}")
                            continue
                        
                        # Convert BaseTask from defaults.py to UserBaseTaskDB
                        db_task = UserBaseTaskDB(  # ✅ FIXED: Changed from BaseTaskDB to UserBaseTaskDB
                            name=base_task.name,
                            discipline=discipline,
                            resource_type=base_task.resource_type,
                            task_type=getattr(base_task, 'task_type', 'worker'),
                            base_duration=getattr(base_task, 'base_duration', 1.0),
                            min_crews_needed=getattr(base_task, 'min_crews_needed', 1),
                            min_equipment_needed=getattr(base_task, 'min_equipment_needed', {}),
                            predecessors=getattr(base_task, 'predecessors', []),
                            repeat_on_floor=getattr(base_task, 'repeat_on_floor', True),
                            included=getattr(base_task, 'included', True),
                            delay=getattr(base_task, 'delay', 0),
                            created_by_user=False
                        )
                        
                        session.add(db_task)
                        created_tasks += 1
                        logger.debug(f"Added task: {base_task.name}")
                
                session.commit()
                logger.info(f"✅ Created {created_tasks} default tasks from defaults.py")
                
                # Verify task creation
                final_count = session.query(UserBaseTaskDB).count()  # ✅ FIXED: Changed from BaseTaskDB to UserBaseTaskDB
                logger.info(f"✅ Database now contains {final_count} total tasks")
            else:
                logger.info(f"✅ {task_count} tasks already exist in database")
                
    except Exception as e:
        logger.warning(f"Could not create default tasks: {e}")


def _create_fallback_tasks():
    """Create minimal fallback tasks if defaults.py integration fails"""
    logger.warning("Creating fallback construction tasks...")
    
    try:
        with SessionLocal() as session:
            fallback_tasks = [
                UserBaseTaskDB(
                    name="Site Preparation",
                    discipline="Préliminaire",
                    resource_type="BétonArmée",
                    task_type="worker",
                    base_duration=5.0,
                    min_crews_needed=2,
                    repeat_on_floor=False,
                    included=True,
                    created_by_user=False
                ),
                UserBaseTaskDB(
                    name="Excavation", 
                    discipline="Terrassement",
                    resource_type="BétonArmée",
                    task_type="equipment",
                    base_duration=3.0,
                    min_crews_needed=1,
                    min_equipment_needed={"Chargeuse": 1},
                    repeat_on_floor=False,
                    included=True,
                    created_by_user=False
                ),
                UserBaseTaskDB(
                    name="Concrete Foundation",
                    discipline="Fondations",
                    resource_type="BétonArmée",
                    task_type="hybrid",
                    base_duration=7.0,
                    min_crews_needed=3,
                    min_equipment_needed={"Pump": 1},
                    repeat_on_floor=False, 
                    included=True,
                    created_by_user=False
                )
            ]
            
            for task in fallback_tasks:
                session.add(task)
            
            session.commit()
            logger.info(f"✅ Created {len(fallback_tasks)} fallback tasks")
            
    except Exception as e:
        logger.error(f"❌ Failed to create fallback tasks: {e}")

def get_default_resources():
    """
    Get default workers and equipment from defaults.py
    Useful for scheduling engine initialization
    """
    try:
        from defaults import workers, equipment
        return workers, equipment
    except ImportError as e:
        logger.error(f"Could not import resources from defaults.py: {e}")
        return {}, {}

def get_default_scheduling_config():
    """
    Get default scheduling configuration from defaults.py
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

def check_backend_health():
    """
    Comprehensive backend health check
    Returns dict with health status and details
    """
    health_status = {
        "database_connection": False,
        "tables_accessible": False,
        "default_users_exist": False,
        "default_tasks_exist": False,
        "defaults_integration": False,
        "overall_healthy": False
    }
    
    try:
        with SessionLocal() as session:
            # Test database connection
            session.execute(text("SELECT 1"))
            health_status["database_connection"] = True
            
            # Check if tables are accessible
            user_count = session.query(UserDB).count()
            task_count = session.query(UserBaseTaskDB).count()
            health_status["tables_accessible"] = True
            
            # Check if default data exists
            health_status["default_users_exist"] = user_count > 0
            health_status["default_tasks_exist"] = task_count > 0
            
            # Check defaults.py integration
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
                health_status["default_tasks_exist"]
            ])
            
            health_status["details"] = {
                "user_count": user_count,
                "task_count": task_count,
                "database_url": str(engine.url).split('@')[-1]  # Mask credentials
            }
            
    except Exception as e:
        health_status["error"] = str(e)
        logger.error(f"Health check failed: {e}")
    
    return health_status

def get_db_session():
    """
    Get database session for dependency injection.
    This is an alias for SessionLocal context manager for consistency.
    """
    return SessionLocal()

# ----------------- Task Management Utilities -----------------
def get_task_by_id(task_id):
    """Get task by ID with error handling"""
    try:
        with SessionLocal() as session:
            return session.query(BaseTaskDB).filter(BaseTaskDB.id == task_id).first()
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        return None

def get_all_tasks(include_inactive=False):
    """Get all tasks with optional filtering"""
    try:
        with SessionLocal() as session:
            query = session.query(BaseTaskDB)
            if not include_inactive:
                query = query.filter(BaseTaskDB.included == True)
            return query.order_by(BaseTaskDB.discipline, BaseTaskDB.name).all()
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return []

def get_tasks_by_discipline(discipline):
    """Get tasks filtered by discipline"""
    try:
        with SessionLocal() as session:
            return session.query(UserBaseTaskDB).filter(
                UserBaseTaskDB.discipline == discipline,
                UserBaseTaskDB.included == True
            ).order_by(BaseTaskDB.name).all()
    except Exception as e:
        logger.error(f"Error getting tasks for discipline {discipline}: {e}")
        return []

# ----------------- Exports -----------------
__all__ = [
    # Core functions
    "init_backend", 
    "check_backend_health",
    
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
    
    # Logging
    "logger"
]

# ----------------- Initialization Status -----------------
logger.info("Backend initialization module ready")
logger.info("Call init_backend() explicitly in app.py to initialize the system")
