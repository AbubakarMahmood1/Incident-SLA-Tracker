"""Datetime utilities for the application."""

from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Get current UTC datetime with timezone info.

    Returns:
        datetime: Current UTC datetime
    """
    return datetime.now(timezone.utc)


def add_hours(dt: datetime, hours: int) -> datetime:
    """Add hours to a datetime.

    Args:
        dt: Base datetime
        hours: Number of hours to add

    Returns:
        datetime: New datetime with hours added
    """
    return dt + timedelta(hours=hours)


def add_days(dt: datetime, days: int) -> datetime:
    """Add days to a datetime.

    Args:
        dt: Base datetime
        days: Number of days to add

    Returns:
        datetime: New datetime with days added
    """
    return dt + timedelta(days=days)


def format_timedelta(td: timedelta) -> str:
    """Format a timedelta as a human-readable string.

    Args:
        td: Timedelta to format

    Returns:
        str: Formatted string (e.g., "2h 30m", "3d 4h")
    """
    total_seconds = int(td.total_seconds())
    if total_seconds < 0:
        return "Breached"

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def is_past(dt: datetime) -> bool:
    """Check if a datetime is in the past.

    Args:
        dt: Datetime to check

    Returns:
        bool: True if datetime is in the past
    """
    return dt < utc_now()
