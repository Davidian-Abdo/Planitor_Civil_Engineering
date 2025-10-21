

import os
import logging
import time
import sys
from contextlib import contextmanager
from typing import Generator, Dict, Any

from sqlalchemy import create_engine, event, text, exc
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool, StaticPool

logger = logging.getLogger(__name__)
def save_discipline_zone_config(session, project_id, discipline_zone_cfg):
    """
    Save discipline-zone configuration for a specific project.
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


class DatabaseConfig:
    """
    Enhanced database configuration with validation and environment-specific settings
    """
    
    def __init__(self):
        self.env = os.getenv("ENVIRONMENT", "development").lower()
        self._validate_environment()
        
    def _validate_environment(self):
        """Validate environment and set appropriate defaults"""
        valid_environments = ["development", "testing", "production"]
        if self.env not in valid_environments:
            logger.warning(f"Invalid environment '{self.env}', defaulting to 'development'")
            self.env = "development"
    
    @property
    def url(self) -> str:
        """Get database URL based on environment"""
        if self.env == "testing":
            return "sqlite:///:memory:"
        
        # PostgreSQL configuration
        user = os.getenv("DB_USER", "postgres")
        password = self._get_password()
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "construction_db")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"
    
    def _get_password(self) -> str:
        """Get database password with security warnings"""
        password = os.getenv("DB_PASSWORD")
        if not password:
            if self.env == "production":
                raise ValueError("DB_PASSWORD environment variable required in production")
            else:
                password = "postgres"
                logger.warning("🚨 USING DEFAULT DATABASE PASSWORD - NOT SUITABLE FOR PRODUCTION!")
        return password
    
    @property
    def engine_config(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration based on environment"""
        base_config = {
            "echo": os.getenv("DB_ECHO", "false").lower() == "true",
            "pool_pre_ping": True,
            "connect_args": {
                "connect_timeout": 10,
                "application_name": f"construction_app_{self.env}"
            }
        }
        
        if self.env == "testing":
            base_config.update({
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False}
            })
        else:
            base_config.update({
                "poolclass": QueuePool,
                "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
                "pool_timeout": 30,
                "pool_recycle": 1800,  # 30 minutes
            })
        
        return base_config

class DatabaseMetrics:
    """
    Database performance metrics and monitoring
    """
    
    def __init__(self):
        self.query_count = 0
        self.total_query_time = 0.0
        self.connection_count = 0
        self.error_count = 0
    
    def record_query(self, duration: float):
        """Record query execution metrics"""
        self.query_count += 1
        self.total_query_time += duration
    
    def record_connection(self):
        """Record connection event"""
        self.connection_count += 1
    
    def record_error(self):
        """Record error event"""
        self.error_count += 1
    
    @property
    def avg_query_time(self) -> float:
        """Get average query execution time"""
        if self.query_count == 0:
            return 0.0
        return self.total_query_time / self.query_count
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        return {
            "query_count": self.query_count,
            "avg_query_time_ms": round(self.avg_query_time * 1000, 2),
            "connection_count": self.connection_count,
            "error_count": self.error_count
        }

# Initialize configuration and metrics
config = DatabaseConfig()
metrics = DatabaseMetrics()

# Create engine with optimized configuration
try:
    engine = create_engine(config.url, **config.engine_config)
    
    if config.env == "testing":
        logger.info("🔧 Using in-memory SQLite database for testing")
    else:
        logger.info(f"🔗 Database engine created for {config.env} environment")
        
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
    if config.env == "production":
        raise
    else:
        # Fallback to SQLite for development
        logger.warning("🔄 Falling back to SQLite database")
        engine = create_engine("sqlite:///construction_fallback.db", poolclass=StaticPool)

# Enhanced session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Better performance
    class_=Session
)

Base = declarative_base()

