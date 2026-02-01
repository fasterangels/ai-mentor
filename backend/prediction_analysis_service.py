"""
Prediction Analysis Service
Implements clear logic for match predictions with online/offline separation
"""

import logging
from typing import Dict, Optional, Tuple, Any
from datetime import datetime
from sqlalchemy.orm import Session

from data_collector import data_collector
from analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class PredictionAnalysisService:
    """
    Handles prediction analysis with clear online/offline separation
    
    ONLINE PHASE: Data collection
    OFFLINE PHASE: Analysis, weighting, decision
    """
    
    # Weighting factors
    WEIGHTS = {
        'form': 0.30,
        'h2h': 0.20,
        'home_away': 0.25,
        'goals': 0.25
    }
    
    HOME_ADVANTAGE = 12.5  # Home advantage percentage
    MIN_CONFIDENCE_DIFF = 10.0  # Minimum difference for confident prediction
    
    @staticmethod
    def collect_online_data(
        home_team: str,
        away_team: str
    ) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
        """
        ONLINE PHASE: Collect data from reliable sources
        
        Returns:
            Tuple of (home_data, away_data, h2h_data) or (None, None, None) if unavailable
        """
        logger.info(f"[ONLINE] Collecting data for {home_team} vs {away_team}")
        
        # Check if data collection is available
        if not data_collector.is_data_available():
            logger.warning("[ONLINE] Data collection not available (no API key)")
            return None, None, None
        
        # Collect team data
        home_data = data_collector.collect_team_data(home_team)
        away_data = data_collector.collect_team_data(away_team)
        h2h_data = data_collector.collect_match_data(home_team, away_team)
        
        if not home_data or not away_data:
            logger.warning(f"[ONLINE] Insufficient data for {home_team} vs {away_team}")
            return None, None, None
        
        logger.info("[ONLINE] Data collection successful")
        return home_data, away_data, h2h_data
    
    @staticmethod
    def _calculate_form_score(recent_matches: list) -> float:
        """
        Calculate form score from recent matches (0-100)
        
        Args:
            recent_matches: List of recent match results (W/D/L)
        
        Returns:
            Form score (0-100)
        """
        if not recent_matches:
            return 50.0  # Neutral
        
        points = {'W': 10, 'D': 5, 'L': 0}
        total_points = sum(points.get(result, 0) for result in recent_matches)
        max_points = len(recent_matches) * 10
        
        return (total_points / max_points) * 100
    
    @staticmethod
    def calculate_1x2_probabilities(
        home_data: Dict,
        away_data: Dict,
        h2h_data: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        OFFLINE PHASE: Calculate 1/X/2 probabilities
        
        Args:
            home_data: Home team statistics
            away_data: Away team statistics
            h2h_data: Head-to-head data (optional)
        
        Returns:
            Dict with probabilities for '1', 'X', '2'
        """
        logger.info("[OFFLINE] Calculating 1/X/2 probabilities")
        
        # Calculate form scores
        home_form = PredictionAnalysisService._calculate_form_score(
            home_data.get('recent_form', [])
        )
        away_form = PredictionAnalysisService._calculate_form_score(
            away_data.get('recent_form', [])
        )
        
        # Home advantage
        home_advantage = PredictionAnalysisService.HOME_ADVANTAGE
        
        # H2H factor (if available)
        h2h_factor = 0
        if h2h_data:
            home_wins = h2h_data.get('home_wins', 0)
            total_matches = h2h_data.get('total_matches', 1)
            h2h_factor = (home_wins / total_matches - 0.5) * 20  # -10 to +10
        
        # Calculate raw probabilities
        home_prob = (
            home_form * PredictionAnalysisService.WEIGHTS['form'] +
            home_advantage +
            h2h_factor * PredictionAnalysisService.WEIGHTS['h2h']
        )
        
        away_prob = (
            away_form * PredictionAnalysisService.WEIGHTS['form'] +
            abs(h2h_factor) * PredictionAnalysisService.WEIGHTS['h2h']
        )
        
        draw_prob = 100 - home_prob - away_prob
        
        # Normalize to 100%
        total = home_prob + draw_prob + away_prob
        
        result = {
            '1': round(home_prob / total * 100, 1),
            'X': round(draw_prob / total * 100, 1),
            '2': round(away_prob / total * 100, 1)
        }
        
        logger.info(f"[OFFLINE] 1/X/2 probabilities: {result}")
        return result
    
    @staticmethod
    def calculate_over_under_probabilities(
        home_data: Dict,
        away_data: Dict
    ) -> Dict[str, float]:
        """
        OFFLINE PHASE: Calculate Over/Under 2.5 probabilities
        
        Args:
            home_data: Home team statistics
            away_data: Away team statistics
        
        Returns:
            Dict with probabilities for 'Over 2.5', 'Under 2.5'
        """
        logger.info("[OFFLINE] Calculating Over/Under probabilities")
        
        # Average goals
        home_avg_scored = home_data.get('avg_goals_scored', 1.5)
        away_avg_scored = away_data.get('avg_goals_scored', 1.5)
        home_avg_conceded = home_data.get('avg_goals_conceded', 1.5)
        away_avg_conceded = away_data.get('avg_goals_conceded', 1.5)
        
        # Expected total goals
        expected_goals = (
            home_avg_scored + away_avg_scored +
            home_avg_conceded + away_avg_conceded
        ) / 2
        
        # Calculate probabilities
        if expected_goals > 2.5:
            over_prob = min(55 + (expected_goals - 2.5) * 10, 85)
        else:
            over_prob = max(45 - (2.5 - expected_goals) * 10, 15)
        
        result = {
            'Over 2.5': round(over_prob, 1),
            'Under 2.5': round(100 - over_prob, 1)
        }
        
        logger.info(f"[OFFLINE] Over/Under probabilities: {result}")
        return result
    
    @staticmethod
    def calculate_gg_probabilities(
        home_data: Dict,
        away_data: Dict
    ) -> Dict[str, float]:
        """
        OFFLINE PHASE: Calculate GG/NoGG probabilities
        
        Args:
            home_data: Home team statistics
            away_data: Away team statistics
        
        Returns:
            Dict with probabilities for 'GG', 'NoGG'
        """
        logger.info("[OFFLINE] Calculating GG/NoGG probabilities")
        
        # Both teams scoring rate
        home_gg_rate = home_data.get('both_scored_rate', 0.5)
        away_gg_rate = away_data.get('both_scored_rate', 0.5)
        
        # Average GG rate
        avg_gg_rate = (home_gg_rate + away_gg_rate) / 2
        
        result = {
            'GG': round(avg_gg_rate * 100, 1),
            'NoGG': round((1 - avg_gg_rate) * 100, 1)
        }
        
        logger.info(f"[OFFLINE] GG/NoGG probabilities: {result}")
        return result
    
    @staticmethod
    def get_best_prediction(probabilities: Dict[str, float]) -> Tuple[str, float]:
        """
        Get the best prediction from probabilities
        
        Returns:
            Tuple of (prediction, probability)
        """
        best = max(probabilities.items(), key=lambda x: x[1])
        return best[0], best[1]
    
    @staticmethod
    def is_confident_prediction(probabilities: Dict[str, float]) -> bool:
        """
        Check if prediction is confident (difference > MIN_CONFIDENCE_DIFF)
        
        Returns:
            True if confident, False otherwise
        """
        sorted_probs = sorted(probabilities.values(), reverse=True)
        if len(sorted_probs) < 2:
            return False
        
        diff = sorted_probs[0] - sorted_probs[1]
        return diff >= PredictionAnalysisService.MIN_CONFIDENCE_DIFF
    
    @staticmethod
    def generate_prediction_explanation(
        home_team: str,
        away_team: str,
        home_data: Dict,
        away_data: Dict,
        prediction_1x2: Tuple[str, float],
        prediction_ou: Tuple[str, float],
        prediction_gg: Tuple[str, float]
    ) -> str:
        """
        Generate concise explanation for predictions
        
        Returns:
            Explanation string (2-4 bullet points)
        """
        explanation_parts = []
        
        # 1X2 explanation
        pred_1x2, prob_1x2 = prediction_1x2
        explanation_parts.append(f"**Πρόβλεψη 1/X/2:** {pred_1x2} ({prob_1x2}%)")
        
        # Form comparison
        home_form = PredictionAnalysisService._calculate_form_score(
            home_data.get('recent_form', [])
        )
        away_form = PredictionAnalysisService._calculate_form_score(
            away_data.get('recent_form', [])
        )
        explanation_parts.append(
            f"- Φόρμα: {home_team} ({home_form:.0f}/100) vs {away_team} ({away_form:.0f}/100)"
        )
        
        # Home advantage
        if pred_1x2 == '1':
            explanation_parts.append(
                f"- Έδρα: {home_team} έχει πλεονέκτημα έδρας (+{PredictionAnalysisService.HOME_ADVANTAGE}%)"
            )
        
        # Goals
        home_avg = home_data.get('avg_goals_scored', 1.5)
        away_avg = away_data.get('avg_goals_scored', 1.5)
        explanation_parts.append(
            f"- Γκολ: {home_team} ({home_avg:.1f}/αγώνα), {away_team} ({away_avg:.1f}/αγώνα)"
        )
        
        # Over/Under explanation
        pred_ou, prob_ou = prediction_ou
        explanation_parts.append(f"\n**Πρόβλεψη Over/Under:** {pred_ou} ({prob_ou}%)")
        
        # GG/NoGG explanation
        pred_gg, prob_gg = prediction_gg
        explanation_parts.append(f"**Πρόβλεψη GG/NoGG:** {pred_gg} ({prob_gg}%)")
        
        return "\n".join(explanation_parts)
    
    @staticmethod
    def create_prediction_with_analysis(
        db: Session,
        home_team: str,
        away_team: str,
        match_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create prediction with full analysis (online + offline)
        
        Returns:
            Dict with prediction data and explanation, or error message
        """
        logger.info(f"Creating prediction for {home_team} vs {away_team}")
        
        # ONLINE PHASE: Collect data
        home_data, away_data, h2h_data = PredictionAnalysisService.collect_online_data(
            home_team, away_team
        )
        
        # Check if data is available
        if not home_data or not away_data:
            error_msg = (
                f"❌ Δεν υπάρχουν διαθέσιμα δεδομένα για αυτόν τον αγώνα.\n\n"
                f"Για να χρησιμοποιήσετε την online συλλογή δεδομένων:\n"
                f"1. Αποκτήστε API key από https://www.football-data.org/\n"
                f"2. Ορίστε το API key στο σύστημα\n\n"
                f"Προς το παρόν, μπορείτε να δημιουργήσετε προβλέψεις χειροκίνητα "
                f"μέσω του API endpoint."
            )
            logger.warning(error_msg)
            return {"error": error_msg}
        
        # OFFLINE PHASE: Calculate probabilities
        probs_1x2 = PredictionAnalysisService.calculate_1x2_probabilities(
            home_data, away_data, h2h_data
        )
        probs_ou = PredictionAnalysisService.calculate_over_under_probabilities(
            home_data, away_data
        )
        probs_gg = PredictionAnalysisService.calculate_gg_probabilities(
            home_data, away_data
        )
        
        # Get best predictions
        pred_1x2 = PredictionAnalysisService.get_best_prediction(probs_1x2)
        pred_ou = PredictionAnalysisService.get_best_prediction(probs_ou)
        pred_gg = PredictionAnalysisService.get_best_prediction(probs_gg)
        
        # Check confidence
        confident_1x2 = PredictionAnalysisService.is_confident_prediction(probs_1x2)
        confident_ou = PredictionAnalysisService.is_confident_prediction(probs_ou)
        confident_gg = PredictionAnalysisService.is_confident_prediction(probs_gg)
        
        # Generate explanation
        explanation = PredictionAnalysisService.generate_prediction_explanation(
            home_team, away_team, home_data, away_data,
            pred_1x2, pred_ou, pred_gg
        )
        
        # Create prediction in database
        match_id = f"match_{home_team}_{away_team}_{datetime.utcnow().timestamp()}"
        
        prediction = AnalyticsService.create_prediction(
            db,
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            market_1x2=pred_1x2[0] if confident_1x2 else None,
            market_1x2_prob=pred_1x2[1] if confident_1x2 else None,
            market_over_under=pred_ou[0] if confident_ou else None,
            market_over_under_prob=pred_ou[1] if confident_ou else None,
            market_gg_nogg=pred_gg[0] if confident_gg else None,
            market_gg_nogg_prob=pred_gg[1] if confident_gg else None
        )
        
        return {
            "prediction": prediction,
            "explanation": explanation,
            "confidence": {
                "1x2": "High" if confident_1x2 else "Low",
                "over_under": "High" if confident_ou else "Low",
                "gg_nogg": "High" if confident_gg else "Low"
            },
            "all_probabilities": {
                "1x2": probs_1x2,
                "over_under": probs_ou,
                "gg_nogg": probs_gg
            }
        }