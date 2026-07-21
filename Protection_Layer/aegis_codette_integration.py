#!/usr/bin/env python3
"""
AEGIS Integration for Codette Web Server
Adds metrics endpoints to existing codette_server.py without modifying it directly.

Usage:
    # At the top of codette_server.py (after imports):
    from aegis_codette_integration import integrate_aegis_metrics
    
    # After the CodetteHandler class definition:
    integrate_aegis_metrics(app_reference)

Author: Jonathan Harrison
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def integrate_aegis_metrics(handler_class):
    """
    Patch a CodetteHandler class to add AEGIS metrics endpoints.
    
    This is called after the CodetteHandler class is defined in codette_server.py
    to inject new do_GET/do_POST handlers without modifying the original file.
    
    Args:
        handler_class: The CodetteHandler class from codette_server.py
    """
    
    # Import AEGIS components
    try:
        from aegis_forge_integration import AEGISForgeIntegration, patch_forge_engine
        from aegis_metrics_engine import AEGISMetricsEngine
        logger.info("✓ AEGIS metrics integration loaded")
    except ImportError as e:
        logger.warning(f"AEGIS integration not available: {e}")
        return
    
    # Initialize metrics engine (singleton)
    metrics_db_path = Path.cwd() / "aegis_metrics.db"
    global _aegis_metrics_engine
    _aegis_metrics_engine = AEGISMetricsEngine(db_path=metrics_db_path)
    
    # Store original do_GET and do_POST
    original_do_get = handler_class.do_GET
    original_do_post = handler_class.do_POST
    
    # Define patched do_GET that intercepts AEGIS metrics endpoints
    def patched_do_GET(self):
        """Patched do_GET that handles AEGIS metrics endpoints."""
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(self.path)
        path = parsed.path
        
        # AEGIS metrics endpoints
        if path == "/api/aegis/stats":
            try:
                hours = parse_qs(parsed.query).get("hours", ["24"])[0]
                hours = int(hours)
            except (ValueError, IndexError):
                hours = 24
            
            stats = _aegis_metrics_engine.get_statistics(hours=hours)
            self._json_response(stats)
            return
        
        elif path == "/api/aegis/recent-events":
            try:
                limit = parse_qs(parsed.query).get("limit", ["50"])[0]
                limit = int(limit)
            except (ValueError, IndexError):
                limit = 50
            
            events = _aegis_metrics_engine.get_recent_events(limit=limit)
            self._json_response({"events": events})
            return
        
        elif path == "/api/aegis/healing-log":
            try:
                limit = parse_qs(parsed.query).get("limit", ["50"])[0]
                limit = int(limit)
            except (ValueError, IndexError):
                limit = 50
            
            healing_log = _aegis_metrics_engine.get_healing_log(limit=limit)
            self._json_response({"healing_events": healing_log})
            return
        
        # Fall back to original handler
        original_do_get(self)
    
    # Replace do_GET
    handler_class.do_GET = patched_do_GET
    
    logger.info("✓ AEGIS metrics endpoints registered (/api/aegis/*)")
    
    return _aegis_metrics_engine


def integrate_with_forge_engine(forge_engine, metrics_engine=None):
    """
    Wire AEGIS metrics logging into ForgeEngine.
    
    This patches forge_engine.forge_with_debate() to log all calls to the metrics engine.
    
    Args:
        forge_engine: The ForgeEngine instance
        metrics_engine: AEGISMetricsEngine (optional, will create if not provided)
    
    Returns:
        tuple: (metrics_engine, forge_integration)
    """
    
    try:
        from aegis_forge_integration import AEGISForgeIntegration, patch_forge_engine
        from aegis_metrics_engine import AEGISMetricsEngine
    except ImportError as e:
        logger.warning(f"AEGIS integration not available: {e}")
        return None, None
    
    # Create or use provided metrics engine
    if metrics_engine is None:
        metrics_db_path = Path.cwd() / "aegis_metrics.db"
        metrics_engine = AEGISMetricsEngine(db_path=metrics_db_path)
    
    # Create integration and patch ForgeEngine
    integration = AEGISForgeIntegration(
        forge_engine=forge_engine,
        metrics_engine=metrics_engine,
        workspace_dir=Path.cwd(),
    )
    
    patch_forge_engine(forge_engine, metrics_engine=metrics_engine)
    
    logger.info("✓ ForgeEngine patched with AEGIS metrics logging")
    
    return metrics_engine, integration


# Singleton instance (set by integrate_aegis_metrics)
_aegis_metrics_engine = None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("\n✓ AEGIS Codette Integration module loaded\n")
    print("Usage in codette_server.py:")
    print("  from aegis_codette_integration import integrate_aegis_metrics")
    print("  integrate_aegis_metrics(CodetteHandler)\n")
