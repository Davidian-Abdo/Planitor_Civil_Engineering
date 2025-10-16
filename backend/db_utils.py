from sqlalchemy.orm import Session
from backend.db_models import User, BaseTaskDB, ScheduleDB, MonitoringDB
from typing import List, Optional

# ---------------- User CRUD ----------------
def create_user(db: Session, user: User) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def list_users(db: Session) -> List[User]:
    return db.query(User).all()


# ---------------- Task CRUD ----------------
def get_base_task(db: Session, task_id: int) -> Optional[BaseTaskDB]:
    return db.query(BaseTaskDB).filter(BaseTaskDB.id == task_id).first()

def list_base_tasks(db: Session, discipline: Optional[str] = None) -> List[BaseTaskDB]:
    query = db.query(BaseTaskDB)
    if discipline:
        query = query.filter(BaseTaskDB.discipline == discipline)
    return query.all()


# ---------------- Schedule CRUD ----------------
def create_schedule(db: Session, schedule: ScheduleDB) -> ScheduleDB:
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule

def list_schedules(db: Session, user_id: Optional[int] = None) -> List[ScheduleDB]:
    query = db.query(ScheduleDB)
    if user_id:
        query = query.filter(ScheduleDB.user_id == user_id)
    return query.all()


# ---------------- Monitoring CRUD ----------------
def create_monitoring(db: Session, monitoring: MonitoringDB) -> MonitoringDB:
    db.add(monitoring)
    db.commit()
    db.refresh(monitoring)
    return monitoring

def list_monitorings(db: Session, user_id: Optional[int] = None) -> List[MonitoringDB]:
    query = db.query(MonitoringDB)
    if user_id:
        query = query.filter(MonitoringDB.user_id == user_id)
    return query.all()