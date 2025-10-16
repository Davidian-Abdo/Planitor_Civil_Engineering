#!/usr/bin/env python3
"""
Database migration script for Construction Management App
Run this to initialize/update database schema with enhanced models
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, SessionLocal
from backend.db_models import Base, UserDB
from backend.auth import AuthManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def migrate_database():
    """Create or update database schema with enhanced models"""
    try:
        logger.info("🚀 Starting database migration...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        # Create default admin user if none exists
        with SessionLocal() as session:
            admin_exists = session.query(UserDB).filter(UserDB.role == "admin").first()
            if not admin_exists:
                logger.info("Creating default admin user...")
                auth_manager = AuthManager(session)
                hashed_password = auth_manager.hash_password("admin123")
                
                admin_user = UserDB(
                    username="admin",
                    email="admin@construction.com",
                    hashed_password=hashed_password,
                    full_name="System Administrator",
                    role="admin"
                )
                session.add(admin_user)
                session.commit()
                logger.info("✅ Default admin user created (username: admin, password: admin123)")
            else:
                logger.info("✅ Admin user already exists")
        
        # Verify tables
        with SessionLocal() as session:
            table_count = session.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'").scalar()
            logger.info(f"✅ Database ready with {table_count} tables")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)