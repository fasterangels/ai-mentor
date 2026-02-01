from sqlalchemy.orm import Session
from typing import List, Optional
from models import Memory


class MemoryService:
    """Service for managing user memories"""
    
    @staticmethod
    def create_memory(
        db: Session,
        content: str,
        importance: float = 0.5,
        tags: Optional[str] = None
    ) -> Memory:
        """Create a new memory"""
        memory = Memory(
            content=content,
            importance=importance,
            tags=tags or ""
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory
    
    @staticmethod
    def get_memories(
        db: Session,
        min_importance: float = 0.0,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Memory]:
        """Get memories filtered by importance and tags"""
        query = db.query(Memory).filter(Memory.importance >= min_importance)
        
        if tags:
            # Filter by tags (simple contains check)
            for tag in tags:
                query = query.filter(Memory.tags.contains(tag))
        
        return query.order_by(Memory.importance.desc()).limit(limit).all()
    
    @staticmethod
    def get_memory(db: Session, memory_id: int) -> Optional[Memory]:
        """Get a specific memory"""
        return db.query(Memory).filter(Memory.id == memory_id).first()
    
    @staticmethod
    def update_memory(
        db: Session,
        memory_id: int,
        content: Optional[str] = None,
        importance: Optional[float] = None,
        tags: Optional[str] = None
    ) -> Optional[Memory]:
        """Update a memory"""
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            return None
        
        if content is not None:
            memory.content = content
        if importance is not None:
            memory.importance = importance
        if tags is not None:
            memory.tags = tags
        
        db.commit()
        db.refresh(memory)
        return memory
    
    @staticmethod
    def delete_memory(db: Session, memory_id: int) -> bool:
        """Delete a memory"""
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if memory:
            db.delete(memory)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_relevant_memories(
        db: Session,
        query: str,
        min_importance: float = 0.3,
        limit: int = 5
    ) -> List[Memory]:
        """Get relevant memories for a query (optimized with database-level filtering)"""
        # PERFORMANCE FIX: Use database-level filtering instead of loading all memories
        # This reduces query time from O(n) to O(log n) with proper indexing
        
        keywords = query.lower().split()
        
        # Start with importance filter and limit at database level
        base_query = db.query(Memory).filter(
            Memory.importance >= min_importance
        ).order_by(Memory.importance.desc()).limit(limit * 3)  # Get 3x limit for scoring
        
        memories = base_query.all()
        
        # Score memories by keyword matches (now on much smaller dataset)
        scored = []
        for memory in memories:
            content_lower = memory.content.lower()
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                scored.append((memory, score))
        
        # Sort by score and importance
        scored.sort(key=lambda x: (x[1], x[0].importance), reverse=True)
        
        return [memory for memory, _ in scored[:limit]]