#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, SessionLocal
import sqlalchemy as sa

def check_migration_status():
    """Check if database has been properly migrated"""
    try:
        with engine.connect() as conn:
            # Check if resource_type constraint exists (should NOT exist)
            result = conn.execute(sa.text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE table_name = 'user_base_tasks' 
                    AND constraint_name = 'valid_resource_type'
                )
            """))
            has_old_constraint = result.scalar()
            
            # Check if base_duration allows NULL
            result = conn.execute(sa.text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'user_base_tasks' 
                AND column_name = 'base_duration'
            """))
            allows_null = result.scalar() == 'YES'
            
            # Check default tasks exist
            from backend.db_models import UserBaseTaskDB
            with SessionLocal() as session:
                task_count = session.query(UserBaseTaskDB).count()
            
            return {
                "migration_status": "✅ Complete" if not has_old_constraint and allows_null else "❌ Needed",
                "old_constraint_removed": not has_old_constraint,
                "allows_null_duration": allows_null,
                "total_tasks": task_count
            }
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    status = check_migration_status()
    print("🔍 Database Migration Status:")
    for key, value in status.items():
        print(f"  {key}: {value}"
