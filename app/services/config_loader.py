#!/usr/bin/env python3
"""
Configuration loader utilities.

Provides a small, robust loader for frequency ownership mappings used as a
tie-breaker when multiple controllers match the same flight transceiver record.

API:
  load_frequency_owners(path: Optional[str]) -> Dict[Decimal, str]
  get_frequency_owner(freq_mhz: Decimal, owners, tolerance) -> Optional[str]

Reads the `config/controller_callsigns_list.txt` file by default but can be
overridden by the `FREQ_OWNER_FILE_PATH` environment variable.
Frequencies are normalised to Decimal with 3 decimal places but lookups are
tolerance-aware (do not require exact string equality).
"""
from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation, getcontext
from typing import Dict, Optional, Tuple

# use sufficient precision for MHz decimals
getcontext().prec = 9
CANONICAL_QUANT = Decimal("0.001")

DEFAULT_REL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "controller_callsigns_list.txt")


def _parse_frequency(value: str) -> Optional[Decimal]:
    try:
        v = value.strip()
        # accept integer Hz (e.g. 132200000) or MHz decimal (e.g. 132.2)
        if v.isdigit() and len(v) > 6:
            d = Decimal(v) / Decimal(1000000)
        else:
            d = Decimal(v)
        return d.quantize(CANONICAL_QUANT)
    except (InvalidOperation, ValueError):
        return None


def load_frequency_owners(path: Optional[str] = None) -> Dict[Decimal, str]:
    """Load frequency ownership mapping from file.

    Returns a mapping from canonical Decimal frequency (MHz) -> callsign.
    Malformed lines are ignored.
    """
    file_path = path or os.getenv("FREQ_OWNER_FILE_PATH", DEFAULT_REL_PATH)
    owners: Dict[Decimal, str] = {}

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            for ln in fh:
                s = ln.strip()
                if not s or s.startswith("#"):
                    continue
                parts = [p.strip() for p in s.split(",")]
                if len(parts) < 2:
                    continue
                callsign, freq_raw = parts[0], parts[1]
                freq = _parse_frequency(freq_raw)
                if freq is None:
                    continue
                if freq not in owners:
                    owners[freq] = callsign
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

    return owners


def get_frequency_owner(freq_mhz: Decimal, owners: Dict[Decimal, str], tolerance_mhz: Decimal) -> Optional[str]:
    """Return owner callsign for a frequency using tolerance-aware lookup.

    If multiple owners are within tolerance, chooses the owner with smallest
    frequency difference.
    """
    if not owners:
        return None

    freq_norm = freq_mhz.quantize(CANONICAL_QUANT)
    best: Tuple[Optional[Decimal], Optional[str]] = (None, None)
    for owner_freq, callsign in owners.items():
        diff = abs(owner_freq - freq_norm)
        if diff <= tolerance_mhz:
            if best[0] is None or diff < best[0]:
                best = (diff, callsign)

    return best[1]


