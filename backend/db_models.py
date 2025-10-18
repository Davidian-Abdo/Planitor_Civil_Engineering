


from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, JSON,
    CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

# Constants for validation
VALID_ROLES = ['admin', 'manager', 'worker', 'viewer']
VALID_TASK_TYPES = ['worker', 'equipment', 'hybrid']
VALID_RESOURCE_TYPES = ['BétonArmée', 'Férailleur', 'ConstMéttalique', 'plaquiste', 'Etanchiété', 'Revetement', 'peinture']
VALID_DISCIPLINES = ['Préliminaire', 'Terrassement', 'Fondations', 'Structure', 'VRD', 'Finitions']
VALID_SCHEDULE_STATUS = ['scheduled', 'in_progress', 'completed', 'delayed']

class LoginAttemptDB(Base):
    __tablename__ = "login_attempts"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, index=True)
    successful = Column(Boolean, default=False)
    attempt_time = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)
    __table_args__ = (
        Index("idx_login_attempts_username_time", "username", "attempt_time"),
        Index("idx_login_attempts_time", "attempt_time"),
    )

class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default="worker", nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Table constraints
    __table_args__ = (
        CheckConstraint(f"role IN ({', '.join(repr(r) for r in VALID_ROLES)})", name="valid_user_role"),
        CheckConstraint("char_length(username) >= 3", name="username_min_length"),
    )

    # FIXED: Relationships - UserBaseTaskDB is now the main task model
    tasks_created = relationship("UserBaseTaskDB", back_populates="creator")
    schedules = relationship("ScheduleDB", back_populates="user")
    monitorings = relationship("MonitoringDB", back_populates="user")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

# FIXED: This is now your MAIN task model (replaces BaseTaskDB)
class UserBaseTaskDB(Base):
    __tablename__ = "user_base_tasks"  # ✅ CORRECT: Separate table for user tasks

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # ✅ Link to user
    name = Column(String(100), nullable=False, index=True)
    discipline = Column(String(50), nullable=False)
    resource_type = Column(String(20), nullable=False)
    task_type = Column(String(20), default="worker")
    base_duration = Column(Float, default=1.0, nullable=False)
    min_crews_needed = Column(Integer, default=1)
    min_equipment_needed = Column(JSON, default=lambda: {})
    predecessors = Column(JSON, default=lambda: [])
    repeat_on_floor = Column(Boolean, default=True)
    included = Column(Boolean, default=True)
    delay = Column(Integer, default=0)
    
    # Cross-floor configuration
    cross_floor_dependencies = Column(JSON, default=lambda: [])
    applies_to_floors = Column(String(20), default="auto")
    
    # System constraints
    max_duration = Column(Float, default=365.0)
    max_crews = Column(Integer, default=50)

    # User tracking
    created_by_user = Column(Boolean, default=True)  # ✅ Always True for user tasks
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint(f"resource_type IN ({', '.join(repr(r) for r in VALID_RESOURCE_TYPES)})", name="valid_resource_type"),
        CheckConstraint(f"task_type IN ({', '.join(repr(r) for r in VALID_TASK_TYPES)})", name="valid_task_type"),
        CheckConstraint(f"discipline IN ({', '.join(repr(d) for d in VALID_DISCIPLINES)})", name="valid_discipline"),
        CheckConstraint("base_duration >= 0", name="positive_duration"),
        CheckConstraint("min_crews_needed >= 0", name="non_negative_crews"),
        CheckConstraint("delay >= 0", name="non_negative_delay"),
        Index('idx_task_discipline_included', 'discipline', 'included'),
        Index('idx_task_creator', 'creator_id', 'created_at'),
        Index('idx_task_resource_type', 'resource_type', 'included'),
        Index('idx_user_tasks_user', 'user_id', 'included'),  # ✅ Added user index
        UniqueConstraint('user_id', 'name', 'discipline', name='unique_user_task_per_discipline'),  # ✅ User-specific uniqueness
    )

    # FIXED: Relationships
    creator = relationship("UserDB", back_populates="tasks_created", foreign_keys=[creator_id])
    user = relationship("UserDB", foreign_keys=[user_id])  # ✅ Link to user owner

    def __repr__(self):
        return f"<UserTask {self.name} ({self.discipline})>"

class DisciplineZoneConfigDB(Base):
    __tablename__ = "discipline_zone_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), nullable=False, index=True)
    discipline = Column(String(50), nullable=False)
    strategy = Column(String(50), default="group_sequential")
    zone_groups = Column(JSON, nullable=False, default=lambda: [])

    def __repr__(self):
        return f"<DisciplineZoneConfig project={self.project_id} discipline={self.discipline}>"

# FIXED: ScheduleDB now references UserBaseTaskDB
class ScheduleDB(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(String(50), nullable=False, index=True)
    project_name = Column(String(200), nullable=False)
    zone = Column(String(50), nullable=False)
    floor = Column(Integer, nullable=False)
    task_id = Column(Integer, ForeignKey("user_base_tasks.id"), nullable=False)  # ✅ FIXED: Reference user_base_tasks
    task_name = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    actual_start_date = Column(DateTime, nullable=True)
    actual_end_date = Column(DateTime, nullable=True)
    progress = Column(Float, default=0.0)
    status = Column(String(20), default="scheduled")
    allocated_crews = Column(Integer)
    allocated_equipment = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="valid_date_range"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="valid_progress"),
        CheckConstraint("floor >= 0", name="non_negative_floor"),
        CheckConstraint(f"status IN ({', '.join(repr(s) for s in VALID_SCHEDULE_STATUS)})", name="valid_schedule_status"),
        Index('idx_schedule_project', 'project_id', 'zone', 'floor'),
        Index('idx_schedule_dates', 'start_date', 'end_date'),
        Index('idx_schedule_status', 'status', 'progress'),
    )

    # FIXED: Relationships
    user = relationship("UserDB", back_populates="schedules")
    task = relationship("UserBaseTaskDB")  # ✅ FIXED: Reference UserBaseTaskDB

    def __repr__(self):
        return f"<Schedule {self.task_name} - {self.project_name}>"

class MonitoringDB(Base):
    __tablename__ = "monitoring"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(String(50), nullable=False, index=True)
    reference_file_path = Column(String(500), nullable=False)
    actual_file_path = Column(String(500), nullable=False)
    analysis_csv_path = Column(String(500), nullable=True)
    monitoring_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Table indexes
    __table_args__ = (
        Index('idx_monitoring_project', 'project_id', 'monitoring_date'),
        Index('idx_monitoring_user', 'user_id', 'created_at'),
    )

    # relationships
    user = relationship("UserDB", back_populates="monitorings")

    def __repr__(self):
        return f"<Monitoring {self.project_id} - {self.monitoring_date}>"
