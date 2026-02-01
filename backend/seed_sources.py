"""
Seed default data sources
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import db_manager
from data_sources_service import DataSourcesService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_sources():
    """Seed default data sources"""
    db = next(db_manager.get_session())
    
    try:
        logger.info("=" * 80)
        logger.info("  SEEDING DEFAULT DATA SOURCES")
        logger.info("=" * 80)
        logger.info("")
        
        default_sources = [
            # Fixtures
            {
                "name": "Football-Data.org",
                "url": "https://api.football-data.org/v4",
                "category": "fixtures",
                "reliability_score": 1.0,
                "active": True
            },
            {
                "name": "API-Football",
                "url": "https://api-football-v1.p.rapidapi.com/v3",
                "category": "fixtures",
                "reliability_score": 1.0,
                "active": False
            },
            
            # News
            {
                "name": "ESPN Soccer",
                "url": "https://www.espn.com/soccer/",
                "category": "news",
                "reliability_score": 0.8,
                "active": True
            },
            {
                "name": "BBC Sport Football",
                "url": "https://www.bbc.com/sport/football",
                "category": "news",
                "reliability_score": 0.8,
                "active": True
            },
            {
                "name": "Sky Sports Football",
                "url": "https://www.skysports.com/football",
                "category": "news",
                "reliability_score": 0.8,
                "active": False
            },
            
            # Statistics
            {
                "name": "FBref",
                "url": "https://fbref.com/",
                "category": "statistics",
                "reliability_score": 1.0,
                "active": True
            },
            {
                "name": "WhoScored",
                "url": "https://www.whoscored.com/",
                "category": "statistics",
                "reliability_score": 0.8,
                "active": False
            },
            {
                "name": "Understat",
                "url": "https://understat.com/",
                "category": "statistics",
                "reliability_score": 0.8,
                "active": False
            },
            
            # Odds
            {
                "name": "Oddsportal",
                "url": "https://www.oddsportal.com/",
                "category": "odds",
                "reliability_score": 0.8,
                "active": True
            },
            {
                "name": "Betfair",
                "url": "https://www.betfair.com/",
                "category": "odds",
                "reliability_score": 0.6,
                "active": False
            },
            {
                "name": "Bet365",
                "url": "https://www.bet365.com/",
                "category": "odds",
                "reliability_score": 0.6,
                "active": False
            }
        ]
        
        for source_data in default_sources:
            source = DataSourcesService.create_source(
                db,
                name=source_data["name"],
                url=source_data["url"],
                category=source_data["category"],
                reliability_score=source_data["reliability_score"],
                active=source_data["active"]
            )
            logger.info(f"✅ Created: {source.name} ({source.category})")
        
        logger.info("")
        logger.info(f"✅ Seeded {len(default_sources)} default data sources!")
        logger.info("")
        logger.info("=" * 80)
        logger.info("  SEEDING COMPLETED")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_sources()