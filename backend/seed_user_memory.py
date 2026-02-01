"""
Seed User Memory
Ensures user name (Σάκης) and language rules are stored in database
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import db_manager
from memory_service import MemoryService
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_user_memory():
    """Seed user memory with name and language rules"""
    try:
        logger.info("=" * 80)
        logger.info("  SEEDING USER MEMORY")
        logger.info("=" * 80)
        logger.info("")
        
        db = next(db_manager.get_session())
        
        # Check if memories already exist
        result = db.execute(text('SELECT COUNT(*) FROM memories WHERE content LIKE "%Σάκης%"')).fetchone()
        if result[0] > 0:
            logger.info("✅ User memory already exists")
            db.close()
            return
        
        # Add user name memory
        memory_service = MemoryService(db)
        memory_service.add_memory(
            content="Το όνομά μου είναι Σάκης",
            category="user_info",
            importance=10
        )
        logger.info("✅ Added user name memory: Σάκης")
        
        # Add language rules memory
        memory_service.add_memory(
            content="Θέλω να μου μιλάς: Απλά, καθαρά ελληνικά. Χωρίς φλυαρία. Χωρίς προσφωνήσεις.",
            category="preferences",
            importance=10
        )
        logger.info("✅ Added language rules memory")
        
        db.commit()
        db.close()
        
        logger.info("")
        logger.info("✅ User memory seeded successfully")
        logger.info("")
        logger.info("=" * 80)
        logger.info("  SEEDING COMPLETED")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Error seeding user memory: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    seed_user_memory()