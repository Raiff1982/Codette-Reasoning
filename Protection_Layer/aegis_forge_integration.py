#!/usr/bin/env python3
"""
AEGIS Forge Integration — ForgeEngine Wrapper with Full Safeguards
Drops directly into ForgeEngine to apply all protection layers transparently.

Architecture:
  forge_engine.forge_with_debate()
           ↓
  AEGISForgeIntegration.forge_with_full_safeguards()
           ↓
  [Layer 2: Filesystem] → [Layer 3: Boot] → [Original Forge] → 
  [Layer 5: Healing] → [Layer 6: RenderLayer] → [Metrics Logging] → Result

Usage:
    from aegis_forge_integration import AEGISForgeIntegration
    
    integration = AEGISForgeIntegration(forge_engine, metrics_engine)
    result = integration.forge_with_full_safeguards(concept="...", debate_rounds=2)

Author: Jonathan Harrison / Codette Architecture
"""

import logging
import time
import json
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ForgeExecutionMetrics:
    """Track execution of a single forge cycle."""
    
    concept: str
    timestamp: float
    debate_rounds: int
    
    # Layer timings
    layer2_time: float = 0.0
    layer3_time: float = 0.0
    layer5_time: float = 0.0
    layer6_time: float = 0.0
    forge_time: float = 0.0
    total_time: float = 0.0
    
    # Layer status
    layer2_success: bool = False
    layer3_success: bool = False
    layer5_healing_applied: bool = False
    layer6_valid: bool = False
    
    # Layer 5 healing details
    healing_action: Optional[str] = None
    healing_magnitude: float = 0.0
    healing_reason: str = ""
    
    # Layer 6 validation details
    overlap_percentage: float = 0.0
    overlap_valid: bool = False
    
    # Overall result
    valid: bool = False
    alerts: list = None
    
    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []


