#!/usr/bin/env python3
"""
AEGIS Metrics UI — Real-Time Web Dashboard
Flask-based dashboard for monitoring AEGIS protection layer metrics.

Features:
  - Real-time metrics display (rejection rate, healing frequency, etc.)
  - Healing event log with full details
  - Layer activation timings
  - Live alert streaming (WebSocket)

Usage:
    from aegis_metrics_ui import create_metrics_app
    
    app = create_metrics_app(metrics_engine)
    app.run(host="0.0.0.0", port=5000, debug=False)

Then visit: http://localhost:5000

Author: Jonathan Harrison / Codette Architecture
"""

import logging
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from flask import Flask, render_template, jsonify, request
    from flask_cors import CORS
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

logger = logging.getLogger(__name__)


def create_metrics_app(metrics_engine):
    """
    Create a Flask app for AEGIS metrics visualization.

    Args:
        metrics_engine: AEGISMetricsEngine instance

    Returns:
        Flask app
    """

    if not HAS_FLASK:
        logger.error("Flask not installed. Install with: pip install flask flask-cors")
        return None

    app = Flask(__name__)
    CORS(app)

    # =========================================================================
    # API ENDPOINTS
    # =========================================================================

    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        """Get summary statistics."""
        hours = request.args.get("hours", 24, type=int)
        stats = metrics_engine.get_statistics(hours=hours)
        return jsonify(stats)

    @app.route("/api/recent-events", methods=["GET"])
    def get_recent_events():
        """Get recent forge executions."""
        limit = request.args.get("limit", 50, type=int)
        events = metrics_engine.get_recent_events(limit=limit)
        return jsonify({"events": events})

    @app.route("/api/healing-log", methods=["GET"])
    def get_healing_log():
        """Get healing events log."""
        limit = request.args.get("limit", 50, type=int)
        log = metrics_engine.get_healing_log(limit=limit)
        return jsonify({"healing_events": log})

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

    # =========================================================================
    # WEB UI ENDPOINTS
    # =========================================================================

    @app.route("/", methods=["GET"])
    def index():
        """Main dashboard page."""
        return render_template("aegis_dashboard.html")

    @app.route("/healing", methods=["GET"])
    def healing_dashboard():
        """Healing events detailed view."""
        return render_template("aegis_healing.html")

    return app


