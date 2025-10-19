import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine
import sqlalchemy as sa

def drop_problematic_indexes():
    """Drop all problematic indexes that are causing duplicates"""
    with engine.connect() as conn:
        # List of indexes to drop
        indexes_to_drop = [
            "idx_task_resource_type",
            "idx_task_creator", 
            "idx_task_discipline_included",
            "idx_user_tasks_user"
        ]
        
        for index_name in indexes_to_drop:
            try:
                conn.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))
                print(f"✅ Dropped index: {index_name}")
            except Exception as e:
                print(f"⚠️ Could not drop {index_name}: {e}")
        
        conn.commit()
        print("✅ All problematic indexes dropped!")

if __name__ == "__main__":
    drop_problematic_indexes()
