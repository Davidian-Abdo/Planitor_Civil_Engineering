#!/usr/bin/env python3
"""
Database backup script
Creates timestamped backups of the construction database
"""

import sys
import os
import shutil
import datetime
import logging
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def backup_database():
    """Create a backup of the database file"""
    try:
        # Create backups directory
        backups_dir = Path("backups")
        backups_dir.mkdir(exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backups_dir / f"construction_db_backup_{timestamp}.db"
        
        # Copy database file (for SQLite)
        if settings.DATABASE_URL.startswith("sqlite"):
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_file)
                logger.info(f"✅ Database backed up to: {backup_file}")
                return True
            else:
                logger.error("❌ Database file not found")
                return False
        else:
            logger.info("ℹ️  Backup for PostgreSQL requires pg_dump utility")
            return True
            
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return False

if __name__ == "__main__":
    success = backup_database()
    sys.exit(0 if success else 1)