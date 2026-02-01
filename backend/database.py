import os
import shutil
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine data directory
def get_data_dir() -> Path:
    """Get the data directory path from environment or use default"""
    try:
        # Check for custom DATA_DIR environment variable
        data_dir_env = os.getenv('DATA_DIR')
        if data_dir_env:
            data_dir = Path(data_dir_env)
            logger.info(f"Using custom DATA_DIR from environment: {data_dir}")
        else:
            # Default: User home directory / AI_Mentor_Data
            home = Path.home()
            data_dir = home / 'AI_Mentor_Data'
            logger.info(f"Using default data directory: {data_dir}")
        
        # Create directory if it doesn't exist
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Data directory ready: {data_dir}")
        
        return data_dir
    except Exception as e:
        logger.error(f"Failed to create data directory: {e}")
        # Fallback to current directory
        fallback_dir = Path.cwd() / 'data'
        fallback_dir.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Using fallback directory: {fallback_dir}")
        return fallback_dir

# Get database path
DATA_DIR = get_data_dir()
DB_PATH = DATA_DIR / 'ai_mentor.db'
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Migration: Check for old database in project directory
def migrate_old_database():
    """Migrate old database from project directory to new data folder"""
    try:
        old_db_path = Path(__file__).parent / 'ai_mentor.db'
        
        if old_db_path.exists() and not DB_PATH.exists():
            logger.info(f"[Migration] Found old database at {old_db_path}")
            logger.info(f"[Migration] Migrating to {DB_PATH}")
            
            try:
                shutil.copy2(old_db_path, DB_PATH)
                logger.info(f"[Migration] Successfully migrated database to {DB_PATH}")
                logger.info(f"[Migration] Old database kept at {old_db_path} (you can delete it manually)")
            except Exception as e:
                logger.error(f"[Migration] Error during migration: {e}")
                logger.info(f"[Migration] Will create new database at {DB_PATH}")
        elif old_db_path.exists() and DB_PATH.exists():
            logger.info(f"[Migration] Both old and new databases exist. Using new database at {DB_PATH}")
            logger.info(f"[Migration] Old database at {old_db_path} is not used (safe to delete)")
        else:
            logger.debug("[Migration] No old database found, using new location")
    except Exception as e:
        logger.error(f"[Migration] Unexpected error during migration check: {e}")

# Run migration check on import
migrate_old_database()

Base = declarative_base()


class DatabaseManager:
    """Single database manager for the entire application"""
    
    _instance = None
    _engine = None
    _SessionLocal = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize database engine and session factory"""
        try:
            logger.info(f"[Database] Initializing database at: {DB_PATH}")
            logger.info(f"[Database] Data directory: {DATA_DIR}")
            
            self._engine = create_engine(
                DATABASE_URL,
                connect_args={"check_same_thread": False},
                echo=False,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600    # Recycle connections after 1 hour
            )
            self._SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine
            )
            
            logger.info("[Database] Database engine initialized successfully")
        except Exception as e:
            logger.error(f"[Database] Failed to initialize database: {e}")
            raise
    
    def create_tables(self):
        """Create all tables in the database"""
        try:
            Base.metadata.create_all(bind=self._engine)
            logger.info(f"[Database] Tables created/verified at {DB_PATH}")
        except Exception as e:
            logger.error(f"[Database] Failed to create tables: {e}")
            raise
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session"""
        db = self._SessionLocal()
        try:
            yield db
        except Exception as e:
            logger.error(f"[Database] Session error: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    @property
    def engine(self):
        return self._engine
    
    def get_db_path(self) -> Path:
        """Get the current database file path"""
        return DB_PATH
    
    def get_data_dir(self) -> Path:
        """Get the data directory path"""
        return DATA_DIR


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI routes"""
    yield from db_manager.get_session()