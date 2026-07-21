#!/usr/bin/env python3
"""
AEGIS Metrics Engine — Centralized Logging & Real-Time Tracking
Stores and queries metrics from all forge cycles with AEGIS safeguards.

Supports:
  - SQLite backend for persistence
  - Real-time in-memory cache for UI updates
  - Statistical summaries (rejection rates, healing frequency, etc.)
  - Streaming updates for dashboard

Usage:
    from aegis_metrics_engine import AEGISMetricsEngine
    
    metrics = AEGISMetricsEngine(db_path="./aegis_metrics.db")
    metrics.log_forge_execution(forge_metrics)
    
    stats = metrics.get_statistics()
    print(stats["rejection_rate"])
    
    # Real-time updates via callback
    def on_metric_update(event):
        print(f"Alert: {event['healing_action']}")
    
    metrics.subscribe_to_updates(on_metric_update)

Author: Jonathan Harrison / Codette Architecture
"""

import logging
import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import deque
import threading

logger = logging.getLogger(__name__)


class AEGISMetricsEngine:
    """
    Centralized metrics logging and querying for all AEGIS forge executions.
    """

    def __init__(self, db_path: Path = None):
        """
        Args:
            db_path: Path to SQLite database (default: ./aegis_metrics.db)
        """
        self.db_path = Path(db_path or "./aegis_metrics.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache for real-time updates (last 100 events)
        self.recent_events = deque(maxlen=100)

        # Subscribers for real-time updates
        self.subscribers = []

        # Initialize database
        self._init_database()

        logger.info(f"✓ AEGIS Metrics Engine initialized at {self.db_path}")

    def _init_database(self):
        """Create metrics tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS forge_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                concept TEXT NOT NULL,
                debate_rounds INTEGER,
                
                layer2_success BOOLEAN,
                layer2_time REAL,
                layer3_success BOOLEAN,
                layer3_time REAL,
                layer5_healing_applied BOOLEAN,
                layer5_time REAL,
                healing_action TEXT,
                healing_magnitude REAL,
                healing_reason TEXT,
                layer6_valid BOOLEAN,
                layer6_time REAL,
                overlap_percentage REAL,
                overlap_valid BOOLEAN,
                
                total_time REAL,
                valid BOOLEAN,
                forge_time REAL,
                alerts TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Statistics cache table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT UNIQUE,
                metric_value REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Healing log (for UI display)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS healing_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                concept TEXT NOT NULL,
                healing_action TEXT,
                healing_magnitude REAL,
                healing_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()
        conn.close()

    def log_forge_execution(self, metrics: Any) -> int:
        """
        Log a single forge execution cycle.

        Args:
            metrics: ForgeExecutionMetrics dataclass instance (or dict)

        Returns:
            Row ID of inserted record
        """
        # Convert dataclass to dict if needed
        if hasattr(metrics, "__dataclass_fields__"):
            data = asdict(metrics)
        else:
            data = metrics

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO forge_executions (
                    timestamp, concept, debate_rounds,
                    layer2_success, layer2_time,
                    layer3_success, layer3_time,
                    layer5_healing_applied, layer5_time,
                    healing_action, healing_magnitude, healing_reason,
                    layer6_valid, layer6_time,
                    overlap_percentage, overlap_valid,
                    total_time, valid, forge_time, alerts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get("timestamp"),
                    data.get("concept", ""),
                    data.get("debate_rounds", 2),
                    data.get("layer2_success", False),
                    data.get("layer2_time", 0.0),
                    data.get("layer3_success", False),
                    data.get("layer3_time", 0.0),
                    data.get("layer5_healing_applied", False),
                    data.get("layer5_time", 0.0),
                    data.get("healing_action", ""),
                    data.get("healing_magnitude", 0.0),
                    data.get("healing_reason", ""),
                    data.get("layer6_valid", False),
                    data.get("layer6_time", 0.0),
                    data.get("overlap_percentage", 0.0),
                    data.get("overlap_valid", False),
                    data.get("total_time", 0.0),
                    data.get("valid", False),
                    data.get("forge_time", 0.0),
                    json.dumps(data.get("alerts", [])),
                ),
            )

            row_id = cursor.lastrowid

            # Log healing separately
            if data.get("healing_action") and data.get("healing_action") != "none":
                cursor.execute(
                    """
                    INSERT INTO healing_log (timestamp, concept, healing_action, healing_magnitude, healing_reason)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        data.get("timestamp"),
                        data.get("concept", ""),
                        data.get("healing_action"),
                        data.get("healing_magnitude", 0.0),
                        data.get("healing_reason", ""),
                    ),
                )

            conn.commit()

            # Add to in-memory cache
            self.recent_events.append(
                {
                    "row_id": row_id,
                    "timestamp": data.get("timestamp"),
                    "concept": data.get("concept", "")[:50],
                    "healing_action": data.get("healing_action"),
                    "valid": data.get("valid"),
                    "layer5_healing": data.get("layer5_healing_applied"),
                }
            )

            # Notify subscribers
            self._notify_subscribers(
                {
                    "type": "forge_execution",
                    "row_id": row_id,
                    "concept": data.get("concept", "")[:50],
                    "healing_action": data.get("healing_action"),
                    "valid": data.get("valid"),
                    "timestamp": data.get("timestamp"),
                }
            )

            logger.debug(f"Logged forge execution: {data.get('concept', '')[:30]}...")

            return row_id

        except Exception as e:
            logger.error(f"Failed to log forge execution: {e}")
            conn.rollback()
            return -1

        finally:
            conn.close()

    def get_statistics(self, hours: int = 24) -> Dict:
        """
        Get summary statistics over the specified time period.

        Args:
            hours: Number of hours to look back (default 24)

        Returns:
            Dict with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = time.time() - (hours * 3600)

        try:
            # Total forge calls
            cursor.execute("SELECT COUNT(*) FROM forge_executions WHERE timestamp > ?", (cutoff_time,))
            total_calls = cursor.fetchone()[0]

            # Successful cycles
            cursor.execute("SELECT COUNT(*) FROM forge_executions WHERE valid = 1 AND timestamp > ?", (cutoff_time,))
            valid_calls = cursor.fetchone()[0]

            # Rejected cycles
            cursor.execute("SELECT COUNT(*) FROM forge_executions WHERE valid = 0 AND timestamp > ?", (cutoff_time,))
            invalid_calls = cursor.fetchone()[0]

            # Healing actions
            cursor.execute(
                "SELECT COUNT(*) FROM forge_executions WHERE layer5_healing_applied = 1 AND timestamp > ?",
                (cutoff_time,),
            )
            healing_applied = cursor.fetchone()[0]

            # Healing by action type
            cursor.execute(
                """
                SELECT healing_action, COUNT(*) as count
                FROM forge_executions
                WHERE layer5_healing_applied = 1 AND timestamp > ?
                GROUP BY healing_action
                """,
                (cutoff_time,),
            )
            healing_distribution = {row[0]: row[1] for row in cursor.fetchall()}

            # Layer 6 validation stats
            cursor.execute(
                "SELECT COUNT(*) FROM forge_executions WHERE overlap_valid = 1 AND timestamp > ?",
                (cutoff_time,),
            )
            overlap_valid = cursor.fetchone()[0]

            # Average overlap percentage
            cursor.execute(
                "SELECT AVG(overlap_percentage) FROM forge_executions WHERE timestamp > ?",
                (cutoff_time,),
            )
            avg_overlap = cursor.fetchone()[0] or 0.0

            # Average timings
            cursor.execute(
                """
                SELECT
                    AVG(layer2_time),
                    AVG(layer3_time),
                    AVG(layer5_time),
                    AVG(layer6_time),
                    AVG(total_time)
                FROM forge_executions WHERE timestamp > ?
                """,
                (cutoff_time,),
            )
            timings = cursor.fetchone()

            # Recent healing events
            cursor.execute(
                """
                SELECT timestamp, concept, healing_action, healing_magnitude
                FROM healing_log
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
                """,
                (cutoff_time,),
            )
            recent_healing = [
                {
                    "timestamp": row[0],
                    "concept": row[1][:50],
                    "action": row[2],
                    "magnitude": row[3],
                }
                for row in cursor.fetchall()
            ]

            stats = {
                "time_window_hours": hours,
                "total_forge_calls": total_calls,
                "valid_calls": valid_calls,
                "invalid_calls": invalid_calls,
                "rejection_rate": (invalid_calls / total_calls * 100) if total_calls > 0 else 0.0,
                "layer5_healing_applied": healing_applied,
                "healing_rate": (healing_applied / total_calls * 100) if total_calls > 0 else 0.0,
                "healing_distribution": healing_distribution,
                "layer6_overlap_valid": overlap_valid,
                "avg_overlap_percentage": round(avg_overlap, 2),
                "avg_timings": {
                    "layer2_ms": round((timings[0] or 0.0) * 1000, 2),
                    "layer3_ms": round((timings[1] or 0.0) * 1000, 2),
                    "layer5_ms": round((timings[2] or 0.0) * 1000, 2),
                    "layer6_ms": round((timings[3] or 0.0) * 1000, 2),
                    "total_ms": round((timings[4] or 0.0) * 1000, 2),
                },
                "recent_healing_events": recent_healing,
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

        finally:
            conn.close()

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get most recent forge executions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT
                    id, timestamp, concept, healing_action, valid,
                    overlap_percentage, layer5_healing_applied
                FROM forge_executions
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

            events = [
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "concept": row[2][:50],
                    "healing_action": row[3],
                    "valid": bool(row[4]),
                    "overlap_percentage": row[5],
                    "healing_applied": bool(row[6]),
                }
                for row in cursor.fetchall()
            ]

            return events

        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

        finally:
            conn.close()

    def get_healing_log(self, limit: int = 50) -> List[Dict]:
        """Get healing actions from the healing log."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT timestamp, concept, healing_action, healing_magnitude, healing_reason
                FROM healing_log
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

            events = [
                {
                    "timestamp": datetime.fromtimestamp(row[0]).isoformat(),
                    "concept": row[1][:50],
                    "action": row[2],
                    "magnitude": round(row[3], 3),
                    "reason": row[4],
                }
                for row in cursor.fetchall()
            ]

            return events

        except Exception as e:
            logger.error(f"Failed to get healing log: {e}")
            return []

        finally:
            conn.close()

    def subscribe_to_updates(self, callback: Callable):
        """
        Subscribe to real-time metric updates.

        Args:
            callback: Function(event_dict) called on each metric
        """
        self.subscribers.append(callback)
        logger.info(f"Subscriber added (total: {len(self.subscribers)})")

    def _notify_subscribers(self, event: Dict):
        """Notify all subscribers of a metric event."""
        for callback in self.subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.debug(f"Subscriber callback failed: {e}")

    def print_status_report(self):
        """Print a human-readable status report."""
        stats = self.get_statistics(hours=24)
        healing_log = self.get_healing_log(limit=5)

        print("\n" + "=" * 70)
        print("AEGIS Metrics Status Report (Last 24 Hours)")
        print("=" * 70)
        print(f"Total Forge Calls:     {stats.get('total_forge_calls', 0)}")
        print(f"Valid Cycles:          {stats.get('valid_calls', 0)}")
        print(f"Rejected Cycles:       {stats.get('invalid_calls', 0)}")
        print(f"Rejection Rate:        {stats.get('rejection_rate', 0.0):.1f}%")
        print()
        print(f"Layer 5 Healings:      {stats.get('layer5_healing_applied', 0)}")
        print(f"Healing Rate:          {stats.get('healing_rate', 0.0):.1f}%")
        print(f"Healing Distribution:  {stats.get('healing_distribution', {})}")
        print()
        print(f"Layer 6 Overlap Valid:  {stats.get('layer6_overlap_valid', 0)}")
        print(f"Avg Overlap %:         {stats.get('avg_overlap_percentage', 0.0)}%")
        print()
        print("Average Timings:")
        timings = stats.get("avg_timings", {})
        print(f"  Layer 2: {timings.get('layer2_ms', 0):.1f}ms")
        print(f"  Layer 3: {timings.get('layer3_ms', 0):.1f}ms")
        print(f"  Layer 5: {timings.get('layer5_ms', 0):.1f}ms")
        print(f"  Layer 6: {timings.get('layer6_ms', 0):.1f}ms")
        print(f"  TOTAL:   {timings.get('total_ms', 0):.1f}ms")
        print()
        print("Recent Healing Events:")
        for event in healing_log[:5]:
            print(f"  • {event['action']}: {event['concept']}")
            print(f"    Reason: {event['reason']}")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("\n" + "=" * 70)
    print("AEGIS Metrics Engine — Demo")
    print("=" * 70)

    metrics = AEGISMetricsEngine(db_path="/tmp/test_aegis_metrics.db")

    # Simulate some forge execution
    from aegis_forge_integration import ForgeExecutionMetrics

    for i in range(5):
        test_metrics = ForgeExecutionMetrics(
            concept=f"Test concept {i}",
            timestamp=time.time(),
            debate_rounds=2,
            layer2_success=True,
            layer3_success=True,
            layer5_healing_applied=(i % 2 == 0),
            healing_action="correction" if (i % 2 == 0) else "none",
            healing_magnitude=0.35 if (i % 2 == 0) else 0.0,
            healing_reason="High epistemic tension" if (i % 2 == 0) else "",
            layer6_valid=True,
            valid=True,
            overlap_percentage=85.0 + i * 2,
        )
        metrics.log_forge_execution(test_metrics)
        time.sleep(0.1)

    metrics.print_status_report()

    print("✓ Metrics engine demo complete\n")
