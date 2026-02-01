"""
Seed data for analytics tables
Creates sample predictions and results for testing
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import db_manager
from analytics_models import Base
from analytics_service import AnalyticsService
import random


def seed_analytics_data():
    """Seed sample predictions and results"""
    # Create analytics tables
    Base.metadata.create_all(bind=db_manager.engine)
    
    # Get database session
    db = next(db_manager.get_session())
    
    try:
        # Sample teams
        teams = [
            ("Manchester United", "Liverpool"),
            ("Barcelona", "Real Madrid"),
            ("Bayern Munich", "Borussia Dortmund"),
            ("PSG", "Marseille"),
            ("Juventus", "AC Milan"),
            ("Chelsea", "Arsenal"),
            ("Atletico Madrid", "Sevilla"),
            ("Inter Milan", "Napoli")
        ]
        
        # Create predictions for the past 2 weeks
        predictions = []
        for i in range(10):
            home, away = random.choice(teams)
            match_date = datetime.utcnow() - timedelta(days=random.randint(0, 14))
            
            # Random predictions
            market_1x2_options = ["1", "X", "2"]
            market_1x2 = random.choice(market_1x2_options)
            market_1x2_prob = random.uniform(40, 80)
            
            market_ou_options = ["Over 2.5", "Under 2.5"]
            market_ou = random.choice(market_ou_options)
            market_ou_prob = random.uniform(45, 75)
            
            market_gg_options = ["GG", "NoGG"]
            market_gg = random.choice(market_gg_options)
            market_gg_prob = random.uniform(50, 80)
            
            prediction = AnalyticsService.create_prediction(
                db,
                match_id=f"match_{i+1}",
                home_team=home,
                away_team=away,
                match_date=match_date,
                market_1x2=market_1x2,
                market_1x2_prob=market_1x2_prob,
                market_over_under=market_ou,
                market_over_under_prob=market_ou_prob,
                market_gg_nogg=market_gg,
                market_gg_nogg_prob=market_gg_prob
            )
            predictions.append(prediction)
            
            print(f"Created prediction {i+1}: {home} vs {away}")
        
        # Create results for 7 predictions (leaving 3 pending)
        for i in range(7):
            pred = predictions[i]
            
            # Random scores
            home_score = random.randint(0, 4)
            away_score = random.randint(0, 4)
            
            result = AnalyticsService.create_result(
                db,
                match_id=pred.match_id,
                prediction_id=pred.id,
                home_team=pred.home_team,
                away_team=pred.away_team,
                home_score=home_score,
                away_score=away_score,
                match_date=pred.match_date or datetime.utcnow()
            )
            
            print(f"Created result {i+1}: {pred.home_team} {home_score}-{away_score} {pred.away_team}")
        
        print("\n✅ Analytics data seeded successfully!")
        print(f"Created {len(predictions)} predictions")
        print(f"Created 7 results (3 predictions pending)")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_analytics_data()