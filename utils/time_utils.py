"""Time utilities for trading sessions and timezone handling."""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple


def get_utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


def get_session_context() -> Dict:
    """Determine current trading session and expected volatility."""
    now = get_utc_now()
    hour = now.hour
    
    sessions = {
        "sydney": (21, 6),
        "tokyo": (0, 9),
        "london": (7, 16),
        "new_york": (12, 21)
    }
    
    active = []
    for session, (start, end) in sessions.items():
        if start < end:
            if start <= hour < end:
                active.append(session)
        else:  # Session crosses midnight
            if hour >= start or hour < end:
                active.append(session)
    
    overlap = len(active) > 1
    
    volatility_expectation = "HIGH" if overlap else \
                             "HIGH" if "london" in active or "new_york" in active else \
                             "MEDIUM" if "tokyo" in active else "LOW"
    
    best_pairs = {
        "sydney": ["AUDUSD", "NZDUSD", "AUDJPY"],
        "tokyo": ["USDJPY", "EURJPY", "GBPJPY", "XAUUSD"],
        "london": ["EURUSD", "GBPUSD", "EURGBP", "XAUUSD"],
        "new_york": ["EURUSD", "GBPUSD", "USDCAD", "XAUUSD"]
    }
    
    return {
        "utc_time": str(now),
        "utc_hour": hour,
        "active_sessions": active,
        "session_overlap": overlap,
        "overlap_sessions": active if overlap else [],
        "expected_volatility": volatility_expectation,
        "best_pairs_for_session": [best_pairs.get(s, []) for s in active],
        "is_trading_hours": len(active) > 0
    }


def get_timeframe_minutes(timeframe: str) -> int:
    """Convert timeframe string to minutes."""
    tf_map = {
        "M1": 1, "M5": 5, "M15": 15, "M30": 30,
        "H1": 60, "H4": 240, "D1": 1440, "W1": 10080, "MN1": 43200
    }
    return tf_map.get(timeframe, 60)


def format_duration(seconds: int) -> str:
    """Format seconds into human readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h {seconds % 3600 // 60}m"
    else:
        return f"{seconds // 86400}d {seconds % 86400 // 3600}h"


def hours_until_event(event_hour: int, event_minute: int = 0) -> float:
    """Calculate hours until a specific UTC time today."""
    now = get_utc_now()
    event_time = now.replace(hour=event_hour, minute=event_minute, second=0, microsecond=0)
    
    if event_time < now:
        event_time += timedelta(days=1)
    
    return (event_time - now).total_seconds() / 3600
