"""
Database-agnostic column types for vet-core.

This module provides column types that work across different database backends,
particularly for handling JSON data in both PostgreSQL and SQLite.
"""

from typing import Any

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.type_api import TypeEngine


class JSONType(TypeDecorator):
    """
    Database-agnostic JSON column type.

    Uses JSONB for PostgreSQL and JSON for other databases (like SQLite).
    This ensures compatibility across different database backends while
    maintaining optimal performance for each.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """Load the appropriate JSON type based on the database dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        """Process value when storing to database."""
        if value is None:
            return None

        # Ensure date fields are stored as date strings, not datetime strings
        if isinstance(value, list):
            formatted_list = []
            for item in value:
                if isinstance(item, dict):
                    formatted_item = item.copy()

                    # Format date fields to ensure they're stored as date strings
                    for field_name in [
                        "date",
                        "next_due_date",
                        "date_discovered",
                        "date_recorded",
                    ]:
                        if field_name in formatted_item and formatted_item[field_name]:
                            date_value = formatted_item[field_name]
                            if isinstance(date_value, str) and "T" in date_value:
                                # Extract just the date part if it contains time
                                formatted_item[field_name] = date_value.split("T")[0]

                    formatted_list.append(formatted_item)
                else:
                    formatted_list.append(item)
            return formatted_list
        elif isinstance(value, dict):
            # Handle single dictionary objects
            formatted_dict = value.copy()

            # Format date fields to ensure they're stored as date strings
            for field_name in [
                "date",
                "next_due_date",
                "date_discovered",
                "date_recorded",
            ]:
                if field_name in formatted_dict and formatted_dict[field_name]:
                    date_value = formatted_dict[field_name]
                    if isinstance(date_value, str) and "T" in date_value:
                        # Extract just the date part if it contains time
                        formatted_dict[field_name] = date_value.split("T")[0]

            # Handle nested records in medical_history
            if "records" in formatted_dict and isinstance(
                formatted_dict["records"], list
            ):
                formatted_records = []
                for record in formatted_dict["records"]:
                    if isinstance(record, dict):
                        formatted_record = record.copy()
                        for field_name in [
                            "date",
                            "next_due_date",
                            "date_discovered",
                            "date_recorded",
                        ]:
                            if (
                                field_name in formatted_record
                                and formatted_record[field_name]
                            ):
                                date_value = formatted_record[field_name]
                                if isinstance(date_value, str) and "T" in date_value:
                                    formatted_record[field_name] = date_value.split(
                                        "T"
                                    )[0]
                        formatted_records.append(formatted_record)
                    else:
                        formatted_records.append(record)
                formatted_dict["records"] = formatted_records

            return formatted_dict

        return value

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        """Process value when loading from database."""
        if value is None:
            return None

        # Handle date formatting in vaccination records and other JSON data
        if isinstance(value, list):
            formatted_list = []
            for item in value:
                if isinstance(item, dict):
                    formatted_item = item.copy()

                    # Format date fields that might have been converted to datetime strings
                    for field_name in [
                        "date",
                        "next_due_date",
                        "date_discovered",
                        "date_recorded",
                    ]:
                        if field_name in formatted_item and formatted_item[field_name]:
                            date_value = formatted_item[field_name]
                            if isinstance(date_value, str) and "T" in date_value:
                                # Extract just the date part if it contains time
                                formatted_item[field_name] = date_value.split("T")[0]

                    formatted_list.append(formatted_item)
                else:
                    formatted_list.append(item)
            return formatted_list
        elif isinstance(value, dict):
            # Handle single dictionary objects (like medical_history)
            formatted_dict = value.copy()

            # Format date fields that might have been converted to datetime strings
            for field_name in [
                "date",
                "next_due_date",
                "date_discovered",
                "date_recorded",
            ]:
                if field_name in formatted_dict and formatted_dict[field_name]:
                    date_value = formatted_dict[field_name]
                    if isinstance(date_value, str) and "T" in date_value:
                        # Extract just the date part if it contains time
                        formatted_dict[field_name] = date_value.split("T")[0]

            # Handle nested records in medical_history
            if "records" in formatted_dict and isinstance(
                formatted_dict["records"], list
            ):
                formatted_records = []
                for record in formatted_dict["records"]:
                    if isinstance(record, dict):
                        formatted_record = record.copy()
                        for field_name in [
                            "date",
                            "next_due_date",
                            "date_discovered",
                            "date_recorded",
                        ]:
                            if (
                                field_name in formatted_record
                                and formatted_record[field_name]
                            ):
                                date_value = formatted_record[field_name]
                                if isinstance(date_value, str) and "T" in date_value:
                                    formatted_record[field_name] = date_value.split(
                                        "T"
                                    )[0]
                        formatted_records.append(formatted_record)
                    else:
                        formatted_records.append(record)
                formatted_dict["records"] = formatted_records

            return formatted_dict

        return value
