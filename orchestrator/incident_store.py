"""SQLite-backed incident store shared across orchestration loops."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from adapters.canonical_alert import CanonicalAlert, Incident


class IncidentStore:
    """Persist and query incidents with async-safe writers and sync readers."""

    def __init__(self, db_path: str = "incidents.db") -> None:
        """Open SQLite database, create schema, and prepare locks."""
        self._db_path = db_path
        self._async_lock = asyncio.Lock()
        self._sql_lock = threading.RLock()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Create incidents table if missing."""
        with self._sql_lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    status TEXT,
                    root_cause_device TEXT,
                    incident_title TEXT,
                    affected_services TEXT,
                    confidence REAL,
                    recommended_action TEXT,
                    alerts TEXT,
                    preliminary_advisory_sent INTEGER DEFAULT 0,
                    confirmed_advisory_sent INTEGER DEFAULT 0
                )
                """
            )
            self._conn.commit()

    def _incident_to_row(self, incident: Incident) -> tuple[Any, ...]:
        """Serialize incident for SQLite insert/replace."""
        return (
            incident.incident_id,
            incident.created_at.isoformat(),
            incident.updated_at.isoformat(),
            incident.status,
            incident.root_cause_device,
            incident.incident_title,
            json.dumps(incident.affected_services),
            float(incident.confidence),
            incident.recommended_action,
            json.dumps([alert.to_dict() for alert in incident.alerts]),
            1 if incident.preliminary_advisory_sent else 0,
            1 if incident.confirmed_advisory_sent else 0,
        )

    def _row_to_incident(self, row: sqlite3.Row) -> Incident:
        """Deserialize SQLite row into Incident."""
        alerts_raw = json.loads(str(row["alerts"]))
        alerts = [CanonicalAlert.from_dict(dict(a)) for a in alerts_raw]
        affected = json.loads(str(row["affected_services"]))
        return Incident(
            incident_id=str(row["incident_id"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            status=str(row["status"]),
            root_cause_device=str(row["root_cause_device"]),
            incident_title=str(row["incident_title"]),
            affected_services=[str(x) for x in affected],
            confidence=float(row["confidence"]),
            recommended_action=str(row["recommended_action"]),
            alerts=alerts,
            preliminary_advisory_sent=bool(row["preliminary_advisory_sent"]),
            confirmed_advisory_sent=bool(row["confirmed_advisory_sent"]),
        )

    def _upsert_sync(self, incident: Incident) -> None:
        """Insert or replace one incident row."""
        with self._sql_lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO incidents (
                    incident_id, created_at, updated_at, status,
                    root_cause_device, incident_title, affected_services,
                    confidence, recommended_action, alerts,
                    preliminary_advisory_sent, confirmed_advisory_sent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._incident_to_row(incident),
            )
            self._conn.commit()

    async def upsert(self, incident: Incident) -> None:
        """Insert or replace an incident; alerts stored as JSON."""
        async with self._async_lock:
            await asyncio.to_thread(self._upsert_sync, incident)

    def get_open_incidents(self) -> List[Incident]:
        """Return all incidents with status open."""
        with self._sql_lock:
            cursor = self._conn.execute(
                "SELECT * FROM incidents WHERE status = ? ORDER BY updated_at DESC",
                ("open",),
            )
            rows = cursor.fetchall()
        return [self._row_to_incident(row) for row in rows]

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Return a single incident by id, if present."""
        with self._sql_lock:
            cursor = self._conn.execute(
                "SELECT * FROM incidents WHERE incident_id = ?",
                (incident_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_incident(row)

    def _mark_advisory_sent_sync(self, incident_id: str, advisory_type: str) -> None:
        """Update advisory flags for one incident."""
        if advisory_type not in {"preliminary", "confirmed"}:
            raise ValueError("advisory_type must be 'preliminary' or 'confirmed'.")
        if advisory_type == "preliminary":
            sql = "UPDATE incidents SET preliminary_advisory_sent = 1 WHERE incident_id = ?"
        else:
            sql = "UPDATE incidents SET confirmed_advisory_sent = 1 WHERE incident_id = ?"
        with self._sql_lock:
            self._conn.execute(sql, (incident_id,))
            self._conn.commit()

    async def mark_advisory_sent(self, incident_id: str, advisory_type: str) -> None:
        """Set preliminary or confirmed advisory-sent flag."""
        async with self._async_lock:
            await asyncio.to_thread(self._mark_advisory_sent_sync, incident_id, advisory_type)

    def get_recent_resolved(self, hours: int = 24) -> List[Incident]:
        """Return resolved incidents updated within the last ``hours``."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        with self._sql_lock:
            cursor = self._conn.execute(
                "SELECT * FROM incidents WHERE status = ? ORDER BY updated_at DESC",
                ("resolved",),
            )
            rows = cursor.fetchall()
        resolved: List[Incident] = []
        for row in rows:
            incident = self._row_to_incident(row)
            updated = incident.updated_at
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            else:
                updated = updated.astimezone(timezone.utc)
            if updated >= cutoff:
                resolved.append(incident)
        return resolved

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._sql_lock:
            self._conn.close()
