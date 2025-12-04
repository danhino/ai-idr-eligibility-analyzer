"""
Configuration management for ERA IDR Analyzer.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SEED_DIR = DATA_DIR / "seed"
SAMPLES_DIR = BASE_DIR / "samples"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = BASE_DIR / "era_idr.db"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
SEED_DIR.mkdir(exist_ok=True)
SAMPLES_DIR.mkdir(exist_ok=True)

# Environment variables
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "eng")
TZ: str = os.getenv("TZ", "America/New_York")
APP_PORT: int = int(os.getenv("APP_PORT", "8501"))

# Database settings
DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

# AI settings
AI_ENABLED: bool = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 0
AI_MODEL: str = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "30"))

# ERA parsing settings
DEFAULT_SEGMENT_DELIMITER: str = "~"
DEFAULT_ELEMENT_DELIMITER: str = "*"
DEFAULT_SUBELEMENT_DELIMITER: str = ":"

# IDR timeline settings
OPEN_NEGOTIATION_DAYS: int = 30
IDR_INITIATION_DAYS: int = 4

