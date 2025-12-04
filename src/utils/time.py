"""
Time and date utilities for IDR timeline calculations.
"""
from datetime import date, datetime, timedelta
from typing import Optional
import pytz

from src.config import TZ, OPEN_NEGOTIATION_DAYS, IDR_INITIATION_DAYS


def get_timezone():
    """Get timezone object."""
    try:
        return pytz.timezone(TZ)
    except pytz.exceptions.UnknownTimeZoneError:
        return pytz.UTC


def is_business_day(d: date) -> bool:
    """Check if a date is a business day (Monday-Friday)."""
    return d.weekday() < 5  # 0=Monday, 4=Friday


def add_business_days(start_date: date, days: int) -> date:
    """Add business days to a date."""
    current = start_date
    added = 0
    
    while added < days:
        current += timedelta(days=1)
        if is_business_day(current):
            added += 1
    
    return current


def calculate_open_negotiation_end(payment_date: date) -> date:
    """Calculate open negotiation window end date (30 business days from payment)."""
    return add_business_days(payment_date, OPEN_NEGOTIATION_DAYS)


def calculate_idr_initiation_window_end(payment_date: date) -> date:
    """Calculate IDR initiation window end date (4 business days after open negotiation end)."""
    open_neg_end = calculate_open_negotiation_end(payment_date)
    return add_business_days(open_neg_end, IDR_INITIATION_DAYS)


def parse_date(date_str: str, formats: Optional[list] = None) -> Optional[date]:
    """Parse date string in various formats."""
    if formats is None:
        formats = [
            "%Y%m%d",  # ANSI 835 format
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
        ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    
    return None


