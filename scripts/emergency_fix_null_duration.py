#!/usr/bin/env python3
"""
EMERGENCY FIX: Remove NOT NULL constraint from base_duration column
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def emergency_fix_null_duration():
    """Emergency fix for NULL duration and add base_task_id column"""
    logger.info("🚨 Running EMERGENCY fix for NULL duration and adding base_task_id...")
    
    try:
        with engine.connect() as conn:
            # 1. Make base_duration nullable
            conn.execute(text("""
                ALTER TABLE user_base_tasks 
                ALTER COLUMN base_duration DROP NOT NULL
            """))
            logger.info("✅ Step 1: Made base_duration nullable")
            
            # 2. Drop old constraint
            conn.execute(text("""
                ALTER TABLE user_base_tasks 
                DROP CONSTRAINT IF EXISTS user_base_tasks_base_duration_check
            """))
            logger.info("✅ Step 2: Dropped old constraint")
            
            # 3. Drop new constraint if exists (to avoid conflicts)
            conn.execute(text("""
                ALTER TABLE user_base_tasks 
                DROP CONSTRAINT IF EXISTS positive_or_null_duration
            """))
            logger.info("✅ Step 3: Dropped existing new constraint")
            
            # 4. Add new constraint that allows NULL
            conn.execute(text("""
                ALTER TABLE user_base_tasks 
                ADD CONSTRAINT positive_or_null_duration 
                CHECK (base_duration >= 0 OR base_duration IS NULL)
            """))
            logger.info("✅ Step 4: Added NULL-allowing constraint")
            
            # 5. Add new column base_task_id
            conn.execute(text("""
                ALTER TABLE user_base_tasks
                ADD COLUMN IF NOT EXISTS base_task_id VARCHAR(50)
            """))
            logger.info("✅ Step 5: Added base_task_id column")
            
            # Optional: populate base_task_id with existing id if null
            conn.execute(text("""
                UPDATE user_base_tasks
                SET base_task_id = id::text
                WHERE base_task_id IS NULL
            """))
            logger.info("✅ Step 6: Populated base_task_id with existing ids")
            
            conn.commit()
            
            # Verify the fix
            result = conn.execute(text("""
                SELECT column_name, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'user_base_tasks' AND column_name IN ('base_duration','base_task_id')
            """)).fetchall()
            
            for column in result:
                logger.info(f"Column {column[0]} nullable? {column[1]}")
            
            logger.info("🎉 SUCCESS: Emergency fix applied!")
            return True
                
    except Exception as e:
        logger.error(f"❌ Emergency fix failed: {e}")
        return False

if __name__ == "__main__":
    success = emergency_fix_null_duration()
    sys.exit(0 if success else 1)
