"""
Enhanced database operations for task management
"""
import streamlit as st  # ← ADD THIS FOR DEBUGGING
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.db_models import UserBaseTaskDB, UserDB
import logging

logger = logging.getLogger(__name__)
def save_enhanced_task(session, task, is_new, user_id, name, discipline, resource_type, 
                      base_duration, min_crews_needed, delay, min_equipment_needed, 
                      predecessors, cross_floor_config, task_type, repeat_on_floor, 
                      included=True, sub_discipline=None):  # ✅ NEW: Add sub_discipline parameter
    """Save task with all parameters - INCLUDES sub_discipline"""
    try:
        if is_new:
            new_task = UserBaseTaskDB(
                user_id=user_id,
                name=name,
                discipline=discipline,
                sub_discipline=sub_discipline,  # ✅ NEW: Include sub_discipline
                resource_type=resource_type,
                task_type=task_type,
                base_duration=base_duration,
                min_crews_needed=min_crews_needed,
                min_equipment_needed=min_equipment_needed,
                predecessors=predecessors,
                delay=delay,
                repeat_on_floor=repeat_on_floor,
                included=included,
                cross_floor_dependencies=cross_floor_config.get('cross_floor_dependencies', []),
                applies_to_floors=cross_floor_config.get('applies_to_floors', 'auto'),
                created_by_user=True
            )
            session.add(new_task)
        else:
            # Update existing task
            task.name = name
            task.discipline = discipline
            task.sub_discipline = sub_discipline  # ✅ NEW: Update sub_discipline
            task.resource_type = resource_type
            task.task_type = task_type
            task.base_duration = base_duration
            task.min_crews_needed = min_crews_needed
            task.min_equipment_needed = min_equipment_needed
            task.predecessors = predecessors
            task.delay = delay
            task.repeat_on_floor = repeat_on_floor
            task.included = included
            task.cross_floor_dependencies = cross_floor_config.get('cross_floor_dependencies', [])
            task.applies_to_floors = cross_floor_config.get('applies_to_floors', 'auto')
        
        session.commit()
        
        sub_disc_info = f" | Sub: {sub_discipline}" if sub_discipline else ""
        duration_info = "🔄 calculated by engine" if base_duration is None else f"⏱️ fixed at {base_duration} days"
        logger.info(f"✅ Task {'created' if is_new else 'updated'}: {name} ({discipline}{sub_disc_info}) - {duration_info}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save task: {e}")
        session.rollback()
        return False

def copy_default_tasks_to_user(user_id: int, session) -> int:
    """
    Copy default tasks from defaults.py to a specific user
    Returns number of tasks copied
    """
    try:
        from defaults import BASE_TASKS
        
        # Get existing task names for this user to avoid duplicates
        existing_tasks = session.query(UserBaseTaskDB.name).filter(
            UserBaseTaskDB.user_id == user_id
        ).all()
        existing_task_names = {task[0] for task in existing_tasks}
        
        tasks_created = 0
        for discipline, tasks in BASE_TASKS.items():
            for base_task in tasks:
                # Skip if task already exists for this user
                if getattr(base_task, 'name', 'Unknown') in existing_task_names:
                    continue
                    
                # Skip excluded tasks
                if not getattr(base_task, 'included', True):
                    continue
                
                # Create new task for user
                new_task = UserBaseTaskDB(
                    user_id=user_id,
                    name=getattr(base_task, 'name', 'Unknown Task'),
                    discipline=discipline,
                    sub_discipline=getattr(base_task, 'sub_discipline', None),
                    resource_type=getattr(base_task, 'resource_type', 'BétonArmée'),
                    task_type=getattr(base_task, 'task_type', 'worker'),
                    base_duration=getattr(base_task, 'base_duration', None),
                    min_crews_needed=getattr(base_task, 'min_crews_needed', 1),
                    min_equipment_needed=getattr(base_task, 'min_equipment_needed', {}),
                    predecessors=getattr(base_task, 'predecessors', []),
                    repeat_on_floor=getattr(base_task, 'repeat_on_floor', True),
                    included=getattr(base_task, 'included', True),
                    delay=getattr(base_task, 'delay', 0),
                    cross_floor_dependencies=getattr(base_task, 'cross_floor_dependencies', []),
                    applies_to_floors=getattr(base_task, 'applies_to_floors', 'auto'),
                    created_by_user=False,  # Mark as system-created
                    creator_id=user_id
                )
                session.add(new_task)
                tasks_created += 1
        
        if tasks_created > 0:
            session.commit()
            logger.info(f"Copied {tasks_created} default tasks to user {user_id}")
        
        return tasks_created
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error copying default tasks to user {user_id}: {e}")
        return 0
