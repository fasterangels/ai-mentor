"""
Data Sources Service
Manages online data sources for predictions
"""

import logging
from sqlalchemy.orm import Session
from typing import List, Optional
from analytics_models import DataSource

logger = logging.getLogger(__name__)


class DataSourcesService:
    """Service for managing data sources"""
    
    VALID_CATEGORIES = ["fixtures", "news", "statistics", "odds"]
    VALID_RELIABILITY_SCORES = [1.0, 0.8, 0.6]
    
    @staticmethod
    def get_sources(
        db: Session,
        category: Optional[str] = None,
        active_only: bool = False
    ) -> List[DataSource]:
        """Get all data sources, optionally filtered"""
        query = db.query(DataSource)
        
        if category:
            query = query.filter(DataSource.category == category)
        
        if active_only:
            query = query.filter(DataSource.active == True)
        
        return query.order_by(DataSource.category, DataSource.name).all()
    
    @staticmethod
    def get_source(db: Session, source_id: int) -> Optional[DataSource]:
        """Get a specific data source"""
        return db.query(DataSource).filter(DataSource.id == source_id).first()
    
    @staticmethod
    def create_source(
        db: Session,
        name: str,
        url: str,
        category: str,
        reliability_score: float,
        active: bool = True
    ) -> DataSource:
        """Create a new data source"""
        # Validate category
        if category not in DataSourcesService.VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {DataSourcesService.VALID_CATEGORIES}")
        
        # Validate reliability score
        if reliability_score not in DataSourcesService.VALID_RELIABILITY_SCORES:
            raise ValueError(f"Invalid reliability score. Must be one of: {DataSourcesService.VALID_RELIABILITY_SCORES}")
        
        source = DataSource(
            name=name,
            url=url,
            category=category,
            reliability_score=reliability_score,
            active=active
        )
        
        db.add(source)
        db.commit()
        db.refresh(source)
        
        logger.info(f"Created data source: {name} ({category})")
        return source
    
    @staticmethod
    def update_source(
        db: Session,
        source_id: int,
        name: Optional[str] = None,
        url: Optional[str] = None,
        category: Optional[str] = None,
        reliability_score: Optional[float] = None,
        active: Optional[bool] = None
    ) -> Optional[DataSource]:
        """Update a data source"""
        source = db.query(DataSource).filter(DataSource.id == source_id).first()
        
        if not source:
            return None
        
        if name is not None:
            source.name = name
        
        if url is not None:
            source.url = url
        
        if category is not None:
            if category not in DataSourcesService.VALID_CATEGORIES:
                raise ValueError(f"Invalid category. Must be one of: {DataSourcesService.VALID_CATEGORIES}")
            source.category = category
        
        if reliability_score is not None:
            if reliability_score not in DataSourcesService.VALID_RELIABILITY_SCORES:
                raise ValueError(f"Invalid reliability score. Must be one of: {DataSourcesService.VALID_RELIABILITY_SCORES}")
            source.reliability_score = reliability_score
        
        if active is not None:
            source.active = active
        
        db.commit()
        db.refresh(source)
        
        logger.info(f"Updated data source: {source.name}")
        return source
    
    @staticmethod
    def delete_source(db: Session, source_id: int) -> bool:
        """Delete a data source"""
        source = db.query(DataSource).filter(DataSource.id == source_id).first()
        
        if not source:
            return False
        
        db.delete(source)
        db.commit()
        
        logger.info(f"Deleted data source: {source.name}")
        return True
    
    @staticmethod
    def toggle_active(db: Session, source_id: int) -> Optional[DataSource]:
        """Toggle active status of a data source"""
        source = db.query(DataSource).filter(DataSource.id == source_id).first()
        
        if not source:
            return None
        
        source.active = not source.active
        db.commit()
        db.refresh(source)
        
        logger.info(f"Toggled data source: {source.name} -> {'active' if source.active else 'inactive'}")
        return source