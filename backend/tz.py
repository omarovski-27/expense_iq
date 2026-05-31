from datetime import date, datetime, timedelta, timezone

JORDAN_TZ = timezone(timedelta(hours=3))


def today_jordan() -> date:
    return datetime.now(JORDAN_TZ).date()
