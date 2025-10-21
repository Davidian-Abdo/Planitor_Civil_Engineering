"""
Enhanced database operations for task management
"""
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.db_models import UserBaseTaskDB, UserDB
import logging

logger = logging.getLogger(__name__)

def copy_default_tasks_to_user(user_id):
    """Copy default tasks to user's personal library"""
    try:
        with SessionLocal() as session:
            # Get default tasks (system tasks or tasks with no specific user)
            default_tasks = session.query(UserBaseTaskDB).filter(
                (UserBaseTaskDB.user_id.is_(None)) | 
                (UserBaseTaskDB.created_by_user == False)
            ).all()
            
            created_count = 0
            for default_task in default_tasks:
                # Check if user already has this task
                existing = session.query(UserBaseTaskDB).filter(
                    UserBaseTaskDB.user_id == user_id,
                    UserBaseTaskDB.name == default_task.name,
                    UserBaseTaskDB.discipline == default_task.discipline
                ).first()
                
                if not existing:
                    # Create user-specific copy
                    user_task = UserBaseTaskDB(
                        user_id=user_id,
                        name=default_task.name,
                        discipline=default_task.discipline,
                        resource_type=default_task.resource_type,
                        task_type=getattr(default_task, 'task_type', 'worker'),
                        base_duration=default_task.base_duration,
                        min_crews_needed=default_task.min_crews_needed,
                        min_equipment_needed=default_task.min_equipment_needed,
                        predecessors=default_task.predecessors,
                        repeat_on_floor=default_task.repeat_on_floor,
                        included=default_task.included,
                        delay=default_task.delay,
                        cross_floor_dependencies=getattr(default_task, 'cross_floor_dependencies', []),
                        applies_to_floors=getattr(default_task, 'applies_to_floors', 'auto'),
                        created_by_user=True  # Mark as user's custom task
                    )
                    session.add(user_task)
                    created_count += 1
            
            session.commit()
            logger.info(f"✅ Copied {created_count} default tasks to user {user_id}")
            return created_count
            
    except Exception as e:
        logger.error(f"❌ Failed to copy default tasks: {e}")
        return 0

def save_enhanced_task(session, task, is_new, user_id, name, discipline, resource_type, 
                      base_duration, min_crews_needed, delay, min_equipment_needed, 
                      predecessors, cross_floor_config, task_type, repeat_on_floor):
    """Save task with all parameters to database"""
    try:
        if is_new:
            new_task = UserBaseTaskDB(
                user_id=user_id,
                name=name,
                discipline=discipline,
                resource_type=resource_type,
                task_type=task_type,
                base_duration=base_duration,
                min_crews_needed=min_crews_needed,
                min_equipment_needed=min_equipment_needed,
                predecessors=predecessors,
                delay=delay,
                repeat_on_floor=repeat_on_floor,
                cross_floor_dependencies=cross_floor_config.get('cross_floor_dependencies', []),
                applies_to_floors=cross_floor_config.get('applies_to_floors', 'auto'),
                created_by_user=True
            )
            session.add(new_task)
        else:
            # Update existing task
            task.name = name
            task.discipline = discipline
            task.resource_type = resource_type
            task.task_type = task_type
            task.base_duration = base_duration
            task.min_crews_needed = min_crews_needed
            task.min_equipment_needed = min_equipment_needed
            task.predecessors = predecessors
            task.delay = delay
            task.repeat_on_floor = repeat_on_floor
            task.cross_floor_dependencies = cross_floor_config.get('cross_floor_dependencies', [])
            task.applies_to_floors = cross_floor_config.get('applies_to_floors', 'auto')
        
        session.commit()
        logger.info(f"✅ Task {'created' if is_new else 'updated'}: {name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save task: {e}")
        session.rollback()
        return False

def duplicate_task(original_task, user_id, modifications=None):
    """Duplicate a task with optional modifications"""
    try:
        with SessionLocal() as session:
            new_task = UserBaseTaskDB(
                user_id=user_id,
                name=modifications.get('name', f"{original_task.name} (Copy)") if modifications else f"{original_task.name} (Copy)",
                discipline=original_task.discipline,
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
            logger.info(f"✅ Task duplicated: {new_task.name}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to duplicate task: {e}")
        return False

def delete_task(task_id, user_id):
    """Delete a task with confirmation"""
    try:
        with SessionLocal() as session:
            task = session.query(UserBaseTaskDB).filter_by(id=task_id, user_id=user_id).first()
            if task:
                task_name = task.name
                session.delete(task)
                session.commit()
                logger.info(f"✅ Task deleted: {task_name}")
                return True
            else:
                logger.warning(f"Task not found for deletion: {task_id}")
                return False
    except Exception as e:
        logger.error(f"❌ Failed to delete task: {e}")
        return False

def get_user_tasks_with_filters(user_id, search_term="", discipline_filter=None):
    """Get tasks with advanced filtering"""
    try:
        with SessionLocal() as session:
            query = session.query(UserBaseTaskDB).filter(UserBaseTaskDB.user_id == user_id)
            
            if search_term:
                query = query.filter(UserBaseTaskDB.name.ilike(f"%{search_term}%"))
            
            if discipline_filter:
                query = query.filter(UserBaseTaskDB.discipline.in_(discipline_filter))
            
            return query.order_by(UserBaseTaskDB.discipline, UserBaseTaskDB.name).all()
    except Exception as e:
        logger.error(f"❌ Failed to load tasks: {e}")
        return []

def get_user_task_count(user_id):
    """Get count of tasks for a user"""
    try:
        with SessionLocal() as session:
            return session.query(UserBaseTaskDB).filter(UserBaseTaskDB.user_id == user_id).count()
    except Exception as e:
        logger.error(f"❌ Failed to get task count: {e}")
        return 0
