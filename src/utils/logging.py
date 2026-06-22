"""
Logging configuration for ERA IDR Analyzer.
"""
import sys
from pathlib import Path
from loguru import logger

from src.config import LOGS_DIR

# Remove default handler
logger.remove()

# Add file handler
log_file = LOGS_DIR / "app.log"
logger.add(
    log_file,
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    backtrace=True,
    diagnose=False
)

# Add console handler with less verbose format
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True
)


