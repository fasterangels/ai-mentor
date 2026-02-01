from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    thinking_state = Column(String(50))  # offline, online, memory, knowledge
    used_online = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")


class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    importance = Column(Float, default=0.5)  # 0.0 to 1.0
    tags = Column(String(500))  # comma-separated tags
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Knowledge(Base):
    __tablename__ = "knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    content = Column(Text)
    tags = Column(String(500))  # comma-separated tags
    sources = Column(Text)  # JSON string of sources
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # =========================
# Analyzer / Predictions
# =========================

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    competition = Column(String(255), nullable=False)
    match_date = Column(DateTime, nullable=False)
    home_team = Column(String(255), nullable=False)
    away_team = Column(String(255), nullable=False)

    data_json = Column(Text, nullable=False)
    data_coverage = Column(Integer, default=0)

    # Probabilities
    p_home = Column(Float)
    p_draw = Column(Float)
    p_away = Column(Float)

    p_over25 = Column(Float)
    p_under25 = Column(Float)

    p_gg = Column(Float)
    p_ng = Column(Float)

    confidence = Column(Float)
    risk = Column(String(50))

    reasoning = Column(Text)
    missing = Column(Text)

    # Final picks
    pick_1x2 = Column(String(10))
    pick_ou25 = Column(String(10))
    pick_ggng = Column(String(10))

    result = relationship("MatchResult", back_populates="prediction", uselist=False)
    evaluation = relationship("Evaluation", back_populates="prediction", uselist=False)


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), unique=True)

    final_home_goals = Column(Integer)
    final_away_goals = Column(Integer)

    final_1x2 = Column(String(10))
    final_ou25 = Column(String(10))
    final_ggng = Column(String(10))

    result_date = Column(DateTime, default=datetime.utcnow)

    prediction = relationship("Prediction", back_populates="result")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), unique=True)

    hit_1x2 = Column(Boolean)
    hit_ou25 = Column(Boolean)
    hit_ggng = Column(Boolean)

    notes = Column(Text)

    evaluated_at = Column(DateTime, default=datetime.utcnow)

    prediction = relationship("Prediction", back_populates="evaluation")
