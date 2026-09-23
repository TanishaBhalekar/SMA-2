"""
Configuration module for Unified Progressive Entity Resolution & Data Repository (PRJ-07).
Loads environment variables and provides global settings.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv, find_dotenv

# Determine base project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Attempt loading from explicit root .env, fallback to find_dotenv()
env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(find_dotenv())

# Core Configuration Settings
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