def create_default_tasks_from_defaults_py(user_id=None):
    """Create default tasks from defaults.py by calling copy_default_tasks_to_user"""
    try:
        with SessionLocal() as session:
            if user_id is None:
                admin_user = session.query(UserDB).filter_by(username="admin").first()
                if admin_user:
                    user_id = admin_user.id
                    logger.info(f"Using admin user (ID: {user_id}) for system tasks")
                else:
                    logger.error("No admin user found and no user_id provided")
                    return 0
            
            # Call the core copying function
            tasks_created = copy_default_tasks_to_user(user_id, session)
            logger.info(f"Created {tasks_created} default tasks for user {user_id}")
            return tasks_created
            
    except Exception as e:
        logger.error(f"Error in create_default_tasks_from_defaults_py: {e}")
        return 0
def duplicate_task(original_task, user_id, modifications=None):
    """Duplicate a task with optional modifications - INCLUDES sub_discipline"""
    try:
        with SessionLocal() as session:
            new_task = UserBaseTaskDB(
                user_id=user_id,
                name=modifications.get('name', f"{original_task.name} (Copy)") if modifications else f"{original_task.name} (Copy)",
                discipline=original_task.discipline,
                sub_discipline=original_task.sub_discipline,  # ✅ NEW: Copy sub_discipline
                resource_type=original_task.resource_type,
                task_type=original_task.task_type,
                base_duration=modifications.get('base_duration', original_task.base_duration) if modifications else original_task.base_duration,
                min_crews_needed=modifications.get('min_crews_needed', original_task.min_crews_needed) if modifications else original_task.min_crews_needed,
                min_equipment_needed=original_task.min_equipment_needed,
                predecessors=original_task.predecessors.copy() if original_task.predecessors else [],
                delay=original_task.delay,
                repeat_on_floor=original_task.repeat_on_floor,
                cross_floor_dependencies=original_task.cross_floor_dependencies.copy() if original_task.cross_floor_dependencies else [],
                applies_to_floors=original_task.applies_to_floors,
                created_by_user=True
            )
            session.add(new_task)
            session.commit()
            sub_disc_info = f" (Sub: {original_task.sub_discipline})" if original_task.sub_discipline else ""
            logger.info(f"✅ Task duplicated: {new_task.name}{sub_disc_info}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to duplicate task: {e}")
        return False

# ✅ NEW: Add filtering by sub_discipline
def get_user_tasks_with_filters(user_id, search_term="", discipline_filter=None, sub_discipline_filter=None):
    """Get tasks with advanced filtering - INCLUDES sub_discipline filtering"""
    try:
        with SessionLocal() as session:
            query = session.query(UserBaseTaskDB).filter(UserBaseTaskDB.user_id == user_id)
            
            if search_term:
                query = query.filter(UserBaseTaskDB.name.ilike(f"%{search_term}%"))
            
            if discipline_filter:
                query = query.filter(UserBaseTaskDB.discipline.in_(discipline_filter))
            
            if sub_discipline_filter:  # ✅ NEW: Filter by sub_discipline
                query = query.filter(UserBaseTaskDB.sub_discipline.in_(sub_discipline_filter))
            
            return query.order_by(UserBaseTaskDB.discipline, UserBaseTaskDB.sub_discipline, UserBaseTaskDB.name).all()
    except Exception as e:
        logger.error(f"❌ Failed to load tasks: {e}")
        return []