class AEGISForgeIntegration:
    """
    Drop-in wrapper for ForgeEngine that applies all AEGIS protection layers.
    """

    def __init__(self, forge_engine, metrics_engine=None, workspace_dir: Path = None):
        """
        Args:
            forge_engine: ForgeEngine instance
            metrics_engine: AEGISMetricsEngine for centralized logging
            workspace_dir: Project root for Layer 2 isolation
        """
        self.forge_engine = forge_engine
        self.metrics_engine = metrics_engine
        self.workspace_dir = workspace_dir or Path.cwd()

        # Import AEGIS layers
        try:
            from aegis_orchestrator import AEGISOrchestrator
            from aegis_layer5_complete import PreEmptiveImmuneEngine
            from aegis_layer6_complete import RenderLayer

            self.orchestrator = AEGISOrchestrator(
                forge_engine=forge_engine,
                workspace_dir=workspace_dir,
                use_layer2=True,
                use_layer3=True,
                use_layer5=True,
                use_layer6=True,
                require_full_isolation=False,
            )
            self.PreEmptiveImmuneEngine = PreEmptiveImmuneEngine
            self.RenderLayer = RenderLayer

            logger.info("✓ AEGIS layers loaded successfully")
        except ImportError as e:
            logger.warning(f"⚠️  AEGIS layers not available: {e}")
            self.orchestrator = None

    def forge_with_full_safeguards(
        self, concept: str, debate_rounds: int = 2, user_context: Optional[Dict] = None
    ) -> Dict:
        """
        Full forge cycle with all AEGIS protection layers.

        Args:
            concept: User query
            debate_rounds: Number of debate rounds
            user_context: Optional context

        Returns:
            Dict with result + metrics
        """

        metrics = ForgeExecutionMetrics(
            concept=concept, timestamp=time.time(), debate_rounds=debate_rounds
        )

        result = {
            "concept": concept,
            "timestamp": metrics.timestamp,
            "synthesis": None,
            "valid": False,
            "alerts": [],
            "cocoon": {},
            "metrics": None,
        }

        if not self.orchestrator:
            logger.error("AEGIS orchestrator unavailable, running unprotected forge")
            result["synthesis"] = self.forge_engine.forge_with_debate(concept, debate_rounds=debate_rounds)
            return result

        try:
            # ── Layer 2: Filesystem Isolation ──────────────────────────────
            logger.info("[AEGIS] Activating Layer 2 (Filesystem Isolation)...")
            t0 = time.time()
            l2_ok, l2_msg = self.orchestrator.activate_layer2_filesystem_isolation()
            metrics.layer2_time = time.time() - t0
            metrics.layer2_success = l2_ok
            logger.info(f"  Layer 2: {l2_msg} ({metrics.layer2_time*1000:.1f}ms)")

            # ── Layer 3: Boot Integrity ────────────────────────────────────
            logger.info("[AEGIS] Activating Layer 3 (Boot Integrity)...")
            t0 = time.time()
            l3_ok, l3_report = self.orchestrator.activate_layer3_boot_verification()
            metrics.layer3_time = time.time() - t0
            metrics.layer3_success = l3_ok
            logger.info(f"  Layer 3: {l3_report.get('summary', 'unknown')} ({metrics.layer3_time*1000:.1f}ms)")

            # ── Run ForgeEngine ────────────────────────────────────────────
            logger.info("[ForgeEngine] Running core reasoning...")
            t0 = time.time()
            try:
                forge_result = self.forge_engine.forge_with_debate(concept, debate_rounds=debate_rounds)
            except Exception as e:
                logger.exception(f"ForgeEngine failed: {e}")
                result["alerts"].append(f"ForgeEngine error: {e}")
                metrics.valid = False
                result["metrics"] = asdict(metrics)
                self._log_metrics(metrics)
                return result

            metrics.forge_time = time.time() - t0
            logger.info(f"  ForgeEngine complete ({metrics.forge_time*1000:.1f}ms)")

            # Extract key outputs
            messages = forge_result.get("messages", [])
            user_facing_synthesis = None
            for msg in messages:
                if msg.get("role") == "assistant":
                    user_facing_synthesis = msg.get("content", "")
                    break

            cocoon = forge_result.get("cocoon", {})
            authored_state = forge_result.get("authored_state", {})

            # ── Layer 5: Pre-Emptive Healing ───────────────────────────────
            logger.info("[AEGIS] Activating Layer 5 (Pre-Emptive Healing)...")
            t0 = time.time()

            healing_action = None
            healing_info = {}

            if authored_state and cocoon:
                embedding = authored_state.get("evidence_vector", [0.5] * 128)
                intent = [0.1] * 128

                healed_state, healing_info = self.orchestrator.activate_layer5_healing(embedding, intent, cocoon)

                metrics.layer5_time = time.time() - t0
                metrics.layer5_healing_applied = healing_info.get("action") != "none"
                metrics.healing_action = healing_info.get("action")
                metrics.healing_magnitude = float(healing_info.get("magnitude", 0.0))
                metrics.healing_reason = str(healing_info.get("reason", ""))

                # Add healing metadata to cocoon for Layer 6 validation
                if not cocoon.get("healing_metadata"):
                    cocoon["healing_metadata"] = {}

                cocoon["healing_metadata"] = {
                    "action": healing_info.get("action"),
                    "magnitude": healing_info.get("magnitude"),
                    "reason": healing_info.get("reason"),
                    "timestamp": time.time(),
                    "applied": metrics.layer5_healing_applied,
                }

                logger.info(f"  Layer 5: {healing_info.get('action')} ({metrics.layer5_time*1000:.1f}ms)")
            else:
                metrics.layer5_time = time.time() - t0
                logger.warning("  Layer 5: Skipped (no authored_state or cocoon)")

            # ── Layer 6: RenderLayer Validation ────────────────────────────
            logger.info("[AEGIS] Activating Layer 6 (RenderLayer Validation)...")
            t0 = time.time()

            if user_facing_synthesis:
                l6_ok, l6_report = self.orchestrator.activate_layer6_validation(
                    authored_state, user_facing_synthesis, cocoon
                )

                metrics.layer6_time = time.time() - t0
                metrics.layer6_valid = l6_ok
                metrics.overlap_valid = l6_report.get("validation_steps", {}).get("word_overlap", {}).get("valid", False)
                metrics.overlap_percentage = (
                    l6_report.get("validation_steps", {}).get("word_overlap", {}).get("details", {}).get("overlap_percentage", 0.0)
                )

                logger.info(f"  Layer 6: {'PASS' if l6_ok else 'FAIL'} ({metrics.layer6_time*1000:.1f}ms)")

                if not l6_ok:
                    result["alerts"].extend(l6_report.get("alerts", []))
            else:
                metrics.layer6_time = time.time() - t0
                logger.warning("  Layer 6: Skipped (no user_facing_synthesis)")

            # ── Final Assembly ────────────────────────────────────────────
            metrics.total_time = time.time() - metrics.timestamp
            metrics.valid = metrics.layer6_valid if user_facing_synthesis else True

            result["synthesis"] = user_facing_synthesis
            result["cocoon"] = cocoon
            result["messages"] = messages
            result["valid"] = metrics.valid
            result["metrics"] = asdict(metrics)

            logger.info(f"✓ [AEGIS] Forge cycle complete ({metrics.total_time*1000:.1f}ms total)")

            # Log metrics to centralized engine
            self._log_metrics(metrics)

            return result

        except Exception as e:
            logger.exception(f"AEGIS integration failed: {e}")
            result["alerts"].append(f"AEGIS error: {e}")
            metrics.valid = False
            result["metrics"] = asdict(metrics)
            self._log_metrics(metrics)
            return result

    def _log_metrics(self, metrics: ForgeExecutionMetrics):
        """Send metrics to centralized logging engine."""
        if self.metrics_engine:
            try:
                self.metrics_engine.log_forge_execution(metrics)
                logger.debug(f"Metrics logged: {metrics.concept[:30]}...")
            except Exception as e:
                logger.debug(f"Metrics logging failed: {e}")


# =====================================================================
# BACKWARDS COMPATIBILITY: Monkey-patch ForgeEngine
# =====================================================================

def patch_forge_engine(forge_engine, metrics_engine=None, workspace_dir: Path = None):
    """
    Monkey-patch ForgeEngine to use AEGIS-wrapped forge_with_debate.

    Usage:
        from aegis_forge_integration import patch_forge_engine
        patch_forge_engine(forge_engine, metrics_engine)
        result = forge_engine.forge_with_debate(concept)  # Now uses AEGIS!
    """
    integration = AEGISForgeIntegration(forge_engine, metrics_engine, workspace_dir)
    original_forge = forge_engine.forge_with_debate

    def wrapped_forge_with_debate(concept: str, debate_rounds: int = 2, **kwargs):
        return integration.forge_with_full_safeguards(
            concept, debate_rounds=debate_rounds, user_context=kwargs.get("user_context")
        )

    forge_engine.forge_with_debate_original = original_forge
    forge_engine.forge_with_debate = wrapped_forge_with_debate
    forge_engine.forge_with_aegis_safeguards = wrapped_forge_with_debate

    logger.info("✓ ForgeEngine patched with AEGIS safeguards")
    return integration


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("\n✓ AEGIS ForgeEngine Integration module loaded\n")