# =====================================================================
# HTML TEMPLATES (Embedded)
# =====================================================================

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AEGIS Metrics Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
            color: #e0e0e0;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-left: 4px solid #4a9eff;
            border-radius: 8px;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #4a9eff, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .header p {
            color: #a0a0a0;
            font-size: 1em;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: rgba(74, 158, 255, 0.1);
            border: 1px solid rgba(74, 158, 255, 0.3);
            border-radius: 12px;
            padding: 20px;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }

        .metric-card:hover {
            background: rgba(74, 158, 255, 0.15);
            border-color: rgba(74, 158, 255, 0.6);
            transform: translateY(-2px);
        }

        .metric-label {
            font-size: 0.85em;
            color: #a0a0a0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }

        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #4a9eff;
            margin-bottom: 5px;
        }

        .metric-subtext {
            font-size: 0.8em;
            color: #707080;
        }

        .stat-good {
            color: #10b981;
        }

        .stat-warning {
            color: #f59e0b;
        }

        .stat-critical {
            color: #ef4444;
        }

        .section {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }

        .section-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #4a9eff;
            border-bottom: 2px solid rgba(74, 158, 255, 0.3);
            padding-bottom: 10px;
        }

        .events-table {
            width: 100%;
            border-collapse: collapse;
        }

        .events-table thead {
            background: rgba(74, 158, 255, 0.1);
        }

        .events-table th {
            text-align: left;
            padding: 12px;
            color: #4a9eff;
            font-weight: 600;
            border-bottom: 1px solid rgba(74, 158, 255, 0.2);
        }

        .events-table td {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .events-table tr:hover {
            background: rgba(74, 158, 255, 0.05);
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }

        .status-success {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.5);
        }

        .status-failed {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.5);
        }

        .healing-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            background: rgba(167, 139, 250, 0.2);
            color: #a78bfa;
            border: 1px solid rgba(167, 139, 250, 0.5);
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #a0a0a0;
        }

        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(74, 158, 255, 0.2);
            border-top-color: #4a9eff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #707080;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🛡️ AEGIS Protection Layer Dashboard</h1>
            <p>Real-time monitoring of Codette ForgeEngine safeguards</p>
        </div>

        <!-- Metrics Grid -->
        <div class="metrics-grid" id="metricsGrid">
            <div class="metric-card">
                <div class="metric-label">Forge Calls (24h)</div>
                <div class="metric-value" id="forgeCalls">-</div>
                <div class="metric-subtext">Total executions</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Valid Cycles</div>
                <div class="metric-value stat-good" id="validCalls">-</div>
                <div class="metric-subtext"><span id="validRate">-</span>% success rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Rejection Rate</div>
                <div class="metric-value" id="rejectionRate">-</div>
                <div class="metric-subtext"><span id="rejectedCount">-</span> rejected</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Layer 5 Healings</div>
                <div class="metric-value stat-good" id="healingApplied">-</div>
                <div class="metric-subtext"><span id="healingRate">-</span>% healing rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Overlap %</div>
                <div class="metric-value" id="avgOverlap">-</div>
                <div class="metric-subtext">Layer 6 validation</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Latency</div>
                <div class="metric-value" id="totalLatency">-</div>
                <div class="metric-subtext">Average per cycle</div>
            </div>
        </div>

        <!-- Recent Events -->
        <div class="section">
            <div class="section-title">📊 Recent Forge Executions</div>
            <div id="recentEventsContainer" class="loading">
                <div class="spinner"></div> Loading...
            </div>
        </div>

        <!-- Healing Log -->
        <div class="section">
            <div class="section-title">✨ Healing Events Log</div>
            <div id="healingLogContainer" class="loading">
                <div class="spinner"></div> Loading...
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>AEGIS Metrics Engine • Last updated: <span id="lastUpdate">-</span></p>
        </div>
    </div>

    <script>
        const STATS_POLL_INTERVAL = 5000; // 5 seconds
        const EVENTS_POLL_INTERVAL = 10000; // 10 seconds

        async function loadStats() {
            try {
                const response = await fetch('/api/stats?hours=24');
                const stats = await response.json();

                // Update metrics
                document.getElementById('forgeCalls').textContent = stats.total_forge_calls || 0;
                document.getElementById('validCalls').textContent = stats.valid_calls || 0;
                document.getElementById('validRate').textContent = Math.round(100 - (stats.rejection_rate || 0));
                document.getElementById('rejectionRate').textContent = 
                    ((stats.rejection_rate || 0).toFixed(1)) + '%';
                document.getElementById('rejectedCount').textContent = stats.invalid_calls || 0;
                document.getElementById('healingApplied').textContent = stats.layer5_healing_applied || 0;
                document.getElementById('healingRate').textContent = Math.round(stats.healing_rate || 0);
                document.getElementById('avgOverlap').textContent = 
                    ((stats.avg_overlap_percentage || 0).toFixed(1)) + '%';
                document.getElementById('totalLatency').textContent = 
                    ((stats.avg_timings?.total_ms || 0).toFixed(0)) + 'ms';

                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        }

        async function loadRecentEvents() {
            try {
                const response = await fetch('/api/recent-events?limit=20');
                const data = await response.json();

                let html = '<table class="events-table"><thead><tr>' +
                    '<th>Time</th><th>Concept</th><th>Healing</th><th>Overlap</th><th>Status</th></tr></thead><tbody>';

                data.events.forEach(event => {
                    const time = new Date(event.timestamp * 1000).toLocaleTimeString();
                    const healingBadge = event.healing_action && event.healing_action !== 'none' ?
                        `<span class="healing-badge">${event.healing_action}</span>` : '-';
                    const statusBadge = event.valid ?
                        '<span class="status-badge status-success">✓ Valid</span>' :
                        '<span class="status-badge status-failed">✗ Failed</span>';

                    html += `<tr>
                        <td>${time}</td>
                        <td>${event.concept}</td>
                        <td>${healingBadge}</td>
                        <td>${(event.overlap_percentage || 0).toFixed(1)}%</td>
                        <td>${statusBadge}</td>
                    </tr>`;
                });

                html += '</tbody></table>';
                document.getElementById('recentEventsContainer').innerHTML = html;
            } catch (error) {
                console.error('Failed to load recent events:', error);
                document.getElementById('recentEventsContainer').innerHTML =
                    '<p style="color: #ef4444;">Failed to load events</p>';
            }
        }

        async function loadHealingLog() {
            try {
                const response = await fetch('/api/healing-log?limit=20');
                const data = await response.json();

                let html = '<table class="events-table"><thead><tr>' +
                    '<th>Time</th><th>Concept</th><th>Action</th><th>Magnitude</th><th>Reason</th></tr></thead><tbody>';

                data.healing_events.forEach(event => {
                    html += `<tr>
                        <td>${event.timestamp}</td>
                        <td>${event.concept}</td>
                        <td><span class="healing-badge">${event.action}</span></td>
                        <td>${event.magnitude.toFixed(3)}</td>
                        <td>${event.reason}</td>
                    </tr>`;
                });

                html += '</tbody></table>';
                document.getElementById('healingLogContainer').innerHTML = html;
            } catch (error) {
                console.error('Failed to load healing log:', error);
                document.getElementById('healingLogContainer').innerHTML =
                    '<p style="color: #ef4444;">Failed to load healing log</p>';
            }
        }

        // Initial load
        loadStats();
        loadRecentEvents();
        loadHealingLog();

        // Periodic updates
        setInterval(loadStats, STATS_POLL_INTERVAL);
        setInterval(loadRecentEvents, EVENTS_POLL_INTERVAL);
        setInterval(loadHealingLog, EVENTS_POLL_INTERVAL);
    </script>
</body>
</html>
"""


# =====================================================================
# Register templates with Flask
# =====================================================================

def register_templates(app):
    """Register embedded HTML templates with Flask."""
    from flask import render_template_string

    @app.route("/")
    def index():
        return render_template_string(DASHBOARD_TEMPLATE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not HAS_FLASK:
        print("\n⚠️  Flask not installed. Install with:\n  pip install flask flask-cors\n")
        exit(1)

    from aegis_metrics_engine import AEGISMetricsEngine

    print("\n" + "=" * 70)
    print("AEGIS Metrics UI — Starting Dashboard")
    print("=" * 70)

    metrics = AEGISMetricsEngine(db_path="./aegis_metrics.db")
    app = create_metrics_app(metrics)

    if app:
        register_templates(app)
        print(f"\n✓ Dashboard available at http://localhost:5000")
        print("  Press Ctrl+C to stop\n")
        app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        print("\n✗ Failed to create Flask app\n")
