"""
Base model class for all SQLAlchemy models in the vet-core package.

This module provides the base model class that all other models inherit from,
including common fields and functionality.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

# Type variable for model classes
ModelType = TypeVar("ModelType", bound="BaseModel")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    # Use UUID type for PostgreSQL
    type_annotation_map = {
        uuid.UUID: UUID(as_uuid=True),
    }


class BaseModel(Base):
    """
    Base model class with common fields and functionality.
    
    Provides:
    - UUID primary key
    - Audit fields (created_at, updated_at, created_by, updated_by)
    - Soft delete capability (deleted_at, is_deleted)
    - Common query methods and utilities
    """
    
    __abstract__ = True
    
    # Primary key - UUID for distributed systems
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    
    # Soft delete fields
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self, exclude_deleted: bool = True) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Args:
            exclude_deleted: Whether to exclude soft-deleted records
            
        Returns:
            Dictionary representation of the model
        """
        if exclude_deleted and self.is_deleted:
            return {}
            
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                result[column.name] = str(value)
            else:
                result[column.name] = value
        return result
    
    def soft_delete(self, deleted_by: Optional[uuid.UUID] = None) -> None:
        """
        Perform soft delete on the model instance.
        
        Args:
            deleted_by: UUID of the user performing the deletion
        """
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        if deleted_by:
            self.updated_by = deleted_by
    
    def restore(self, restored_by: Optional[uuid.UUID] = None) -> None:
        """
        Restore a soft-deleted model instance.
        
        Args:
            restored_by: UUID of the user performing the restoration
        """
        self.is_deleted = False
        self.deleted_at = None
        if restored_by:
            self.updated_by = restored_by
    
    @classmethod
    def get_table_name(cls) -> str:
        """Get the table name for this model."""
        return cls.__tablename__
    
    @classmethod
    def get_primary_key_column(cls) -> str:
        """Get the primary key column name."""
        return "id"
    
    @classmethod
    def create_query_filter_active(cls):
        """Create a filter for active (non-deleted) records."""
        return cls.is_deleted == False
    
    @classmethod
    def create_query_filter_deleted(cls):
        """Create a filter for deleted records."""
        return cls.is_deleted == True
    
    def update_fields(self, **kwargs) -> None:
        """
        Update multiple fields on the model instance.
        
        Args:
            **kwargs: Field names and values to update
        """
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
            else:
                raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{field}'")