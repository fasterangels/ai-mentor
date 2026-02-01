"""
Analytics Models for Sports Betting Predictions
Separate file to avoid modifying existing models.py
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class MarketType(str, enum.Enum):
    """Market types for predictions"""
    ONE_X_TWO = "1X2"  # Home/Draw/Away
    OVER_UNDER = "OverUnder"  # Over/Under goals
    GG_NOGG = "GGNOGG"  # Both teams to score


class PredictionStatus(str, enum.Enum):
    """Status of predictions"""
    PENDING = "pending"
    COMPLETED = "completed"


class Prediction(Base):
    """Football match predictions"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(100), unique=True, nullable=False, index=True)
    home_team = Column(String(255), nullable=False)
    away_team = Column(String(255), nullable=False)
    prediction_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    match_date = Column(DateTime, nullable=True)
    
    # Market predictions (JSON-like storage)
    market_1x2 = Column(String(10))  # "1", "X", "2"
    market_1x2_probability = Column(Float)  # 0.0 to 100.0
    
    market_over_under = Column(String(20))  # "Over 2.5", "Under 2.5"
    market_over_under_probability = Column(Float)
    
    market_gg_nogg = Column(String(10))  # "GG", "NoGG"
    market_gg_nogg_probability = Column(Float)
    
    status = Column(String(20), default=PredictionStatus.PENDING.value)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    result = relationship("Result", back_populates="prediction", uselist=False)
    prediction_results = relationship("PredictionResult", back_populates="prediction")


class Result(Base):
    """Actual match results"""
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(100), unique=True, nullable=False, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    
    home_team = Column(String(255), nullable=False)
    away_team = Column(String(255), nullable=False)
    home_score = Column(Integer, nullable=False)
    away_score = Column(Integer, nullable=False)
    match_date = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    prediction = relationship("Prediction", back_populates="result")
    prediction_results = relationship("PredictionResult", back_populates="result")


class PredictionResult(Base):
    """Evaluation of predictions against actual results"""
    __tablename__ = "prediction_results"
    
    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    result_id = Column(Integer, ForeignKey("results.id"), nullable=False)
    
    market_type = Column(String(20), nullable=False)  # "1X2", "OverUnder", "GGNOGG"
    predicted_value = Column(String(50), nullable=False)
    actual_value = Column(String(50), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    prediction = relationship("Prediction", back_populates="prediction_results")
    result = relationship("Result", back_populates="prediction_results")


class Statistics(Base):
    """Aggregated statistics for performance tracking"""
    __tablename__ = "statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    market_type = Column(String(20), nullable=False, unique=True)  # "1X2", "OverUnder", "GGNOGG", "Overall"
    
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # 0.0 to 100.0
    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DataSource(Base):
    """Online data sources for predictions"""
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)  # fixtures, news, statistics, odds
    reliability_score = Column(Float, nullable=False)  # 1.0, 0.8, 0.6
    active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)