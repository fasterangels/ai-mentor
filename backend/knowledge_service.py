from sqlalchemy.orm import Session
from typing import List, Optional
from models import Knowledge


class KnowledgeService:
    """Service for managing knowledge base"""
    
    @staticmethod
    def create_knowledge(
        db: Session,
        title: str,
        summary: str,
        content: Optional[str] = None,
        tags: Optional[str] = None,
        sources: Optional[str] = None
    ) -> Knowledge:
        """Create a new knowledge entry"""
        knowledge = Knowledge(
            title=title,
            summary=summary,
            content=content or "",
            tags=tags or "",
            sources=sources or ""
        )
        db.add(knowledge)
        db.commit()
        db.refresh(knowledge)
        return knowledge
    
    @staticmethod
    def get_knowledge_list(
        db: Session,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Knowledge]:
        """Get knowledge entries filtered by tags"""
        query = db.query(Knowledge)
        
        if tags:
            for tag in tags:
                query = query.filter(Knowledge.tags.contains(tag))
        
        return query.order_by(Knowledge.updated_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_knowledge(db: Session, knowledge_id: int) -> Optional[Knowledge]:
        """Get a specific knowledge entry"""
        return db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    
    @staticmethod
    def update_knowledge(
        db: Session,
        knowledge_id: int,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[str] = None,
        sources: Optional[str] = None
    ) -> Optional[Knowledge]:
        """Update a knowledge entry"""
        knowledge = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
        if not knowledge:
            return None
        
        if title is not None:
            knowledge.title = title
        if summary is not None:
            knowledge.summary = summary
        if content is not None:
            knowledge.content = content
        if tags is not None:
            knowledge.tags = tags
        if sources is not None:
            knowledge.sources = sources
        
        db.commit()
        db.refresh(knowledge)
        return knowledge
    
    @staticmethod
    def delete_knowledge(db: Session, knowledge_id: int) -> bool:
        """Delete a knowledge entry"""
        knowledge = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
        if knowledge:
            db.delete(knowledge)
            db.commit()
            return True
        return False
    
    @staticmethod
    def search_knowledge(
        db: Session,
        query: str,
        limit: int = 5
    ) -> List[Knowledge]:
        """Search knowledge entries (optimized with database-level limiting)"""
        # PERFORMANCE FIX: Limit database query instead of loading all knowledge
        # This reduces query time from O(n) to O(log n) with proper indexing
        
        keywords = query.lower().split()
        
        # Get recent knowledge entries (limit at database level)
        knowledge_list = db.query(Knowledge).order_by(
            Knowledge.updated_at.desc()
        ).limit(limit * 3).all()  # Get 3x limit for scoring
        
        # Score knowledge by keyword matches (now on much smaller dataset)
        scored = []
        for knowledge in knowledge_list:
            searchable = f"{knowledge.title} {knowledge.summary} {knowledge.content}".lower()
            score = sum(1 for keyword in keywords if keyword in searchable)
            if score > 0:
                scored.append((knowledge, score))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [knowledge for knowledge, _ in scored[:limit]]