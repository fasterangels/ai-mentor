from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from models import Conversation, Message


class ConversationService:
    """Service for managing conversations"""
    
    @staticmethod
    def create_conversation(db: Session, title: str) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation
    
    @staticmethod
    def get_conversations(db: Session, limit: int = 50) -> List[Conversation]:
        """Get all conversations ordered by updated_at"""
        return db.query(Conversation).order_by(
            Conversation.updated_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
        """Get a specific conversation"""
        return db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
    
    @staticmethod
    def delete_conversation(db: Session, conversation_id: int) -> bool:
        """Delete a conversation"""
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            db.delete(conversation)
            db.commit()
            return True
        return False
    
    @staticmethod
    def add_message(
        db: Session,
        conversation_id: int,
        role: str,
        content: str,
        thinking_state: Optional[str] = None,
        used_online: bool = False
    ) -> Message:
        """Add a message to a conversation"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            thinking_state=thinking_state,
            used_online=used_online
        )
        db.add(message)
        
        # Update conversation timestamp
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        return message
    
    @staticmethod
    def get_messages(
        db: Session,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get messages for a conversation"""
        query = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_recent_messages(
        db: Session,
        conversation_id: int,
        count: int = 10
    ) -> List[Message]:
        """Get recent messages for context"""
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(count).all()
        
        return list(reversed(messages))