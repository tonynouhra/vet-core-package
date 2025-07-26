"""
DateTime utilities for veterinary operations.

This module provides timezone-aware datetime handling, business hours calculation,
appointment scheduling helpers, and age calculation utilities for pets.
"""

import calendar
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from zoneinfo import ZoneInfo


class DayOfWeek(Enum):
    """Enumeration for days of the week."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class BusinessHours:
    """Represents business hours for a clinic."""

    def __init__(
        self, day: DayOfWeek, open_time: time, close_time: time, is_closed: bool = False
    ):
        """
        Initialize business hours for a specific day.

        Args:
            day: Day of the week
            open_time: Opening time
            close_time: Closing time
            is_closed: Whether the business is closed on this day
        """
        self.day = day
        self.open_time = open_time
        self.close_time = close_time
        self.is_closed = is_closed

    def is_open_at(self, check_time: time) -> bool:
        """Check if the clinic is open at a specific time."""
        if self.is_closed:
            return False
        return self.open_time <= check_time <= self.close_time


def get_current_utc() -> datetime:
    """Get the current UTC datetime."""
    return datetime.now(ZoneInfo("UTC"))


def get_current_local(timezone: str = "UTC") -> datetime:
    """Get the current datetime in a specific timezone."""
    return datetime.now(ZoneInfo(timezone))


def convert_timezone(dt: datetime, from_tz: str, to_tz: str) -> datetime:
    """Convert datetime from one timezone to another."""
    if dt.tzinfo is None:
        # Assume the datetime is in the from_tz
        dt = dt.replace(tzinfo=ZoneInfo(from_tz))
    elif dt.tzinfo != ZoneInfo(from_tz):
        # Convert to from_tz first if it's in a different timezone
        dt = dt.astimezone(ZoneInfo(from_tz))

    return dt.astimezone(ZoneInfo(to_tz))


def to_utc(dt: datetime, source_tz: str = "UTC") -> datetime:
    """Convert a datetime to UTC."""
    return convert_timezone(dt, source_tz, "UTC")


def from_utc(dt: datetime, target_tz: str) -> datetime:
    """Convert a UTC datetime to a target timezone."""
    return convert_timezone(dt, "UTC", target_tz)


def is_business_hours(
    check_datetime: datetime,
    business_hours: Dict[DayOfWeek, BusinessHours],
    timezone: str = "UTC",
) -> bool:
    """
    Check if a datetime falls within business hours.

    Args:
        check_datetime: The datetime to check
        business_hours: Dictionary mapping days to BusinessHours
        timezone: Timezone to use for the check

    Returns:
        True if the datetime is within business hours
    """
    # Convert to the clinic's timezone
    local_dt = (
        from_utc(check_datetime, timezone) if check_datetime.tzinfo else check_datetime
    )
    day_of_week = DayOfWeek(local_dt.weekday())

    if day_of_week not in business_hours:
        return False

    hours = business_hours[day_of_week]
    return hours.is_open_at(local_dt.time())


def get_next_business_day(
    start_date: date, business_hours: Dict[DayOfWeek, BusinessHours]
) -> Optional[date]:
    """
    Get the next business day from a given date.

    Args:
        start_date: The starting date
        business_hours: Dictionary mapping days to BusinessHours

    Returns:
        The next business day, or None if no business days found in the next 14 days
    """
    current_date = start_date
    for _ in range(14):  # Check up to 2 weeks ahead
        day_of_week = DayOfWeek(current_date.weekday())
        if day_of_week in business_hours and not business_hours[day_of_week].is_closed:
            return current_date
        current_date += timedelta(days=1)

    return None


def get_available_appointment_slots(
    date_to_check: date,
    business_hours: Dict[DayOfWeek, BusinessHours],
    appointment_duration: timedelta = timedelta(minutes=30),
    buffer_time: timedelta = timedelta(minutes=15),
    existing_appointments: Optional[List[Tuple[datetime, datetime]]] = None,
    timezone: str = "UTC",
) -> List[datetime]:
    """
    Get available appointment slots for a given date.

    Args:
        date_to_check: The date to check for availability
        business_hours: Dictionary mapping days to BusinessHours
        appointment_duration: Duration of each appointment
        buffer_time: Buffer time between appointments
        existing_appointments: List of (start, end) tuples for existing appointments
        timezone: Timezone for the appointments

    Returns:
        List of available appointment start times
    """
    day_of_week = DayOfWeek(date_to_check.weekday())

    if day_of_week not in business_hours or business_hours[day_of_week].is_closed:
        return []

    hours = business_hours[day_of_week]

    # Create datetime objects for the business hours
    start_datetime = datetime.combine(
        date_to_check, hours.open_time, ZoneInfo(timezone)
    )
    end_datetime = datetime.combine(date_to_check, hours.close_time, ZoneInfo(timezone))

    # Generate all possible slots
    available_slots = []
    current_slot = start_datetime
    slot_duration = appointment_duration + buffer_time

    while current_slot + appointment_duration <= end_datetime:
        slot_end = current_slot + appointment_duration

        # Check if this slot conflicts with existing appointments
        is_available = True
        if existing_appointments:
            for existing_start, existing_end in existing_appointments:
                # Check for overlap
                if current_slot < existing_end and slot_end > existing_start:
                    is_available = False
                    break

        if is_available:
            available_slots.append(current_slot)

        current_slot += slot_duration

    return available_slots


def calculate_pet_age(
    birth_date: date, reference_date: Optional[date] = None
) -> Dict[str, int]:
    """
    Calculate a pet's age in years, months, and days.

    Args:
        birth_date: The pet's birth date
        reference_date: The date to calculate age from (defaults to today)

    Returns:
        Dictionary with 'years', 'months', and 'days' keys
    """
    if reference_date is None:
        reference_date = date.today()

    if birth_date > reference_date:
        raise ValueError("Birth date cannot be in the future")

    years = reference_date.year - birth_date.year
    months = reference_date.month - birth_date.month
    days = reference_date.day - birth_date.day

    # Adjust for negative days
    if days < 0:
        months -= 1
        # Get the last day of the previous month
        if reference_date.month == 1:
            prev_month_last_day = calendar.monthrange(reference_date.year - 1, 12)[1]
        else:
            prev_month_last_day = calendar.monthrange(
                reference_date.year, reference_date.month - 1
            )[1]
        days += prev_month_last_day

    # Adjust for negative months
    if months < 0:
        years -= 1
        months += 12

    return {"years": years, "months": months, "days": days}


def format_pet_age(age_dict: Dict[str, int]) -> str:
    """
    Format a pet's age dictionary into a human-readable string.

    Args:
        age_dict: Dictionary with 'years', 'months', and 'days' keys

    Returns:
        Formatted age string
    """
    years = age_dict["years"]
    months = age_dict["months"]
    days = age_dict["days"]

    parts = []

    if years > 0:
        parts.append(f"{years} year{'s' if years != 1 else ''}")

    if months > 0:
        parts.append(f"{months} month{'s' if months != 1 else ''}")

    if days > 0 and years == 0:  # Only show days if less than a year old
        parts.append(f"{days} day{'s' if days != 1 else ''}")

    if not parts:
        return "0 days"

    return ", ".join(parts)


def get_pet_age_category(
    birth_date: date, reference_date: Optional[date] = None
) -> str:
    """
    Get the age category for a pet (puppy/kitten, adult, senior).

    Args:
        birth_date: The pet's birth date
        reference_date: The date to calculate age from (defaults to today)

    Returns:
        Age category string
    """
    age = calculate_pet_age(birth_date, reference_date)
    total_months = age["years"] * 12 + age["months"]

    if total_months < 12:
        return "young"
    elif total_months < 84:  # 7 years
        return "adult"
    else:
        return "senior"


def is_appointment_time_valid(
    appointment_datetime: datetime,
    min_advance_hours: int = 1,
    max_advance_days: int = 90,
) -> Tuple[bool, Optional[str]]:
    """
    Validate if an appointment time is within acceptable scheduling limits.

    Args:
        appointment_datetime: The proposed appointment datetime
        min_advance_hours: Minimum hours in advance required
        max_advance_days: Maximum days in advance allowed

    Returns:
        Tuple of (is_valid, error_message)
    """
    now = get_current_utc()

    # Convert appointment time to UTC if it has timezone info
    if appointment_datetime.tzinfo:
        appointment_utc = appointment_datetime.astimezone(ZoneInfo("UTC"))
    else:
        appointment_utc = appointment_datetime.replace(tzinfo=ZoneInfo("UTC"))

    # Check minimum advance time
    min_time = now + timedelta(hours=min_advance_hours)
    if appointment_utc < min_time:
        return (
            False,
            f"Appointment must be scheduled at least {min_advance_hours} hours in advance",
        )

    # Check maximum advance time
    max_time = now + timedelta(days=max_advance_days)
    if appointment_utc > max_time:
        return (
            False,
            f"Appointment cannot be scheduled more than {max_advance_days} days in advance",
        )

    return True, None


def round_to_nearest_slot(
    dt: datetime, slot_duration: timedelta = timedelta(minutes=15)
) -> datetime:
    """
    Round a datetime to the nearest appointment slot.

    Args:
        dt: The datetime to round
        slot_duration: The duration of each slot

    Returns:
        Rounded datetime
    """
    # Get the number of seconds since midnight
    seconds_since_midnight = (
        dt - dt.replace(hour=0, minute=0, second=0, microsecond=0)
    ).total_seconds()
    slot_seconds = slot_duration.total_seconds()

    # Round to the nearest slot
    rounded_slots = round(seconds_since_midnight / slot_seconds)
    rounded_seconds = rounded_slots * slot_seconds

    # Create the rounded datetime
    midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight + timedelta(seconds=rounded_seconds)
