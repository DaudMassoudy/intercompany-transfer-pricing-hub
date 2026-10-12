from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """UTC timestamp stored as naive UTC for compatibility with legacy DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
