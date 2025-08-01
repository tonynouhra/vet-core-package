"""
Base model class for all SQLAlchemy models in the vet-core package.

This module provides the foundational base model class that all other models inherit from,
including common fields, audit functionality, soft delete capabilities, and utility methods.

The BaseModel class follows modern SQLAlchemy 2.0 patterns with:
- UUID primary keys for distributed system compatibility
- Automatic timestamp management for audit trails
- Soft delete functionality to preserve data integrity
- Common utility methods for data conversion and querying

Example:
    >>> from vet_core.models.base import BaseModel
    >>> from sqlalchemy.orm import Mapped, mapped_column
    >>> from sqlalchemy import String

    >>> class MyModel(BaseModel):
    ...     __tablename__ = "my_table"
    ...     name: Mapped[str] = mapped_column(String(100))

    >>> # Create instance
    >>> instance = MyModel(name="Test")
    >>> print(instance.id)  # Auto-generated UUID
    >>> print(instance.created_at)  # Auto-set timestamp

    >>> # Soft delete
    >>> instance.soft_delete()
    >>> print(instance.is_deleted)  # True

    >>> # Convert to dictionary
    >>> data = instance.to_dict()
    >>> print(data['name'])  # "Test"
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, TypeVar, cast

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import CHAR, TypeDecorator, TypeEngine

# Type variable for model classes
T = TypeVar("T", bound="BaseModel")


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available, otherwise uses CHAR(36)
    for SQLite and other databases.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """
        Load and return an appropriate type implementation for the dialect.

        Based on the database in use. This method provides support for different
        database systems by specifying the type descriptor accordingly.

        Args:
            dialect (Dialect): The SQL dialect being used.

        Returns:
            TypeEngine[Any]: A type engine specific to the provided dialect.
        """
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Optional[str]:
        """
        Process the parameter to be bound to a SQL query, converting it to a string.

        Representation suitable for the specified SQL dialect. It ensures the parameter
        is correctly formatted as a UUID or string, depending on the dialect and input.

        Parameters:
        value (Any): The value to process, which might be a UUID instance, a string
                     representing a UUID, or None.
        dialect (Dialect): The SQL dialect to which the processed value will be bound.

        Returns:
        Optional[str]: The processed string representation of the value if conversion
                       occurs, or the value itself if no processing is required.
        """
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Optional[uuid.UUID]:
        """
        Process the result value retrieved from the database and ensure it is a valid UUID.

        If the value is already a UUID, it will be returned as-is. If the value is None, it returns None. Otherwise, it
        attempts to convert the value to a UUID.

        Params:
            value: Any
                The value to be processed. This can be of any type.
            dialect: Dialect
                SQL dialect in use. Used here for method signature compatibility, but not actively utilized.

        Returns:
            Optional[uuid.UUID]: A UUID object if the value is valid and convertible, or None if the value
            was None.
        """
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


class Base(DeclarativeBase):
    """
    Base declarative class for all SQLAlchemy models.

    Configures the SQLAlchemy declarative base with cross-database
    type mappings, particularly for UUID fields.

    Attributes:
        type_annotation_map: Maps Python types to SQLAlchemy column types
    """

    # Use cross-database compatible UUID type
    type_annotation_map = {
        uuid.UUID: GUID(),
    }


class BaseModel(Base):
    """
    Abstract base model class providing common functionality for all entities.

    This class provides a standardized foundation for all database models in the
    veterinary clinic platform, including:

    - **UUID Primary Keys**: Uses UUID4 for distributed system compatibility
    - **Audit Fields**: Automatic tracking of creation and modification times/users
    - **Soft Delete**: Preserves data integrity by marking records as deleted
    - **Utility Methods**: Common operations like dictionary conversion and filtering

    All models inheriting from BaseModel automatically get these features without
    additional configuration.

    Attributes:
        id (UUID): Primary key, automatically generated UUID4
        created_at (datetime): Timestamp when record was created (UTC)
        updated_at (datetime): Timestamp when record was last updated (UTC)
        created_by (UUID, optional): ID of user who created the record
        updated_by (UUID, optional): ID of user who last updated the record
        deleted_at (datetime, optional): Timestamp when record was soft deleted
        is_deleted (bool): Flag indicating if record is soft deleted (default: False)

    Example:
        >>> class User(BaseModel):
        ...     __tablename__ = "users"
        ...     email: Mapped[str] = mapped_column(String(255), unique=True)

        >>> user = User(email="test@example.com")
        >>> print(user.id)  # Auto-generated UUID
        >>> user.soft_delete()
        >>> print(user.is_deleted)  # True

        >>> # Query active records only
        >>> active_filter = User.create_query_filter_active()
        >>> # Use with: session.query(User).filter(active_filter)

    Note:
        This is an abstract base class and cannot be instantiated directly.
        All concrete models must define a __tablename__ attribute.
    """

    __abstract__ = True

    def __init__(self, **kwargs: Any) -> None:
        """Initialize BaseModel with proper default values."""
        # Set default values if not provided
        if "is_deleted" not in kwargs:
            kwargs["is_deleted"] = False
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()

        super().__init__(**kwargs)

    # Primary key - UUID for distributed systems
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
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
        GUID(),
        nullable=True,
    )

    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
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
        """
        Return string representation of the model instance.

        Returns:
            String in format: <ModelName(id=uuid)>

        Example:
            >>> user = User(email="test@example.com")
            >>> print(repr(user))
            <User(id=123e4567-e89b-12d3-a456-426614174000)>
        """
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self, exclude_deleted: bool = True) -> Dict[str, Any]:
        """
        Convert model instance to dictionary representation.

        Converts all column values to JSON-serializable types:
        - datetime objects to ISO format strings
        - UUID objects to string representation
        - Other types remain unchanged

        Args:
            exclude_deleted: If True, returns empty dict for soft-deleted records.
                           If False, includes all fields regardless of deletion status.

        Returns:
            Dictionary with column names as keys and serialized values.
            Returns empty dict if record is soft-deleted and exclude_deleted=True.

        Example:
            >>> user = User(email="test@example.com", first_name="John")
            >>> data = user.to_dict()
            >>> print(data['email'])  # "test@example.com"
            >>> print(data['created_at'])  # "2024-01-15T10:30:00.123456"

            >>> user.soft_delete()
            >>> data = user.to_dict()  # Returns {} by default
            >>> data = user.to_dict(exclude_deleted=False)  # Returns full dict
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
        Mark the record as deleted without removing it from the database.

        Soft delete preserves data integrity and audit trails by setting
        deletion flags rather than physically removing records. This allows
        for data recovery and maintains referential integrity.

        Args:
            deleted_by: UUID of the user performing the deletion. If provided,
                       also updates the updated_by field for audit purposes.

        Side Effects:
            - Sets is_deleted to True
            - Sets deleted_at to current UTC timestamp
            - Updates updated_by if deleted_by is provided

        Example:
            >>> user = User(email="test@example.com")
            >>> user.soft_delete(deleted_by=admin_user_id)
            >>> print(user.is_deleted)  # True
            >>> print(user.deleted_at)  # 2024-01-15 10:30:00.123456+00:00

        Note:
            This method only modifies the instance. You must commit the
            transaction to persist changes to the database.
        """
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        if deleted_by:
            self.updated_by = deleted_by

    def restore(self, restored_by: Optional[uuid.UUID] = None) -> None:
        """
        Restore a soft-deleted record to active status.

        Reverses the soft delete operation by clearing deletion flags
        and timestamps, making the record active again.

        Args:
            restored_by: UUID of the user performing the restoration. If provided,
                        also updates the updated_by field for audit purposes.

        Side Effects:
            - Sets is_deleted to False
            - Clears deleted_at (sets to None)
            - Updates updated_by if restored_by is provided

        Example:
            >>> user.soft_delete()
            >>> print(user.is_deleted)  # True
            >>> user.restore(restored_by=admin_user_id)
            >>> print(user.is_deleted)  # False
            >>> print(user.deleted_at)  # None

        Note:
            This method only modifies the instance. You must commit the
            transaction to persist changes to the database.
        """
        self.is_deleted = False
        self.deleted_at = None
        if restored_by:
            self.updated_by = restored_by

    @classmethod
    def get_table_name(cls) -> str:
        """
        Get the database table name for this model.

        Returns:
            The table name as defined in __tablename__.

        Example:
            >>> User.get_table_name()
            'users'
        """
        return cast(str, cls.__tablename__)

    @classmethod
    def get_primary_key_column(cls) -> str:
        """
        Get the primary key column name for this model.

        Returns:
            The primary key column name (always 'id' for BaseModel).

        Example:
            >>> User.get_primary_key_column()
            'id'
        """
        return "id"

    @classmethod
    def create_query_filter_active(cls) -> ColumnElement[bool]:
        """
        Create a SQLAlchemy filter expression for active (non-deleted) records.

        Returns:
            SQLAlchemy BinaryExpression that can be used in WHERE clauses
            to filter out soft-deleted records.

        Example:
            >>> from sqlalchemy import select
            >>> stmt = select(User).where(User.create_query_filter_active())
            >>> # Equivalent to: SELECT * FROM users WHERE is_deleted = false

            >>> # Or with session.query (legacy style)
            >>> active_users = session.query(User).filter(
            ...     User.create_query_filter_active()
            ... ).all()
        """
        return cls.is_deleted.is_(False)

    @classmethod
    def create_query_filter_deleted(cls) -> ColumnElement[bool]:
        """
        Create a SQLAlchemy filter expression for soft-deleted records.

        Returns:
            SQLAlchemy BinaryExpression that can be used in WHERE clauses
            to find only soft-deleted records.

        Example:
            >>> from sqlalchemy import select
            >>> stmt = select(User).where(User.create_query_filter_deleted())
            >>> # Equivalent to: SELECT * FROM users WHERE is_deleted = true

            >>> # Find deleted records for recovery
            >>> deleted_users = session.query(User).filter(
            ...     User.create_query_filter_deleted()
            ... ).all()
        """
        return cls.is_deleted.is_(True)

    def update_fields(self, **kwargs: Any) -> None:
        """
        Update multiple fields on the model instance in a single operation.

        Provides a convenient way to update multiple attributes at once
        with validation that the fields exist on the model.

        Args:
            **kwargs: Field names as keys and new values as values.
                     Only existing model attributes can be updated.

        Raises:
            AttributeError: If any field name doesn't exist on the model.

        Example:
            >>> user = User(email="old@example.com", first_name="Old")
            >>> user.update_fields(
            ...     email="new@example.com",
            ...     first_name="New",
            ...     last_name="Name"
            ... )
            >>> print(user.email)  # "new@example.com"

            >>> # This would raise AttributeError
            >>> user.update_fields(nonexistent_field="value")

        Note:
            This method only modifies the instance. You must commit the
            transaction to persist changes to the database.
        """
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
            else:
                raise AttributeError(
                    f"'{self.__class__.__name__}' has no attribute '{field}'"
                )
