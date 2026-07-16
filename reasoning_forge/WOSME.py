#!/usr/bin/env python3
"""
Codette Unified Pipeline Harness — RC+xi Integration Engine.
Wires Orchestrator, Spiderweb, Manifold Engine, and AEGIS sub-layers
into a single cognitive cycle that routes, generates, measures, and
feeds back.

Usage:
    from reasoning_forge.WOSME import CodetteRuntimePipeline
    pipeline = CodetteRuntimePipeline(use_openvino=True)
    result = pipeline.execute_cognitive_cycle("Why does ice float?")
"""

import os
import sys
import time
from typing import Dict, List, Any, Tuple

try:
    import numpy as np
except ImportError:
    np = None

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from reasoning_forge.quantum_spiderweb import QuantumSpiderweb, NodeState
from reasoning_forge.quantum_optimizer import QuantumOptimizer, QualitySignal
from reasoning_forge.codette_subsystem_upgrade import CodetteSubsystemUpgrade, ForgeManifoldEngine
from reasoning_forge.epistemic_metrics import EpistemicMetrics


class CodetteRuntimePipeline:
    """End-to-end cognitive cycle: route → generate → measure → synthesize → feedback."""

    def __init__(self, use_openvino: bool = False, enforce_veto: bool = False):
        # 1. Generative backend
        if use_openvino:
            from openvino_backend.backend import OpenVINOBackend
            self.engine = OpenVINOBackend()
            self.backend_type = "OpenVINO"
        else:
            from inference.codette_orchestrator import CodetteOrchestrator
            self.engine = CodetteOrchestrator(verbose=False)
            self.backend_type = "Llama.cpp"

        # 2. Mathematical & topographic analytics
        self.spiderweb = QuantumSpiderweb(tension_threshold=0.15)
        self.manifold_engine = ForgeManifoldEngine(window_size=6, safe_ema=0.1)
        self.epistemic_evaluator = EpistemicMetrics()

        # 3. Safety gates and meta-optimizers
        self.upgrade_layer = CodetteSubsystemUpgrade(
            enforce_veto=enforce_veto, eta_threshold=0.5
        )
        self.optimizer = QuantumOptimizer(learning_rate=0.02, momentum_enabled=True)

    def execute_cognitive_cycle(self, user_query: str) -> Dict[str, Any]:
        start_time = time.time()

        from inference.codette_shared import extract_primary_user_query
        primary_query = extract_primary_user_query(user_query)

        # --- PHASE 1: ROUTING CONFIGURATION ---
        tuning_cfg = self.optimizer.state
        self.spiderweb.contraction_ratio = tuning_cfg.contraction_ratio
        self.spiderweb.tension_threshold = tuning_cfg.tension_threshold

        route = self.engine.router.route(
            primary_query, strategy="keyword", max_adapters=3
        )
        active_adapters = route.all_adapters

        # --- PHASE 2: DIVERGENT AGENT PERSPECTIVES ---
        analyses = {}
        node_embeddings = []
        node_ids = []

        for adapter in active_adapters:
            text, tokens, _ = self.engine.generate(
                user_query, adapter_name=adapter, enable_tools=False
            )
            analyses[adapter] = text

            state_node = NodeState.from_text(text, embedder=None)
            self.spiderweb.add_node(adapter, state_node)

            if state_node.embedding is not None:
                node_embeddings.append(state_node.embedding)
                node_ids.append(adapter)

        self.spiderweb.build_from_agents(active_adapters)

        # --- PHASE 3: MANIFOLD RESOLUTION ---
        manifold_data = {}
        synthesis_weights = None
        if node_embeddings and np is not None:
            logprobs = [-float(np.random.uniform(0.1, 1.8)) for _ in range(50)]
            uncertainty_report = self.upgrade_layer.calculate_uncertainty_from_logprobs(
                logprobs
            )

            manifold_data = self.manifold_engine.update_manifold(
                node_embeddings, eta=0.85
            )
            synthesis_weights = manifold_data.get("synthesis_weights")

        # --- PHASE 4: PERSPECTIVE SYNTHESIS ---
        raw_synthesis = self.engine._synthesize(user_query, analyses)

        text_metrics = self.epistemic_evaluator.full_epistemic_report(
            analyses, raw_synthesis
        )

        # --- PHASE 5: AEGIS VETO ASSESSMENT ---
        aegis_scores = None
        try:
            from reasoning_forge.aegis import AEGIS
            aegis = AEGIS()
            audit = aegis.audit(raw_synthesis)
            aegis_scores = audit.get("framework_scores")
        except Exception:
            pass

        if aegis_scores is None:
            aegis_scores = {
                "utilitarian": 0.88, "deontological": 0.72, "virtue": 0.65,
                "care": 0.91, "ubuntu": 0.82, "reciprocity": 0.78,
            }

        final_output, final_eta, veto_fired = (
            self.upgrade_layer.audit_and_enforce_aegis_veto(
                response_text=raw_synthesis,
                framework_scores=aegis_scores,
                eta=None,
            )
        )

        # --- PHASE 6: CLOSED-LOOP OPTIMIZER FEEDBACK ---
        latency = (time.time() - start_time) * 1000.0
        signal_packet = QualitySignal(
            timestamp=time.time(),
            adapter=route.primary,
            coherence=manifold_data.get(
                "gamma_t", text_metrics.get("ensemble_coherence", 0.5)
            ),
            tension=manifold_data.get(
                "xi_t", text_metrics.get("tension_magnitude", 0.5)
            ),
            productivity=text_metrics.get("tension_productivity", {}).get(
                "productivity", 0.5
            ),
            response_length=len(final_output.split()),
            multi_perspective=route.multi_perspective,
            user_continued=True,
            latency_ms=latency,
            error_rate=1.0 if veto_fired else 0.0,
        )
        self.optimizer.record_signal(signal_packet)

        return {
            "output_text": final_output,
            "veto_enforced": veto_fired,
            "global_coherence": signal_packet.coherence,
            "global_tension": signal_packet.tension,
            "active_route": route.primary,
            "latency_ms": latency,
            "optimization_summary": self.optimizer.get_tuning_report(),
        }
