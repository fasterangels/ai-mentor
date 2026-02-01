"""
Analytics Service for Sports Betting Predictions
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging

from analytics_models import (
    Prediction, Result, PredictionResult, Statistics,
    MarketType, PredictionStatus
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for managing predictions, results, and statistics"""
    
    @staticmethod
    def create_prediction(
        db: Session,
        match_id: str,
        home_team: str,
        away_team: str,
        match_date: Optional[datetime],
        market_1x2: Optional[str] = None,
        market_1x2_prob: Optional[float] = None,
        market_over_under: Optional[str] = None,
        market_over_under_prob: Optional[float] = None,
        market_gg_nogg: Optional[str] = None,
        market_gg_nogg_prob: Optional[float] = None
    ) -> Prediction:
        """Create a new prediction"""
        prediction = Prediction(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            market_1x2=market_1x2,
            market_1x2_probability=market_1x2_prob,
            market_over_under=market_over_under,
            market_over_under_probability=market_over_under_prob,
            market_gg_nogg=market_gg_nogg,
            market_gg_nogg_probability=market_gg_nogg_prob,
            status=PredictionStatus.PENDING.value
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        logger.info(f"Created prediction for {home_team} vs {away_team}")
        return prediction
    
    @staticmethod
    def get_predictions(
        db: Session,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Prediction]:
        """Get predictions with optional status filter"""
        query = db.query(Prediction)
        
        if status:
            query = query.filter(Prediction.status == status)
        
        return query.order_by(desc(Prediction.prediction_date)).limit(limit).all()
    
    @staticmethod
    def get_prediction(db: Session, prediction_id: int) -> Optional[Prediction]:
        """Get single prediction by ID"""
        return db.query(Prediction).filter(Prediction.id == prediction_id).first()
    
    @staticmethod
    def create_result(
        db: Session,
        match_id: str,
        prediction_id: int,
        home_team: str,
        away_team: str,
        home_score: int,
        away_score: int,
        match_date: datetime
    ) -> Result:
        """Create match result and evaluate predictions"""
        # Create result
        result = Result(
            match_id=match_id,
            prediction_id=prediction_id,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            match_date=match_date
        )
        
        db.add(result)
        db.commit()
        db.refresh(result)
        
        # Get prediction
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        
        if prediction:
            # Update prediction status
            prediction.status = PredictionStatus.COMPLETED.value
            
            # Evaluate predictions
            AnalyticsService._evaluate_predictions(db, prediction, result)
            
            # Update statistics
            AnalyticsService._update_statistics(db)
            
            db.commit()
        
        logger.info(f"Created result for {home_team} {home_score}-{away_score} {away_team}")
        return result
    
    @staticmethod
    def _evaluate_predictions(db: Session, prediction: Prediction, result: Result):
        """Evaluate prediction accuracy against result"""
        # Evaluate 1X2
        if prediction.market_1x2:
            actual_1x2 = AnalyticsService._get_1x2_result(result.home_score, result.away_score)
            is_correct = prediction.market_1x2 == actual_1x2
            
            pred_result = PredictionResult(
                prediction_id=prediction.id,
                result_id=result.id,
                market_type=MarketType.ONE_X_TWO.value,
                predicted_value=prediction.market_1x2,
                actual_value=actual_1x2,
                is_correct=is_correct
            )
            db.add(pred_result)
        
        # Evaluate Over/Under
        if prediction.market_over_under:
            total_goals = result.home_score + result.away_score
            actual_ou = "Over 2.5" if total_goals > 2.5 else "Under 2.5"
            is_correct = prediction.market_over_under == actual_ou
            
            pred_result = PredictionResult(
                prediction_id=prediction.id,
                result_id=result.id,
                market_type=MarketType.OVER_UNDER.value,
                predicted_value=prediction.market_over_under,
                actual_value=actual_ou,
                is_correct=is_correct
            )
            db.add(pred_result)
        
        # Evaluate GG/NoGG
        if prediction.market_gg_nogg:
            actual_gg = "GG" if result.home_score > 0 and result.away_score > 0 else "NoGG"
            is_correct = prediction.market_gg_nogg == actual_gg
            
            pred_result = PredictionResult(
                prediction_id=prediction.id,
                result_id=result.id,
                market_type=MarketType.GG_NOGG.value,
                predicted_value=prediction.market_gg_nogg,
                actual_value=actual_gg,
                is_correct=is_correct
            )
            db.add(pred_result)
    
    @staticmethod
    def _get_1x2_result(home_score: int, away_score: int) -> str:
        """Get 1X2 result from scores"""
        if home_score > away_score:
            return "1"
        elif home_score == away_score:
            return "X"
        else:
            return "2"
    
    @staticmethod
    def _update_statistics(db: Session):
        """Update aggregated statistics"""
        # Overall statistics
        total_results = db.query(PredictionResult).count()
        correct_results = db.query(PredictionResult).filter(
            PredictionResult.is_correct == True
        ).count()
        
        overall_rate = (correct_results / total_results * 100) if total_results > 0 else 0.0
        
        overall_stat = db.query(Statistics).filter(Statistics.market_type == "Overall").first()
        if overall_stat:
            overall_stat.total_predictions = total_results
            overall_stat.correct_predictions = correct_results
            overall_stat.success_rate = overall_rate
            overall_stat.last_updated = datetime.utcnow()
        else:
            overall_stat = Statistics(
                market_type="Overall",
                total_predictions=total_results,
                correct_predictions=correct_results,
                success_rate=overall_rate
            )
            db.add(overall_stat)
        
        # Per-market statistics
        for market in [MarketType.ONE_X_TWO, MarketType.OVER_UNDER, MarketType.GG_NOGG]:
            market_total = db.query(PredictionResult).filter(
                PredictionResult.market_type == market.value
            ).count()
            
            market_correct = db.query(PredictionResult).filter(
                and_(
                    PredictionResult.market_type == market.value,
                    PredictionResult.is_correct == True
                )
            ).count()
            
            market_rate = (market_correct / market_total * 100) if market_total > 0 else 0.0
            
            market_stat = db.query(Statistics).filter(
                Statistics.market_type == market.value
            ).first()
            
            if market_stat:
                market_stat.total_predictions = market_total
                market_stat.correct_predictions = market_correct
                market_stat.success_rate = market_rate
                market_stat.last_updated = datetime.utcnow()
            else:
                market_stat = Statistics(
                    market_type=market.value,
                    total_predictions=market_total,
                    correct_predictions=market_correct,
                    success_rate=market_rate
                )
                db.add(market_stat)
        
        db.commit()
    
    @staticmethod
    def get_results(db: Session, limit: int = 100) -> List[Result]:
        """Get match results"""
        return db.query(Result).order_by(desc(Result.match_date)).limit(limit).all()
    
    @staticmethod
    def get_result(db: Session, result_id: int) -> Optional[Result]:
        """Get single result by ID"""
        return db.query(Result).filter(Result.id == result_id).first()
    
    @staticmethod
    def get_statistics(db: Session) -> List[Statistics]:
        """Get all statistics"""
        return db.query(Statistics).all()
    
    @staticmethod
    def get_statistics_by_market(db: Session, market_type: str) -> Optional[Statistics]:
        """Get statistics for specific market"""
        return db.query(Statistics).filter(Statistics.market_type == market_type).first()
    
    @staticmethod
    def get_weekly_summary(db: Session) -> Dict[str, Any]:
        """Get current week summary"""
        week_start = datetime.utcnow() - timedelta(days=7)
        
        # Get predictions from this week
        week_predictions = db.query(Prediction).filter(
            Prediction.prediction_date >= week_start
        ).all()
        
        # Get completed predictions
        completed = [p for p in week_predictions if p.status == PredictionStatus.COMPLETED.value]
        
        # Count correct predictions
        correct = 0
        for pred in completed:
            pred_results = db.query(PredictionResult).filter(
                PredictionResult.prediction_id == pred.id
            ).all()
            if pred_results and all(pr.is_correct for pr in pred_results):
                correct += 1
        
        total = len(week_predictions)
        completed_count = len(completed)
        incorrect = completed_count - correct
        success_rate = (correct / completed_count * 100) if completed_count > 0 else 0.0
        
        return {
            "total_predictions": total,
            "completed": completed_count,
            "correct": correct,
            "incorrect": incorrect,
            "success_rate": success_rate,
            "week_start": week_start.isoformat(),
            "week_end": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def compare_weekly_summaries(db: Session) -> Dict[str, Any]:
        """Compare current week with previous week"""
        current_week = AnalyticsService.get_weekly_summary(db)
        
        # Previous week
        prev_week_start = datetime.utcnow() - timedelta(days=14)
        prev_week_end = datetime.utcnow() - timedelta(days=7)
        
        prev_predictions = db.query(Prediction).filter(
            and_(
                Prediction.prediction_date >= prev_week_start,
                Prediction.prediction_date < prev_week_end
            )
        ).all()
        
        prev_completed = [p for p in prev_predictions if p.status == PredictionStatus.COMPLETED.value]
        
        prev_correct = 0
        for pred in prev_completed:
            pred_results = db.query(PredictionResult).filter(
                PredictionResult.prediction_id == pred.id
            ).all()
            if pred_results and all(pr.is_correct for pr in pred_results):
                prev_correct += 1
        
        prev_success_rate = (prev_correct / len(prev_completed) * 100) if prev_completed else 0.0
        
        # Calculate change
        rate_change = current_week["success_rate"] - prev_success_rate
        
        return {
            "current_week": current_week,
            "previous_week": {
                "total_predictions": len(prev_predictions),
                "completed": len(prev_completed),
                "correct": prev_correct,
                "success_rate": prev_success_rate
            },
            "change": {
                "success_rate_change": rate_change,
                "trend": "up" if rate_change > 0 else "down" if rate_change < 0 else "stable"
            }
        }