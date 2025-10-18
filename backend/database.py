from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import os
import logging
import time
from contextlib import contextmanager
import warnings

logger = logging.getLogger(__name__)


def save_discipline_zone_config(session, project_id, discipline_zone_cfg):
    """
    Save discipline-zone configuration for a specific project.

    Example of discipline_zone_cfg:
    {
        "Structure": {
            "zone_groups": [["Zone_1", "Zone_2"], ["Zone_3"]],
            "strategy": "sequential"
        },
        "VRD": {
            "zone_groups": [["Zone_1"], ["Zone_2", "Zone_3"]],
            "strategy": "parallel"
        }
    }
    """
    from backend.db_models import DisciplineZoneConfigDB

    cfg = DisciplineZoneConfigDB(
        project_id=project_id,
        config_data=discipline_zone_cfg
    )
    session.add(cfg)
    session.commit()
    return cfg


def get_discipline_zone_config(session, project_id):
    """Retrieve saved discipline-zone configuration for a project."""
    from backend.db_models import DisciplineZoneConfigDB
    cfg = session.query(DisciplineZoneConfigDB).filter_by(project_id=project_id).first()
    return cfg.config_data if cfg else {}


# Enhanced configuration with validation
class DatabaseConfig:
    def __init__(self):
        self.env = os.getenv("ENVIRONMENT", "development")
        self.user = self._get_required("DB_USER", "postgres")
        self.password = self._get_password()
        self.host = self._get_required("DB_HOST", "localhost")
        self.port = self._get_required("DB_PORT", "5432")
        self.name = self._get_required("DB_NAME", "construction_db")
        
    def _get_required(self, env_var, default):
        value = os.getenv(env_var, default)
        if not value and self.env == "production":
            raise ValueError(f"{env_var} environment variable required in production")
        return value
    
    def _get_password(self):
        password = os.getenv("DB_PASSWORD")
        if not password:
            if self.env == "production":
                raise ValueError("DB_PASSWORD environment variable required in production")
            else:
                password = "postgres"
                logger.warning("🚨 Using default database password - NOT FOR PRODUCTION!")
        return password
    
    @property
    def url(self):
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

# Initialize configuration
config = DatabaseConfig()

# Production-optimized engine
engine = create_engine(
    config.url,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    poolclass=QueuePool,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_timeout=30,
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": 10,
        "application_name": f"construction_app_{config.env}"
    }
)

# Enhanced session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Better performance
)

Base = declarative_base()

# Advanced session dependency with metrics
@contextmanager
def get_db_session():
    """
    Enhanced session context manager with metrics and proper error handling.
    Use in with statements: `with get_db_session() as session:`
    """
    session = SessionLocal()
    start_time = time.time()
    
    try:
        yield session
        session.commit()
        logger.debug(f"Database session completed successfully in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Database session failed after {time.time() - start_time:.2f}s: {e}")
        raise
        
    finally:
        session.close()

# Health check function
def check_database_health():
    """Check database connectivity and pool status"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        pool_status = {
            "checkedout": engine.pool.checkedout(),
            "checkedin": engine.pool.checkedin(),
            "overflow": engine.pool.overflow(),
            "size": engine.pool.size()
        }
        
        return {
            "status": "healthy",
            "pool": pool_status,
            "database": f"{config.host}:{config.port}/{config.name}",
            "environment": config.env
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": f"{config.host}:{config.port}/{config.name}",
            "environment": config.env
        }

# Table initialization with versioning
def init_db():
    """Initialize database tables with version tracking"""
    from backend.db_models import Base as ModelsBase
    
    try:
        ModelsBase.metadata.create_all(bind=engine)
        
        # Record schema version (PostgreSQL compatible)
        with engine.connect() as conn:
            # Create schema versions table if not exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_versions (
                    version VARCHAR(50) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            current_version = os.getenv("SCHEMA_VERSION", "1.0.0")
            conn.execute(
                text("INSERT INTO schema_versions (version) VALUES (:version) ON CONFLICT (version) DO NOTHING"),
                {"version": current_version}
            )
            conn.commit()
            
        logger.info(f"✅ Database initialized successfully for {config.env} environment")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

# SQLAlchemy event listeners for monitoring
@event.listens_for(engine, "connect")
def set_connection_settings(dbapi_connection, connection_record):
    """Set connection-level settings"""
    logger.debug("New database connection established")
    
@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout"""
    logger.debug("Connection checked out from pool")

logger.info(f"Database module initialized for {config.env} environment")
