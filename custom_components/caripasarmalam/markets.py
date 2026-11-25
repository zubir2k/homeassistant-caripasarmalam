"""Compatibility facade re-exporting market models and spatial calculations.

Underlying implementation is maintained in the standalone `python-caripasarmalam` library.
"""
from __future__ import annotations

from caripasarmalam import (
    DAY_CODES,
    DAY_INDEX,
    MYT,
    RANK,
    WEEK_MINUTES as WEEK,
    Market,
    haversine_km,
    nearby,
)

__all__ = [
    "DAY_CODES",
    "DAY_INDEX",
    "MYT",
    "RANK",
    "WEEK",
    "Market",
    "haversine_km",
    "nearby",
]
