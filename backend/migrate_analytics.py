"""
Migration script for analytics tables
Run this to create the new analytics tables without affecting existing data
"""

import sys
import logging
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import db_manager
from analytics_models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create analytics tables"""
    try:
        logger.info("=" * 80)
        logger.info("  ANALYTICS TABLES MIGRATION")
        logger.info("=" * 80)
        logger.info("")
        
        logger.info(f"Database location: {db_manager.get_db_path()}")
        logger.info("")
        
        # Create analytics tables
        logger.info("Creating analytics tables...")
        Base.metadata.create_all(bind=db_manager.engine)
        
        logger.info("✅ Analytics tables created successfully!")
        logger.info("")
        logger.info("New tables:")
        logger.info("  - predictions")
        logger.info("  - results")
        logger.info("  - prediction_results")
        logger.info("  - statistics")
        logger.info("")
        logger.info("Existing tables (conversations, messages, memories, knowledge) are unchanged.")
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