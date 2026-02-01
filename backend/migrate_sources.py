"""
Migration script for data_sources table
"""

import sys
import logging
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import db_manager
from analytics_models import Base, DataSource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create data_sources table"""
    try:
        logger.info("=" * 80)
        logger.info("  DATA SOURCES TABLE MIGRATION")
        logger.info("=" * 80)
        logger.info("")
        
        logger.info(f"Database location: {db_manager.get_db_path()}")
        logger.info("")
        
        # Create data_sources table
        logger.info("Creating data_sources table...")
        Base.metadata.create_all(bind=db_manager.engine, tables=[DataSource.__table__])
        
        logger.info("✅ data_sources table created successfully!")
        logger.info("")
        logger.info("=" * 80)
        logger.info("  MIGRATION COMPLETED")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)