# ✅ NEW: Migration function for sub_discipline column
def migrate_sub_discipline_column():
    """Add sub_discipline column to existing database"""
    try:
        with SessionLocal() as session:
            # Check if sub_discipline column exists
            from sqlalchemy import inspect
            inspector = inspect(session.bind)
            columns = [col['name'] for col in inspector.get_columns('user_base_tasks')]
            
            if 'sub_discipline' not in columns:
                logger.info("🔄 Adding sub_discipline column to user_base_tasks table...")
                
                with session.bind.connect() as conn:
                    # Add the new column
                    conn.execute(sa.text("""
                        ALTER TABLE user_base_tasks 
                        ADD COLUMN sub_discipline VARCHAR(50)
                    """))
                    
                    # Update indexes and constraints
                    conn.execute(sa.text("""
                        CREATE INDEX idx_task_sub_discipline 
                        ON user_base_tasks (sub_discipline, included)
                    """))
                    
                    # Drop old unique constraint and create new one
                    conn.execute(sa.text("""
                        ALTER TABLE user_base_tasks 
                        DROP CONSTRAINT IF EXISTS unique_user_task_per_discipline
                    """))
                    
                    conn.execute(sa.text("""
                        ALTER TABLE user_base_tasks 
                        ADD CONSTRAINT unique_user_task_per_discipline_sub 
                        UNIQUE (user_id, name, discipline, sub_discipline)
                    """))
                    
                    conn.commit()
                
                logger.info("✅ Successfully added sub_discipline column and updated constraints")
                return True
            else:
                logger.info("✅ sub_discipline column already exists")
                return True
                
    except Exception as e:
        logger.error(f"❌ Failed to migrate sub_discipline column: {e}")
        return False

# ✅ UPDATE: Enhanced database check function
def check_and_migrate_database():
    """Check if database needs migration and apply changes safely - INCLUDES sub_discipline"""
    try:
        with SessionLocal() as session:
            # First migrate sub_discipline column
            if not migrate_sub_discipline_column():
                return False
                
            # Then check other constraints (your existing code)
            try:
                test_task = UserBaseTaskDB(
                    user_id=1,
                    name="Migration Test Task",
                    discipline="Préliminaire",
                    sub_discipline="TestSubDiscipline",  # ✅ TEST with sub_discipline
                    resource_type="TestResourceType",
                    base_duration=None,
                    min_crews_needed=1,
                    created_by_user=False
                )
                session.add(test_task)
                session.commit()
                
                session.delete(test_task)
                session.commit()
                logger.info("✅ Database supports all required features including sub_discipline")
                return True
                
            except Exception as migration_needed:
                logger.info("🔄 Database needs additional migration, applying changes...")
                session.rollback()
                
                # Your existing migration code here...
                # (rest of your existing migration logic)
                
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        return False

def delete_task(task_id: int, user_id: int) -> bool:
    """
    Delete a task by ID, ensuring it belongs to the user
    Returns True if successful, False otherwise
    """
    try:
        with SessionLocal() as session:
            task = session.query(UserBaseTaskDB).filter(
                UserBaseTaskDB.id == task_id,
                UserBaseTaskDB.user_id == user_id
            ).first()
            
            if task:
                session.delete(task)
                session.commit()
                logger.info(f"✅ Task deleted: {task.name} (ID: {task_id})")
                return True
            else:
                logger.warning(f"⚠️ Task not found or access denied: ID {task_id} for user {user_id}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Failed to delete task {task_id}: {e}")
        session.rollback()
        return False

def get_task_by_id(task_id: int, user_id: int):
    """Get a specific task by ID for a user"""
    try:
        with SessionLocal() as session:
            return session.query(UserBaseTaskDB).filter(
                UserBaseTaskDB.id == task_id,
                UserBaseTaskDB.user_id == user_id
            ).first()
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        return None

def get_user_tasks(user_id: int):
    """Get all tasks for a specific user"""
    try:
        with SessionLocal() as session:
            return session.query(UserBaseTaskDB).filter(
                UserBaseTaskDB.user_id == user_id
            ).order_by(UserBaseTaskDB.discipline, UserBaseTaskDB.name).all()
    except Exception as e:
        logger.error(f"Error getting tasks for user {user_id}: {e}")
        return []
