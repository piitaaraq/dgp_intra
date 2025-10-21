# dgp_intra/routes/shared.py
from datetime import date as date_cls, time

BREAKFAST_LOCK = time(9, 0)

def _safe_date(year, month, day):
    try:
        return date_cls(year, month, day)
    except ValueError:
        if month == 2 and day == 29:
            return date_cls(year, 2, 28)
        raise

def next_birthday(dob: date_cls, today: date_cls) -> date_cls:
    this_year = _safe_date(today.year, dob.month, dob.day)
    if this_year >= today:
        return this_year
    return _safe_date(today.year + 1, dob.month, dob.day)
