"""Logging configuration for the trading system."""
import sys
from pathlib import Path
from loguru import logger

# Remove default handler
logger.remove()

# Add console handler with color
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# Add file handler
log_path = Path(__file__).parent.parent / "data" / "logs"
log_path.mkdir(parents=True, exist_ok=True)

logger.add(
    log_path / "trading_system_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    compression="zip"
)

def get_logger(name: str):
    """Get a logger instance with the given name."""
    return logger.bind(name=name)
