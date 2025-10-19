
import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, SessionLocal
from backend.db_models import Base, UserDB
from backend.auth import AuthManager
import sqlalchemy as sa

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def safe_create_tables():
    """Safely create tables handling existing objects"""
    try:
        # Check if tables already exist by querying a known table
        with engine.connect() as conn:
            try:
                # Try to query users table to see if it exists
                conn.execute(sa.text("SELECT 1 FROM users LIMIT 1"))
                logger.info("✅ Database tables already exist")
                return True
            except Exception:
                # Tables don't exist, create them
                logger.info("🚀 Creating database tables...")
                Base.metadata.create_all(bind=engine)
                logger.info("✅ Database tables created successfully")
                return True
                
    except Exception as e:
        logger.error(f"❌ Table creation failed: {e}")
        return False

def safe_create_indexes():
    """Safely create indexes with existence checks"""
    try:
        with engine.connect() as conn:
            # List of indexes to create safely
            indexes_sql = [
                "CREATE INDEX IF NOT EXISTS idx_task_resource_type ON user_base_tasks (resource_type, included)",
                "CREATE INDEX IF NOT EXISTS idx_task_discipline_included ON user_base_tasks (discipline, included)",
                "CREATE INDEX IF NOT EXISTS idx_task_creator ON user_base_tasks (creator_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_user_tasks_user ON user_base_tasks (user_id, included)",
                "CREATE INDEX IF NOT EXISTS idx_login_attempts_username_time ON login_attempts (username, attempt_time)",
                "CREATE INDEX IF NOT EXISTS idx_login_attempts_time ON login_attempts (attempt_time)",
                "CREATE INDEX IF NOT EXISTS idx_schedule_project ON schedules (project_id, zone, floor)",
                "CREATE INDEX IF NOT EXISTS idx_schedule_dates ON schedules (start_date, end_date)",
                "CREATE INDEX IF NOT EXISTS idx_schedule_status ON schedules (status, progress)",
                "CREATE INDEX IF NOT EXISTS idx_monitoring_project ON monitoring (project_id, monitoring_date)",
                "CREATE INDEX IF NOT EXISTS idx_monitoring_user ON monitoring (user_id, created_at)",
            ]
            
            for sql in indexes_sql:
                try:
                    conn.execute(sa.text(sql))
                    index_name = sql.split("IF NOT EXISTS ")[1].split(" ON")[0]
                    logger.info(f"✅ Index {index_name} created or already exists")
                except Exception as e:
                    logger.warning(f"⚠️ Index creation skipped for {sql}: {e}")
            
            conn.commit()
            return True
            
    except Exception as e:
        logger.error(f"❌ Index creation failed: {e}")
        return False

def create_default_users():
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
                        auth_manager = AuthManager(session)
                        hashed_password = auth_manager.hash_password(user_data["password"])
                        user = UserDB(
                            username=user_data["username"],
                            email=user_data["email"],
                            hashed_password=hashed_password,
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
                
        return True
    except Exception as e:
        logger.warning(f"Could not create default users: {e}")
        return False

def migrate_database():
    """Safe database migration with existence checks"""
    try:
        logger.info("🚀 Starting safe database migration...")
        
        # Step 1: Safely create tables
        if not safe_create_tables():
            return False
        
        # Step 2: Safely create indexes
        if not safe_create_indexes():
            return False
        
        # Step 3: Create default users if none exist
        if not create_default_users():
            logger.warning("User creation had issues, but continuing...")
        
        # Final verification
        with SessionLocal() as session:
            table_count = session.execute(
                sa.text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            ).scalar()
            logger.info(f"✅ Database ready with {table_count} tables")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
