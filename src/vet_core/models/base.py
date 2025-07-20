"""
Base model class for all SQLAlchemy models in the vet-core package.

This module provides the base model class that all other models inherit from,
including common fields and functionality.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the base class for all models
BaseModel = declarative_base()

# This will be properly implemented in task 2
# For now, this is just a placeholder to make imports work