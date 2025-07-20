"""
Vet Core Package

A foundational Python package providing shared data models, database utilities,
and validation schemas for the veterinary clinic platform.
"""

__version__ = "0.1.0"
__author__ = "Vet Clinic Platform Team"

# Import implemented modules
from . import database
from . import exceptions
from . import models

# Lazy imports for schemas and utils (not yet implemented)
# from . import schemas
# from . import utils

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Implemented modules
    "database",
    "exceptions", 
    "models",
    # Core modules will be populated as they're implemented
    # "schemas",
    # "utils",
]