"""Data formatting helpers."""
import pandas as pd
from typing import Any, Dict, List
import json


def df_to_records(df: pd.DataFrame) -> List[Dict]:
    """Convert DataFrame to list of records with datetime handling."""
    df = df.copy()
    if 'time' in df.columns:
        df['time'] = df['time'].astype(str)
    return df.to_dict(orient='records')


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float."""
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert to int."""
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def truncate_list(lst: List, max_items: int = 100) -> List:
    """Truncate a list to max items."""
    if len(lst) <= max_items:
        return lst
    return lst[:max_items]


def format_price(price: float, digits: int = 5) -> float:
    """Format price to specified decimal places."""
    return round(price, digits)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount."""
    return f"{currency} {amount:,.2f}"


def format_pips(pips: float) -> str:
    """Format pip value."""
    return f"{pips:.1f} pips"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage."""
    return f"{value:.{decimals}f}%"


class AnalysisResult:
    """Base class for analysis results."""
    
    def __init__(self, status: str = "success", **kwargs):
        self.status = status
        self.timestamp = pd.Timestamp.now(tz='UTC').isoformat()
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = {"status": self.status, "timestamp": self.timestamp}
        for key, value in self.__dict__.items():
            if key not in ["status", "timestamp"]:
                if isinstance(value, pd.Timestamp):
                    result[key] = value.isoformat()
                elif isinstance(value, pd.DataFrame):
                    result[key] = df_to_records(value)
                else:
                    result[key] = value
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str, indent=2)