# SQLAlchemy event listeners for monitoring and optimization
@event.listens_for(engine, "connect")
def set_connection_settings(dbapi_connection, connection_record):
    """Set connection-level settings and record metrics"""
    metrics.record_connection()
    
    if config.env == "production":
        # PostgreSQL specific optimizations
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SET statement_timeout = 30000")  # 30 second timeout
            cursor.execute("SET idle_in_transaction_session_timeout = 60000")  # 60 seconds
            cursor.close()
        except Exception as e:
            logger.debug(f"Could not set connection settings: {e}")
    
    logger.debug("New database connection established")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout for monitoring"""
    logger.debug("Connection checked out from pool")

@event.listens_for(engine, "handle_error")
def handle_error(exception_context):
    """Handle database errors and record metrics"""
    metrics.record_error()
    logger.error(f"Database error: {exception_context.original_exception}")

class DatabaseManager:
    """
    Advanced database management with connection pooling and health checks
    """
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Enhanced session context manager with comprehensive error handling and metrics
        """
        session = SessionLocal()
        start_time = time.time()
        
        try:
            yield session
            session.commit()
            
            duration = time.time() - start_time
            metrics.record_query(duration)
            
            if duration > 1.0:  # Log slow queries
                logger.warning(f"🐌 Slow query detected: {duration:.2f}s")
            else:
                logger.debug(f"Query completed in {duration:.2f}s")
                
        except exc.SQLAlchemyError as e:
            session.rollback()
            metrics.record_error()
            logger.error(f"Database error in session: {e}")
            raise
        except Exception as e:
            session.rollback()
            metrics.record_error()
            logger.error(f"Unexpected error in database session: {e}")
            raise
        finally:
            session.close()

def get_db_session() -> Generator[Session, None, None]:
    """
    Public interface for database session management
    """
    with DatabaseManager().get_session() as session:
        yield session

def check_database_health() -> Dict[str, Any]:
    """
    Comprehensive database health check with connection pool status
    """
    health_check = {
        "status": "unknown",
        "environment": config.env,
        "database_type": "postgresql" if config.env != "testing" else "sqlite",
        "connection_test": False,
        "pool_status": {},
        "metrics": metrics.get_metrics(),
        "timestamp": time.time()
    }
    
    try:
        # Test basic connectivity
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            health_check["connection_test"] = True
        
        # Get connection pool status (only for QueuePool)
        if hasattr(engine.pool, 'checkedout'):
            health_check["pool_status"] = {
                "checkedout": engine.pool.checkedout(),
                "checkedin": engine.pool.checkedin(),
                "overflow": engine.pool.overflow(),
                "size": engine.pool.size(),
                "max_overflow": getattr(engine.pool, '_max_overflow', 'N/A')
            }
        
        # Additional PostgreSQL-specific checks
        if config.env != "testing":
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                health_check["database_version"] = result.scalar().split(',')[0]
                
                # Check active connections
                result = conn.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                ))
                health_check["active_connections"] = result.scalar()
        
        health_check["status"] = "healthy"
        logger.debug("Database health check passed")
        
    except Exception as e:
        health_check["status"] = "unhealthy"
        health_check["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
    
    return health_check

def init_db() -> bool:
    """
    Initialize database tables with comprehensive error handling and version tracking
    """
    from backend.db_models import Base as ModelsBase
    
    try:
        logger.info("Initializing database schema...")
        
        # Create all tables
        ModelsBase.metadata.create_all(bind=engine)
        
        # Verify table creation
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        expected_tables = ['users', 'user_base_tasks', 'schedules', 'monitoring', 'login_attempts']
        
        created_tables = [table for table in expected_tables if table in tables]
        missing_tables = [table for table in expected_tables if table not in tables]
        
        if missing_tables:
            logger.error(f"❌ Missing tables after initialization: {missing_tables}")
            return False
        
        # Initialize schema version tracking (PostgreSQL only)
        if config.env != "testing":
            try:
                with engine.connect() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS schema_versions (
                            version VARCHAR(50) PRIMARY KEY,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            description TEXT
                        )
                    """))
                    
                    current_version = os.getenv("SCHEMA_VERSION", "1.0.0")
                    conn.execute(
                        text("""
                            INSERT INTO schema_versions (version, description) 
                            VALUES (:version, :description)
                            ON CONFLICT (version) DO NOTHING
                        """),
                        {
                            "version": current_version,
                            "description": f"Initial schema for {config.env}"
                        }
                    )
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not initialize schema version tracking: {e}")
        
        logger.info(f"✅ Database initialized successfully. Created tables: {created_tables}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

def get_database_metrics() -> Dict[str, Any]:
    """
    Get current database performance metrics
    """
    return metrics.get_metrics()

# Export database inspection
def inspect_database() -> Dict[str, Any]:
    """
    Comprehensive database inspection for debugging and monitoring
    """
    try:
        inspector = inspect(engine)
        
        return {
            "tables": inspector.get_table_names(),
            "views": inspector.get_view_names(),
            "schema_info": {
                "database_url": str(engine.url).split('@')[-1],  # Mask credentials
                "environment": config.env,
                "pool_size": getattr(engine.pool, 'size', 'N/A')
            }
        }
    except Exception as e:
        logger.error(f"Database inspection failed: {e}")
        return {"error": str(e)}

logger.info(f"✅ Database module initialized for {config.env} environment")
logger.info(f"📊 Database URL: {config.url.split('@')[-1]}")
