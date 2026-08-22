"""NSE tickers — shared map from news_agent/companies.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from companies import UNIVERSE, companies_in_text  # noqa: F401

__all__ = ["UNIVERSE", "companies_in_text"]
