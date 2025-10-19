#!/usr/bin/env python3
"""
Database backup script - UPDATED FOR POSTGRESQL
"""

import sys
import os
import datetime
import logging
import subprocess
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use environment variables instead of missing config
DB_NAME = os.getenv("DB_NAME", "construction_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def backup_database():
    """Create a PostgreSQL backup using pg_dump"""
    try:
        # Create backups directory
        backups_dir = Path("backups")
        backups_dir.mkdir(exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backups_dir / f"construction_db_backup_{timestamp}.sql"
        
        # Build pg_dump command
        cmd = [
            "pg_dump",
            "-h", DB_HOST,
            "-p", DB_PORT,
            "-U", DB_USER,
            "-d", DB_NAME,
            "-f", str(backup_file),
            "--verbose"
        ]
        
        # Set password in environment for pg_dump
        env = os.environ.copy()
        env["PGPASSWORD"] = os.getenv("DB_PASSWORD", "")
        
        # Execute backup
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"✅ Database backed up to: {backup_file}")
            return True
        else:
            logger.error(f"❌ Backup failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return False

if __name__ == "__main__":
    success = backup_database()
    sys.exit(0 if success else 1)
