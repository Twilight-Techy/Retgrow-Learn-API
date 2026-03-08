#!/usr/bin/env python3
"""
Database Seed Script Wrapper

This script now serves as a wrapper that calls the refactored, comprehensive
database seeder located in `src.seed.seed`.

Usage:
    python scripts/seed_test_data.py
"""

import sys
import asyncio
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.seed.seed import main

if __name__ == "__main__":
    asyncio.run(main())