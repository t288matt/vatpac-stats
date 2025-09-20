#!/usr/bin/env python3
"""
Transceiver Loader (DB-only, deterministic)

Provides helper functions to load transceivers from the database using
keyset pagination over (timestamp, id), with optional filtering by
entity_type and callsign. This module avoids any in-process caching so
that detection services observe identical datasets for a given window.
"""

from __future__ import annotations

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy import text

from app.database import get_database_session


def _get_page_size(override_page_size: Optional[int] = None) -> int:
    if override_page_size is not None and override_page_size > 0:
        return override_page_size
    try:
        return int(os.getenv("TRANSCEIVER_PAGE_SIZE", "10000"))
    except Exception:
        return 10000


async def load_transceivers_window(
    start: datetime,
    end: datetime,
    entity_type: Optional[str] = None,
    page_size: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load transceivers deterministically covering [start, end], optionally
    filtered by entity_type. Uses keyset pagination to avoid large OFFSETs.
    """
    results: List[Dict[str, Any]] = []
    use_page_size = _get_page_size(page_size)

    last_ts = start.replace(microsecond=0) if start is not None else datetime.min.replace(tzinfo=timezone.utc)
    last_id = 0

    while True:
        base = (
            "SELECT id as transceiver_id, callsign, frequency, position_lat, position_lon, height_msl, height_agl, timestamp, entity_type "                                            
            "FROM transceivers WHERE timestamp >= :start AND timestamp <= :end"
        )
        if entity_type:
            base += " AND entity_type = :entity_type"
        # Keyset condition
        base += " AND (timestamp > :last_ts OR (timestamp = :last_ts AND id > :last_id)) ORDER BY timestamp, id LIMIT :limit"

        async with get_database_session() as session:
            params = {
                "start": start,
                "end": end,
                "last_ts": last_ts,
                "last_id": last_id,
                "limit": use_page_size,
            }
            if entity_type:
                params["entity_type"] = entity_type
            res = await session.execute(text(base), params)
            rows = res.fetchall()

        if not rows:
            break

        for row in rows:
            results.append(
                {
                    "transceiver_id": row.transceiver_id,
                    "callsign": row.callsign,
                    "frequency": row.frequency,
                    "frequency_mhz": (row.frequency / 1000000.0) if row.frequency is not None else None,                                                       
                    "position_lat": row.position_lat,
                    "position_lon": row.position_lon,
                    "height_msl": row.height_msl,
                    "height_agl": row.height_agl,
                    "timestamp": row.timestamp,
                    "entity_type": row.entity_type,
                }
            )

        last_row = rows[-1]
        last_ts = last_row.timestamp
        last_id = last_row.transceiver_id

        if len(rows) < use_page_size:
            break

    return results


async def load_transceivers_for_callsign(
    start: datetime,
    end: datetime,
    entity_type: str,
    callsign: str,
    page_size: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load transceivers for a specific callsign and entity_type within [start, end].
    Uses keyset pagination.
    """
    results: List[Dict[str, Any]] = []
    use_page_size = _get_page_size(page_size)

    last_ts = start.replace(microsecond=0) if start is not None else datetime.min.replace(tzinfo=timezone.utc)
    last_id = 0

    while True:
        base = (
            "SELECT id as transceiver_id, callsign, frequency, position_lat, position_lon, height_msl, height_agl, timestamp, entity_type "                                            
            "FROM transceivers WHERE timestamp >= :start AND timestamp <= :end AND entity_type = :entity_type AND callsign = :callsign"                        
        )
        base += " AND (timestamp > :last_ts OR (timestamp = :last_ts AND id > :last_id)) ORDER BY timestamp, id LIMIT :limit"

        async with get_database_session() as session:
            params = {
                "start": start,
                "end": end,
                "entity_type": entity_type,
                "callsign": callsign,
                "last_ts": last_ts,
                "last_id": last_id,
                "limit": use_page_size,
            }
            res = await session.execute(text(base), params)
            rows = res.fetchall()

        if not rows:
            break

        for row in rows:
            results.append(
                {
                    "transceiver_id": row.transceiver_id,
                    "callsign": row.callsign,
                    "frequency": row.frequency,
                    "frequency_mhz": (row.frequency / 1000000.0) if row.frequency is not None else None,                                                       
                    "position_lat": row.position_lat,
                    "position_lon": row.position_lon,
                    "height_msl": row.height_msl,
                    "height_agl": row.height_agl,
                    "timestamp": row.timestamp,
                    "entity_type": row.entity_type,
                }
            )

        last_row = rows[-1]
        last_ts = last_row.timestamp
        last_id = last_row.transceiver_id

        if len(rows) < use_page_size:
            break

    return results


