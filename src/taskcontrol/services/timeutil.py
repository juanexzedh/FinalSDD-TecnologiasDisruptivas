from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


def as_utc(dt):
    """SQLite devuelve datetimes sin zona; los tratamos como UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
