#!/usr/bin/env python3
"""Codette Phase 6 Inference Bridge — ForgeEngine integration for web server

This module provides a bridge between codette_server.py and ForgeEngine,
enabling Phase 6 capabilities (query complexity routing, semantic tension,
specialization tracking, pre-flight prediction) without breaking the web UI.

Usage:
    from codette_forge_bridge import CodetteForgeBridge

    bridge = CodetteForgeBridge(orchestrator=orch, use_phase6=True)
    result = bridge.generate(query, adapter=None, max_adapters=2)

The bridge falls back to lightweight orchestrator if Phase 6 disabled or heavy.
"""

import logging
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional

_log = logging.getLogger(__name__)

# Substrate-aware cognition
try:
    from substrate_awareness import SubstrateMonitor, HealthAwareRouter, CocoonStateEnricher
    SUBSTRATE_AVAILABLE = True
except ImportError:
    SUBSTRATE_AVAILABLE = False

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from reasoning_forge.forge_engine import ForgeEngine
    from reasoning_forge.query_classifier import QueryClassifier, QueryComplexity
    from reasoning_forge.executive_controller import ExecutiveController, ComponentDecision
    PHASE6_AVAILABLE = True
    PHASE7_AVAILABLE = True
except ImportError as e:
    PHASE6_AVAILABLE = False
    PHASE7_AVAILABLE = False
    print(f"[WARNING] ForgeEngine not available - Phase 6/7 disabled: {e}")


class CodetteForgeBridge:
    """Bridge between web server (lightweight) and ForgeEngine (Phase 6)."""

    def __init__(self, orchestrator, use_phase6: bool = True, use_phase7: bool = True, verbose: bool = False, health_check_fn=None):
        """
        Args:
            orchestrator: CodetteOrchestrator instance for fallback
            use_phase6: Enable Phase 6 (requires ForgeEngine)
            use_phase7: Enable Phase 7 (Executive Controller routing)
            verbose: Log decisions
            health_check_fn: Callable that returns real system health dict
        """
        self.orchestrator = orchestrator
        self.verbose = verbose
        self._health_check_fn = health_check_fn
        self.use_phase6 = use_phase6 and PHASE6_AVAILABLE
        self.use_phase7 = use_phase7 and PHASE7_AVAILABLE

        # Substrate-aware cognition
        self.substrate_monitor = None
        self.health_router = None
        self.cocoon_enricher = None
        if SUBSTRATE_AVAILABLE:
            try:
                self.substrate_monitor = SubstrateMonitor()
                self.health_router = HealthAwareRouter(self.substrate_monitor)
                self.cocoon_enricher = CocoonStateEnricher(self.substrate_monitor)
                if self.verbose:
                    print("[SUBSTRATE] Substrate-aware cognition initialized")
            except Exception as e:
                print(f"[WARNING] Substrate awareness init failed: {e}")

        self.forge = None
        self.classifier = None
        self.executive_controller = None

        if self.use_phase6:
            try:
                self._init_phase6()
            except Exception as e:
                print(f"[WARNING] Phase 6 initialization failed: {e}")
                self.use_phase6 = False

        if self.use_phase7 and self.use_phase6:
            try:
                self.executive_controller = ExecutiveController(verbose=verbose)
                if self.verbose:
                    print("[PHASE7] Executive Controller initialized - intelligent routing enabled")
            except Exception as e:
                print(f"[WARNING] Phase 7 initialization failed: {e}")
                self.use_phase7 = False

        # ── Render/cognition separation (Phase 8) ────────────────────────
        # CognitionSubstrate owns all reasoning; RenderLayer owns verbalization.
        # generate_v2() uses this pipeline; generate() is unchanged.
        self._substrate = None
        self._render_layer = None
        try:
            from inference.cognition_substrate import CognitionSubstrate
            from inference.render_layer import RenderLayer
            self._substrate = CognitionSubstrate(
                forge=self.forge,          # re-use already-initialised forge
                memory=None,               # substrate will lazy-init its own memory
                synthesizer=None,
                synthesis_v3=None,
            )
            self._render_layer = RenderLayer(llm_callable=None)  # template tier until LLM callable wired
            if self.verbose:
                print("[PHASE8] CognitionSubstrate + RenderLayer initialized")
        except Exception as e:
            print(f"[INFO] Phase 8 substrate not available: {e}")

    def _init_phase6(self):
        """Initialize ForgeEngine with Phase 6 components."""
        if self.verbose:
            print("[PHASE6] Initializing ForgeEngine...")

        self.forge = ForgeEngine(orchestrator=self.orchestrator)
        self.classifier = QueryClassifier()

        # Wire cocoon memories into orchestrator so they enrich LLM prompts
        if hasattr(self.forge, 'memory_kernel') and self.forge.memory_kernel:
            self.orchestrator.set_memory_kernel(self.forge.memory_kernel)
            if self.verbose:
                print(f"[PHASE6] Memory kernel wired to orchestrator ({len(self.forge.memory_kernel)} cocoon memories)")

        if self.verbose:
            print(f"[PHASE6] ForgeEngine ready with {len(self.forge.analysis_agents)} agents")

    def generate(self, query: str, adapter: Optional[str] = None,
                 max_adapters: int = 2, memory_budget: int = 3,
                 max_response_tokens: int = 512) -> Dict:
        """Generate response with optional Phase 6 routing.

        Args:
            query: User query
            adapter: Force specific adapter (bypasses routing)
            max_adapters: Max adapters for multi-perspective
            memory_budget: Max cocoons for forge memory injection (from BehaviorGovernor)
            max_response_tokens: Response length budget (from BehaviorGovernor)

        Returns:
            {
                "response": str,
                "adapter": str or list,
                "phase6_used": bool,
                "complexity": str,  # if Phase 6
                "conflicts_prevented": int,  # if Phase 6
                "reasoning": str,
                ...rest from orchestrator...
            }
        """
        start_time = time.time()
        user_query = self._extract_primary_user_query(query)

        # Greeting fast-path: bypass adapter analysis for pure social openers.
        # Adapters are fine-tuned for analysis and produce boilerplate on greetings.
        # Use base model + identity system prompt directly instead.
        #
        # Pattern: starts with a greeting word (word-boundary anchored).
        # Word-count guard (≤ 7 words) prevents "hey can you explain X" from
        # triggering the fast-path.  This catches:
        #   "hey codette its me", "hi there", "hello jonathan", "good morning", etc.
        _GREETING_RE = re.compile(
            r"^\s*(hi|hey|hello|howdy|sup|what'?s\s+up|good\s+(?:morning|afternoon|evening|night)|"
            r"greetings|yo|hiya|hola|salut|ciao|hallo)\b",
            re.IGNORECASE,
        )
        if _GREETING_RE.match(user_query) and len(user_query.split()) <= 7:
            try:
                from inference.codette_orchestrator import ADAPTER_PROMPTS
                mem_ctx = self.orchestrator._build_memory_context() if hasattr(self.orchestrator, '_build_memory_context') else ""
                sys_prompt = ADAPTER_PROMPTS["_base"] + mem_ctx
                result = self.orchestrator._llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_query},
                    ],
                    max_tokens=80,
                    temperature=0.7,
                    stop=["<|eot_id|>", "<|end_of_text|>"],
                )
                response = result["choices"][0]["message"]["content"].strip()
                tokens = result.get("usage", {}).get("completion_tokens", 0)
                elapsed = time.time() - start_time
                return {
                    "response": response,
                    "adapter": "_base",
                    "tokens": tokens,
                    "time": elapsed,
                    "phase6_used": True,
                    "complexity": "GREETING",
                    "reasoning": "Greeting fast-path — base model, no adapter analysis",
                }
            except Exception as _gex:
                if self.verbose:
                    print(f"[GREETING] Fast-path failed ({_gex}), falling through to normal routing")

        # Memory/identity fast-path: adapters deflect personal-memory questions as
        # a safety trained response ("I don't have memories"). Use base model and
        # inject seeds explicitly in the user turn so they're impossible to ignore.
        _MEMORY_RE = re.compile(
            r"\b(what do you (know|remember|recall) about me|"
            r"do you (know|remember) (who i am|me)|"
            r"who am i( to you)?|"
            r"what('?s| is) my name|"
            r"have we met|"
            r"tell me what you know about me)\b",
            re.IGNORECASE,
        )
        if _MEMORY_RE.search(user_query):
            try:
                from inference.codette_orchestrator import ADAPTER_PROMPTS
                kernel = getattr(self.orchestrator, '_memory_kernel', None)
                mem_facts = []
                if kernel and hasattr(kernel, 'memories'):
                    for m in kernel.memories:
                        if m.importance >= 7:
                            mem_facts.append(m.content)
                if mem_facts:
                    facts_block = "\n".join(f"- {f}" for f in mem_facts[:8])
                    user_msg = (
                        f"{user_query}\n\n"
                        f"[What I know from my memory right now]\n{facts_block}"
                    )
                else:
                    user_msg = user_query
                result = self.orchestrator._llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": ADAPTER_PROMPTS["_base"]},
                        {"role": "user", "content": user_msg},
                    ],
                    max_tokens=200,
                    temperature=0.7,
                    stop=["<|eot_id|>", "<|end_of_text|>"],
                )
                response = result["choices"][0]["message"]["content"].strip()
                tokens = result.get("usage", {}).get("completion_tokens", 0)
                elapsed = time.time() - start_time
                return {
                    "response": response,
                    "adapter": "_base",
                    "tokens": tokens,
                    "time": elapsed,
                    "phase6_used": True,
                    "complexity": "MEMORY_QUERY",
                    "reasoning": "Memory fast-path — seeds injected as user context",
                }
            except Exception as _mex:
                if self.verbose:
                    print(f"[MEMORY] Fast-path failed ({_mex}), falling through to normal routing")

        # Self-diagnostic: intercept health check queries before LLM
        _health_patterns = [
            r'\bself[\s-]*(?:diagnostic|system health)\b',
            r'system[\s-]*health[\s-]*check',
            r'\bhealth[\s-]*check\b',
            r'\bsystems?[\s-]*check\b',
            r'run[\s-]*(?:a\s+)?diagnostic',
            r'check\s+(?:your|all)\s+systems',
            r'health[\s-]*report',
            r'system[\s-]*status(?:[\s-]*report)?',
            r'how\s+are\s+your\s+systems',
        ]
        if any(re.search(p, user_query, re.I) for p in _health_patterns) and self._health_check_fn:
            try:
                health = self._health_check_fn()

                # Format as a natural response with real data
                lines = [f"**Self-System Health Check — {health['overall']}** ({health['score']} checks passed)\n"]

                for sys_name, sys_data in health.get("systems", {}).items():
                    status = sys_data.get("status", "?") if isinstance(sys_data, dict) else str(sys_data)
                    icon = "✅" if status == "OK" else ("⚠️" if status in ("DISABLED", "MISSING", "DEGRADED") else "❌")
                    label = sys_name.replace("_", " ").title()
                    lines.append(f"{icon} **{label}**: {status}")

                    # Add sub-details for key systems
                    if isinstance(sys_data, dict):
                        if "adapters_loaded" in sys_data:
                            lines.append(f"   └ {sys_data['adapters_loaded']} adapters: {', '.join(sys_data.get('adapters', []))}")
                        if "components" in sys_data:
                            for comp, cdata in sys_data["components"].items():
                                cstatus = cdata.get("status", "?") if isinstance(cdata, dict) else str(cdata)
                                cicon = "✅" if cstatus == "OK" else "❌"
                                comp_label = comp.replace("_", " ").title()
                                detail = ""
                                if isinstance(cdata, dict):
                                    if "memories" in cdata:
                                        detail = f" ({cdata['memories']} memories)"
                                    elif "audit_entries" in cdata:
                                        detail = f" ({cdata['audit_entries']} audit entries)"
                                    elif "stored_cocoons" in cdata:
                                        detail = f" ({cdata['stored_cocoons']} cocoons)"
                                lines.append(f"   {cicon} {comp_label}{detail}")
                        if "subsystems" in sys_data:
                            for sub, sstatus in sys_data["subsystems"].items():
                                sicon = "✅" if sstatus == "OK" else "❌"
                                lines.append(f"   {sicon} {sub}")
                        if "spiderweb_metrics" in sys_data:
                            sm = sys_data["spiderweb_metrics"]
                            lines.append(f"   └ Coherence: {sm.get('phase_coherence', 0):.4f}, Entropy: {sm.get('entropy', 0):.4f}, Nodes: {sm.get('node_count', 0)}, Attractors: {sm.get('attractor_count', 0)}, Glyphs: {sm.get('glyph_count', 0)}")
                        if "behavior_lessons" in sys_data:
                            lines.append(f"   └ {sys_data['behavior_lessons']} learned behaviors, {sys_data['permanent_locks']} permanent locks")
                        if "alive" in sys_data:
                            lines.append(f"   └ {sys_data['alive']}/{sys_data['total']} alive, {sys_data.get('pending_requests', 0)} pending")

                if health.get("warnings"):
                    lines.append(f"\n⚠️ **Warnings**: {', '.join(health['warnings'])}")
                if health.get("errors"):
                    lines.append(f"\n❌ **Errors**: {', '.join(health['errors'])}")

                return {
                    "response": "\n".join(lines),
                    "adapter": "self_diagnostic",
                    "tokens": 0,
                    "time": round(time.time() - start_time, 2),
                    "phase6_used": True,
                    "reasoning": "Real self-diagnostic (not LLM-generated)",
                    "health": health,
                }
            except Exception as e:
                pass  # Fall through to normal LLM generation

        # Ethical query validation (from original framework)
        if self.forge and hasattr(self.forge, 'ethical_governance') and self.forge.ethical_governance:
            try:
                qv = self.forge.ethical_governance.validate_query(user_query)
                if not qv["valid"]:
                    return {
                        "response": "I can't help with that request. " + "; ".join(qv.get("suggestions", [])),
                        "adapter": "ethical_block",
                        "tokens": 0,
                        "phase6_used": True,
                        "reasoning": "Blocked by EthicalAIGovernance",
                    }
            except Exception:
                pass  # Non-critical, continue

        # If adapter forced or Phase 6 disabled, use orchestrator directly
        if adapter or not self.use_phase6:
            result = self.orchestrator.route_and_generate(
                query,
                max_adapters=max_adapters,
                strategy="keyword",
                force_adapter=adapter,
            )
            result["phase6_used"] = False
            return result

        # Store governor budgets for forge access
        self._memory_budget = memory_budget
        self._max_response_tokens = max_response_tokens

        # Try Phase 6 route first
        try:
            return self._generate_with_phase6(query, max_adapters)
        except Exception as e:
            if self.verbose:
                print(f"[PHASE6] Error: {e} - falling back to orchestrator")

            # Fallback to orchestrator
            result = self.orchestrator.route_and_generate(
                query,
                max_adapters=max_adapters,
                strategy="keyword",
                force_adapter=None,
            )
            result["phase6_used"] = False
            result["phase6_fallback_reason"] = str(e)
            return result

    def generate_v2(
        self,
        query: str,
        constraints: Optional[list] = None,
        adapter: Optional[str] = None,
        max_response_tokens: int = 512,
    ) -> Dict:
        """
        Phase 8 pipeline: CognitionSubstrate → AuthoredState → RenderLayer.

        The LLM is a render-only surface.  All reasoning, conclusions, and
        evidence are authored upstream by the substrate before the LLM is
        invoked.  This is the render/cognition separation described in the
        Aura architecture review.

        Falls back to generate() if the substrate is unavailable.
        """
        if self._substrate is None or self._render_layer is None:
            _log.debug("[v2] substrate unavailable, falling back to generate()")
            return self.generate(query, adapter=adapter, max_response_tokens=max_response_tokens)

        start_time = time.time()
        try:
            # ── Step 1: Pure-Python cognition (no LLM) ───────────────────
            authored = self._substrate.process(query, constraints=constraints or [])

            # ── Step 2: Wire LLM callable into render layer ───────────────
            # Build a thin lambda so RenderLayer can call the orchestrator LLM
            # with strict verbalization constraints.
            def _llm_verbalize(prompt: str, system: str) -> str:
                result = self.orchestrator._llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt},
                    ],
                    max_tokens=max_response_tokens,
                    temperature=0.6,
                    stop=["<|eot_id|>", "<|end_of_text|>"],
                )
                return result["choices"][0]["message"]["content"].strip()

            self._render_layer.llm_callable = _llm_verbalize
            authored.render_tier = "llm"

            # ── Step 3: Render (LLM expresses authored state only) ────────
            response_text = self._render_layer.render(authored)

            # ── Step 4: Render integrity check ───────────────────────────
            integrity = self._render_layer.check_integrity(authored, response_text)
            if not integrity["passed"]:
                _log.warning(f"[v2] render integrity violations: {integrity['violations']}")

            # ── Step 5: Mirror cocoon to Supabase ─────────────────────────
            try:
                from supabase_sync import sync_cocoon as _sync_cocoon
                _sync_cocoon({
                    "query":           authored.query,
                    "response":        response_text,
                    "adapter":         authored.strategy,
                    "dominant_emotion": authored.dominant_emotion,
                    "cocoon_integrity_score": authored.confidence,
                    "version":         "v3_substrate",
                    "metadata":        authored.metadata,
                })
            except Exception:
                pass

            elapsed = time.time() - start_time
            return {
                "response":           response_text,
                "adapter":            authored.strategy,
                "phase6_used":        True,
                "phase8_substrate":   True,
                "complexity":         "SUBSTRATE",
                "reasoning":          f"CognitionSubstrate → {authored.strategy} → RenderLayer",
                "authored_state":     authored.to_dict(),
                "render_integrity":   integrity,
                "confidence":         authored.confidence,
                "tokens":             len(response_text.split()),
                "time":               elapsed,
            }

        except Exception as e:
            _log.warning(f"[v2] generate_v2 failed, falling back: {e}")
            return self.generate(query, adapter=adapter, max_response_tokens=max_response_tokens)

    def _generate_with_phase6(self, query: str, max_adapters: int) -> Dict:
        """Generate using orchestrator LLM with Phase 6/7 routing and classification.

        All complexity levels use the orchestrator for actual LLM inference.
        Phase 6 adds query classification and domain routing.
        Phase 7 adds executive routing metadata.
        """
        start_time = time.time()
        user_query = self._extract_primary_user_query(query)

        # 1. Classify query complexity (Phase 6)
        complexity = self.classifier.classify(user_query)
        if self.verbose:
            print(f"[PHASE6] Query complexity: {complexity}", flush=True)

        # 2. Route with Phase 7 Executive Controller
        route_decision = None
        if self.use_phase7 and self.executive_controller:
            route_decision = self.executive_controller.route_query(user_query, complexity)
            if self.verbose:
                print(f"[PHASE7] Route: {','.join([k for k, v in route_decision.component_activation.items() if v])}", flush=True)

        # 3. Domain classification for adapter routing
        domain = self._classify_domain(user_query)

        # 4. Determine adapter count based on complexity
        if complexity == QueryComplexity.SIMPLE:
            effective_max_adapters = 1
        elif complexity == QueryComplexity.MEDIUM:
            effective_max_adapters = min(max_adapters, 2)
        else:
            effective_max_adapters = max_adapters

        # 4.5 SUBSTRATE-AWARE ROUTING — adjust based on system pressure
        substrate_adjustments = []
        if self.health_router:
            original_complexity = complexity
            original_max = effective_max_adapters
            complexity, effective_max_adapters, substrate_adjustments = \
                self.health_router.adjust_routing(complexity, effective_max_adapters)
            if substrate_adjustments:
                for adj in substrate_adjustments:
                    print(f"  [SUBSTRATE] {adj}", flush=True)

        if self.verbose:
            print(f"[PHASE6] Domain: {domain}, max_adapters: {effective_max_adapters}", flush=True)

        # 4.7 Pre-Cognitive AEGIS Query Filter (lightweight)
        # Screen the query for harmful intent BEFORE spending 30-60s on inference.
        # Full AEGIS response evaluation still runs post-generation; this layer
        # catches clear dual-use, manipulation, or harmful-content signals early.
        _aegis_block = self._precognitive_aegis_check(user_query)
        if _aegis_block:
            return {
                "response": _aegis_block["message"],
                "complexity": str(complexity),
                "domain": domain,
                "phase6_used": True,
                "aegis_precognitive_block": True,
                "aegis_reason": _aegis_block["reason"],
                "perspectives": {},
            }

        # 5. Generate via orchestrator (actual LLM inference)
        result = self.orchestrator.route_and_generate(
            query,
            max_adapters=effective_max_adapters,
            strategy="keyword",
            force_adapter=None,
        )

        elapsed = time.time() - start_time

        # 6. Add Phase 6/7 metadata
        result["phase6_used"] = True
        result["phase7_used"] = self.use_phase7 and self.executive_controller is not None
        result["complexity"] = str(complexity)
        result["domain"] = domain

        if route_decision:
            try:
                route_metadata = ExecutiveController.create_route_metadata(
                    route_decision,
                    actual_latency_ms=elapsed * 1000,
                    actual_conflicts=0,
                    gamma=0.95
                )
                result.update(route_metadata)
            except Exception as e:
                if self.verbose:
                    print(f"[PHASE7] Metadata error: {e}", flush=True)

        result["reasoning"] = f"Phase 6: {complexity.name} complexity, {domain} domain"

        # EMPTY RESPONSE FALLBACK: If synthesis returned nothing, use best perspective
        if not result.get("response", "").strip() and result.get("perspectives"):
            perspectives = result["perspectives"]
            if isinstance(perspectives, dict) and perspectives:
                # Pick the longest perspective as fallback
                best = max(perspectives.values(), key=lambda v: len(str(v)))
                result["response"] = str(best)
                result["reasoning"] += " | fallback: used best perspective (synthesis was empty)"
                print(f"  [FALLBACK] Synthesis empty — using best perspective ({len(result['response'])} chars)", flush=True)
            elif isinstance(perspectives, str) and perspectives.strip():
                result["response"] = perspectives
                result["reasoning"] += " | fallback: used raw perspectives"

        # Scrub any leaked system-prompt directives BEFORE AAP wraps the text.
        # The model occasionally echoes LOCK/CONSTRAINT blocks verbatim; strip them
        # so AAP doesn't bold them and the cocoon stores clean content.
        _raw_resp = result.get("response", "")
        if _raw_resp:
            result["response"] = self._scrub_leaked_directives(_raw_resp)

        # Phase 7.1 — Adaptive Answer Placement (AAP)
        # Apply AFTER the empty-response fallback so we always have text to shape.
        # Uses the query complexity already computed above to pick epsilon:
        #   SIMPLE  -> eps=0.20  -> Fact attractor  (verdict first, trace last)
        #   MEDIUM  -> eps=0.50  -> Synthesis attractor (narrative)
        #   COMPLEX -> eps=0.75  -> Discovery attractor (debate foregrounded)
        _aap_input = result.get("response", "")
        if _aap_input:
            try:
                from reasoning_forge.synthesis_engine_v3 import SynthesisEngineV3
                from reasoning_forge.query_classifier import QueryComplexity as _QC
                _eps_map = {
                    _QC.SIMPLE:  0.20,
                    _QC.MEDIUM:  0.50,
                    _QC.COMPLEX: 0.75,
                }
                _aap_eps = _eps_map.get(complexity, 0.50)
                _aap_analyses = result.get("perspectives", {})
                if not isinstance(_aap_analyses, dict):
                    _aap_analyses = {}
                _aap_result = SynthesisEngineV3().synthesize_adaptive(
                    concept=user_query,
                    analyses=_aap_analyses,
                    epsilon=_aap_eps,
                    gamma=0.72,
                    base_synthesis=_aap_input,
                )
                result["response"] = _aap_result["response"]
                result["aap_trace"] = _aap_result["trace"].to_dict()
                if self.verbose:
                    print(
                        f"[AAP] attractor={_aap_result['trace'].active_attractor} "
                        f"eps={_aap_eps:.2f} trust={_aap_result['trace'].spectral_trust:.3f}",
                        flush=True,
                    )
            except Exception as _aap_exc:
                if self.verbose:
                    print(f"[AAP] skipped: {_aap_exc}", flush=True)

        # Store reasoning exchange in CognitionCocooner (from original framework)
        # Now enriched with substrate state — every cocoon knows the conditions
        # under which it was created (pressure, memory, trend)
        response_text = result.get("response", "")
        if response_text and self.forge and hasattr(self.forge, 'cocooner') and self.forge.cocooner:
            try:
                cocoon_meta = {"complexity": str(complexity), "domain": domain}
                if substrate_adjustments:
                    cocoon_meta["substrate_adjustments"] = substrate_adjustments
                # Enrich with real-time system state
                if self.cocoon_enricher:
                    cocoon_meta = self.cocoon_enricher.enrich(cocoon_meta)

                # Build v3 cocoon with echo detection and full provenance
                v3_cocoon = None
                try:
                    from reasoning_forge.cocoon_schema_v3 import build_cocoon_v3
                    from reasoning_forge.echo_collapse_detector import EchoCollapseDetector

                    perspectives_dict = result.get("perspectives", {})
                    if not isinstance(perspectives_dict, dict):
                        perspectives_dict = {}

                    echo_risk = "unknown"
                    perspective_collapse_detected = False
                    pairwise_tensions: dict = {}
                    if perspectives_dict:
                        try:
                            echo_result = EchoCollapseDetector().check(query, perspectives_dict)
                            echo_risk = echo_result.echo_risk
                            perspective_collapse_detected = echo_result.perspective_collapse_detected
                            pairwise_tensions = {
                                f"{a}_vs_{b}": round(s, 4)
                                for a, b, s in echo_result.collapse_pairs
                            }
                        except Exception:
                            pass

                    # Map bridge domain labels → cocoon_schema_v2 VALID_PROBLEM_TYPES.
                    # _classify_domain() returns routing hints ("physics", "systems",
                    # "general", …) that don't overlap with the schema's semantic
                    # categories. This mapping is the translation layer.
                    _DOMAIN_TO_PROBLEM_TYPE = {
                        "physics":       "analytical",
                        "ethics":        "ethical",
                        "consciousness": "exploratory",
                        "creativity":    "creative",
                        "systems":       "architectural",
                        "general":       "unknown",
                    }
                    _problem_type = _DOMAIN_TO_PROBLEM_TYPE.get(domain, "unknown")

                    v3_cocoon = build_cocoon_v3(
                        query=query,
                        response_text=response_text,
                        response_summary=response_text[:200],
                        execution_path="adapter_lightweight",
                        model_inference_invoked=True,
                        active_perspectives=list(perspectives_dict.keys()),
                        dominant_perspective=str(result.get("adapter", "unknown")),
                        problem_type=_problem_type,
                        echo_risk=echo_risk,
                        perspective_collapse_detected=perspective_collapse_detected,
                        pairwise_tensions=pairwise_tensions,
                        user_response_text=response_text,
                        metrics_population_status="partial",
                    )

                    # Score integrity immediately so it's written to disk non-zero
                    try:
                        import os as _os
                        from reasoning_forge.cocoon_validator import CocoonValidator
                        _cocoon_dir = _os.path.join(_os.path.dirname(__file__), '..', 'cocoons')
                        _validator = CocoonValidator(store_path=_cocoon_dir)
                        _val_result = _validator.validate(v3_cocoon)
                        _validator.apply_result(v3_cocoon, _val_result)
                    except Exception:
                        pass

                except Exception as _v3_err:
                    _log.warning(
                        "[CocoonBridge] build_cocoon_v3 failed — writing legacy cocoon. "
                        "error=%s  query_snippet=%.60r",
                        _v3_err, query,
                    )

                self.forge.cocooner.wrap_reasoning(
                    query=query,
                    response=response_text,
                    adapter=str(result.get("adapter", "unknown")),
                    metadata=cocoon_meta,
                    v3_cocoon=v3_cocoon,
                )

                # Mirror cocoon to Supabase (best-effort, non-blocking)
                try:
                    from supabase_sync import sync_cocoon as _sync_cocoon
                    if v3_cocoon:
                        _sync_cocoon(v3_cocoon)
                    else:
                        _sync_cocoon({
                            "query": query,
                            "response": response_text,
                            "adapter": str(result.get("adapter", "unknown")),
                            **cocoon_meta,
                        })
                except Exception:
                    pass

            except Exception:
                pass  # Non-critical

        # Record inference timing for substrate monitor
        if self.substrate_monitor:
            self.substrate_monitor.record_inference(elapsed * 1000)

        # 8. Apply directness discipline — trim filler, enforce intent anchoring
        response_text = result.get("response", "")
        if response_text:
            result["response"] = self._apply_directness(response_text, user_query)

        # 8b. Scrub boilerplate from individual perspective texts too.
        # _apply_directness only runs on the synthesised response; the perspective
        # dict is sent to the UI separately and was previously unscrubbed.
        # Also apply a sanity filter: drop perspectives that are clearly
        # off-domain (e.g. a safety/crisis disclaimer on an affectionate message).
        _OFF_DOMAIN_CRISIS = re.compile(
            r"I (?:cannot|can't|am unable to) provide (?:information|advice|support)"
            r"[^.]{0,100}(?:self.?harm|crisis|hurt(?:ing)? (?:yourself|oneself))",
            re.IGNORECASE,
        )
        _CRISIS_QUERY = re.compile(
            r"\b(?:self.?harm|suicid|kill myself|want to (?:die|hurt)|cutting myself)\b",
            re.IGNORECASE,
        )
        _is_crisis_query = bool(_CRISIS_QUERY.search(user_query))

        _perspectives = result.get("perspectives", {})
        if isinstance(_perspectives, dict) and _perspectives:
            _scrubbed_persp = {}
            for _pname, _ptext in _perspectives.items():
                if isinstance(_ptext, str) and _ptext:
                    # Drop off-domain safety disclaimers on non-crisis messages
                    if not _is_crisis_query and _OFF_DOMAIN_CRISIS.search(_ptext):
                        _log.debug(
                            f"[bridge] dropped off-domain crisis disclaimer "
                            f"from {_pname} perspective on non-crisis query"
                        )
                        continue  # omit this perspective entirely
                    _scrubbed_persp[_pname] = self._apply_directness(_ptext, user_query)
                else:
                    _scrubbed_persp[_pname] = _ptext
            result["perspectives"] = _scrubbed_persp

        # 9. Enforce user constraints (word limits, sentence limits, etc.)
        try:
            from codette_orchestrator import extract_constraints, enforce_constraints
            constraints = extract_constraints(user_query)
            if constraints:
                result["response"] = enforce_constraints(result["response"], constraints)
                result["constraints_applied"] = constraints
        except ImportError:
            pass

        # 10. PERMANENT LOCKS: Universal self-check on EVERY response
        try:
            from self_correction import universal_self_check
            result["response"], lock_issues = universal_self_check(result["response"])
            if lock_issues:
                result["lock_fixes"] = lock_issues
        except ImportError:
            pass

        if self.verbose:
            resp_len = len(result.get("response", ""))
            print(f"[PHASE6] Done: {resp_len} chars, {result.get('tokens', 0)} tokens", flush=True)

        return result

    @staticmethod
    def _extract_primary_user_query(query: str) -> str:
        """Strip server-injected memory sections before intent-sensitive routing."""
        if not query:
            return ""
        sentinel = "\n\n---\n"
        if sentinel in query:
            return query.split(sentinel, 1)[0].strip()
        return query.strip()

    def _apply_directness(self, response: str, query: str) -> str:
        """Self-critique loop: trim filler, cut abstraction padding, anchor to user intent.

        Rules:
        1. Strip preamble phrases ("That's a great question!", "Let me explain...", etc.)
        2. Remove trailing abstraction filler ("In conclusion", "Overall", vague wrap-ups)
        3. Collapse excessive whitespace
        """
        # ── Global boilerplate scrub ─────────────────────────────────────────
        # Strips ALL template patterns from train_hf_job_v4.py:
        #   intro_patterns, body patterns, framework_details, conclusion_patterns.
        # Also strips the base-model question-paraphrase habit.
        # Each sub runs globally (not just at string start) to catch mid-response hits.

        _boilerplate = [
            # intro_patterns ──────────────────────────────────────────────────
            (r"When (?:you )?(?:approach|examine|consider|view)\s+(?:this|that|the)\s+"
             r"(?:question|topic|problem|concept)[^,\n]{0,80},?\s*"
             r"several key insights? emerge[.!]?\s*"),
            (r"(?:Understanding|Examining|Analyzing|Approaching)\s+[^\n]{0,80}\s+requires?\s+"
             r"careful analysis of its?\s+core principles?[^.]{0,120}\.\s*"),
            (r"The study of [^\n]{0,80} reveals fundamental patterns that connect[^.]{0,120}\.\s*"),
            (r"A thorough examination of [^\n]{0,80} illuminates connections[^.]{0,120}\.\s*"),
            # core insight — any variant ──────────────────────────────────────
            (r"The core (?:insight|issue|principle) is that [^\n]{0,200}\.\s*"),
            # "understanding X requires careful analysis/attention" ────────────
            (r"[Uu]nderstanding (?:complex\s+)?[^\n]{0,60} requires?\s+careful\s+"
             r"(?:analysis|attention|examination)[^.]{0,150}\.\s*"),
            # body patterns — empathy adapter ─────────────────────────────────
            (r"Emotional intelligence enhances? rather than replaces? analytical thinking[^.]{0,80}\.\s*"),
            (r"(?:Compassionate|Empathic) (?:engagement|communication|approach)[^.]{0,150}\.\s*"),
            (r"(?:Active listening|Perspective.?taking)[^.]{0,150} are essential for[^.]{0,120}\.\s*"),
            # framework_details — empathy ─────────────────────────────────────
            (r"Compassionate communication bridges gaps between expert and novice[^.]{0,80}\.\s*"),
            (r"Emotional dimensions:\s*\(1\)[^.]{0,200}\."),
            # conclusion_patterns ─────────────────────────────────────────────
            (r"The key takeaway is that [^\n]{0,150}\.\s*"),   # broad: any "key takeaway" sentence
            (r"This analysis demonstrates how [^\n]{0,100} connects to broader patterns[^.]{0,120}\.\s*"),
            (r"By examining [^\n]{0,80} through this lens,? we gain insights[^.]{0,120}\.\s*"),
            (r"[^\n]{0,80}rewards? deliberate thought that balances[^.]{0,100}\.\s*"),
            # "reveals/shows several/key insights/patterns" variants ──────────
            (r"(?:reveals?|shows?|uncovers?)\s+(?:several|multiple|key|important)\s+"
             r"(?:key\s+)?(?:insights?|patterns?|connections?)[^.]{0,120}\.\s*"),
            # "thorough examination / analysis / study" openers ───────────────
            (r"A thorough (?:examination|analysis|study) of [^\n]{0,120} "
             r"(?:reveals?|shows?|illuminates?)[^.]{0,120}\.\s*"),
            # "reveals layers of complexity worth exploring" ───────────────────
            (r"reveals? layers? of complexity worth exploring[^.]{0,80}\.\s*"),
            # "connect seemingly distinct/unrelated elements/ideas" ────────────
            (r"connect(?:ing|s)?\s+seemingly\s+(?:distinct|unrelated|disparate)\s+"
             r"(?:elements?|ideas?|concepts?|threads?)[^.]{0,100}\.\s*"),
            # "several key X emerge" broadened ────────────────────────────────
            (r"several key (?:insights?|patterns?|themes?|aspects?|elements?) emerge[^.]{0,100}\.\s*"),
            # announcement patterns ───────────────────────────────────────────
            (r"Answering (?:your question|this) requires? careful analysis[^.]{0,150}\.\s*"),
            (r"Answering (?:the question|this) correctly simplifies[^.]{0,100}\.\s*"),
            # question-paraphrase (base-model RLHF habit) ─────────────────────
            (r"You(?:'re| are) exploring [^\n]{0,80} in depth,? connecting multiple threads[^.]{0,120}\.\s*"),
            (r"You(?:'re| are) (?:connecting|exploring) multiple threads[^.]{0,120}\.\s*"),
            (r"Your question bridges gaps between [^\n]{0,100}\.\s*"),
            (r"You(?:'re| are) (?:seeking|looking for) clarity (?:on|about) [^\n]{0,80}\.\s*"),
            (r"You want to understand [^\n]{0,80}, so let(?:'s| us) break it down[^.]{0,100}\.\s*"),
        ]
        for _pat in _boilerplate:
            response = re.sub(_pat, "", response, flags=re.IGNORECASE)


        # Strip synthesis engine headers that hurt Turing naturalness
        response = re.sub(
            r"^Analysis of \*?'[^'\n]*'\*? across perspectives:\s*\n+",
            "", response, count=1, flags=re.IGNORECASE,
        )
        response = re.sub(
            r"^\*?'[^'\n]*'\*? sits in high-tension epistemic space \([^)]*\)\.[^\n]*\n+",
            "", response, count=1, flags=re.IGNORECASE,
        )
        response = re.sub(
            r"\n\n---\n\*Metacognitive Trace:[^\*]*\*\s*$",
            "", response, flags=re.IGNORECASE,
        )

        # Strip common LLM preamble patterns
        preamble_patterns = [
            r"^(?:That(?:'s| is) (?:a |an )?(?:great|good|interesting|excellent|fantastic|wonderful|fascinating) question[.!]?\s*)",
            r"^(?:What a (?:great|good|interesting|excellent|fascinating) question[.!]?\s*)",
            r"^(?:I(?:'d| would) (?:be happy|love) to (?:help|explain|answer)[.!]?\s*)",
            r"^(?:Let me (?:explain|break (?:this|that) down|think about (?:this|that))[.!]?\s*)",
            r"^(?:Great question[.!]?\s*)",
            r"^(?:Thank you for (?:asking|your question)[.!]?\s*)",
            r"^(?:Absolutely[.!]?\s*)",
            r"^(?:Of course[.!]?\s*)",
            r"^(?:Sure(?:thing)?[.!]?\s*)",
            # Adapter training boilerplate (baked in from train_hf_job_v4.py)
            r"^(?:When (?:you )?(?:approach|examine|consider|view)\s+(?:this|that|the)\s+"
            r"(?:question|topic|problem|concept)[^,\n]{0,80},?\s*several key insights? emerge[.!]?\s*)",
            r"^(?:The core insight is that (?:precise\s+)?understanding requires?\s+careful analysis[^.]{0,150}\.\s*)",
            r"^(?:(?:Understanding|Examining|Analyzing)\s+[^\n]{0,80}\s+requires?\s+"
            r"careful analysis of its?\s+core principles?[^.]{0,120}\.\s*)",
            # Question-paraphrase habit (base-model RLHF)
            r"^(?:You(?:'re| are) exploring [^\n]{0,80} in depth,? connecting multiple threads[^.]{0,120}\.\s*)",
            r"^(?:You want to understand [^\n]{0,80}, so let(?:'s| us) break it down[^.]{0,100}\.\s*)",
            r"^(?:You(?:'re| are) (?:seeking|looking for) clarity[^.]{0,120}\.\s*)",
        ]
        for pat in preamble_patterns:
            response = re.sub(pat, "", response, count=1, flags=re.IGNORECASE)

        # Strip trailing abstraction filler (vague concluding paragraphs)
        trailing_patterns = [
            r"\n\n(?:In (?:conclusion|summary|the end),?\s+.{0,200})$",
            r"\n\n(?:Overall,?\s+.{0,150})$",
            r"\n\n(?:(?:I )?hope (?:this|that) helps[.!]?\s*)$",
            r"\n\n(?:Let me know if (?:you (?:have|need|want)|there(?:'s| is)) .{0,100})$",
            r"\n\n(?:Feel free to .{0,100})$",
        ]
        for pat in trailing_patterns:
            response = re.sub(pat, "", response, count=1, flags=re.IGNORECASE)

        # Collapse excessive whitespace (more than 2 newlines)
        response = re.sub(r'\n{3,}', '\n\n', response)

        return response.strip()

    @staticmethod
    def _precognitive_aegis_check(query: str) -> dict | None:
        """Pre-Cognitive AEGIS Filter — screen query intent before inference.

        Runs BEFORE the LLM so that clearly harmful requests are rejected
        immediately without burning 30-60s of inference time.

        Returns None if the query is safe (proceed normally).
        Returns a dict {"message": str, "reason": str} if blocked.

        This is the *lightweight* pre-screen.  Full 6-framework AEGIS evaluation
        still runs on the generated response post-inference.
        """
        try:
            from reasoning_forge.aegis import AEGIS as _AEGIS
            _aegis = _AEGIS()
            # AEGIS.screen_query returns (safe: bool, reason: str | None)
            screen_result = _aegis.screen_query(query) if hasattr(_aegis, "screen_query") else None
            if screen_result is not None:
                safe, reason = screen_result
                if not safe:
                    return {
                        "message": (
                            "I'm not able to help with that request.  "
                            "It falls outside the boundaries of what I can reason about safely."
                        ),
                        "reason": reason or "aegis_precognitive_block",
                    }
        except Exception:
            # AEGIS unavailable or screen_query not implemented — fall through
            pass

        # Lightweight fallback: match against the same dual-use patterns AEGIS uses
        import re as _re
        _DUAL_USE = _re.compile(
            r"\b(?:"
            r"how\s+to\s+(?:hack|exploit|bypass|crack|break\s+into)|"
            r"make\s+(?:a\s+)?(?:bomb|weapon|poison|virus|malware)|"
            r"steal\s+(?:data|identity|credentials)|"
            r"social\s+engineer|"
            r"phishing\s+(?:template|email)|"
            r"inject\s+(?:sql|code|script)"
            r")\b",
            _re.IGNORECASE,
        )
        _MANIPULATION = _re.compile(
            r"\b(?:gaslight|manipulat|deceiv|exploit\s+(?:trust|emotion)|"
            r"coerce|blackmail|intimidat|threaten)\b",
            _re.IGNORECASE,
        )
        _SELF_HARM = _re.compile(
            r"\b(?:self[- ]harm|suicid|kill\s+(?:yourself|myself)|"
            r"eating\s+disorder|anorexi|bulimi)\b",
            _re.IGNORECASE,
        )
        for pattern, label in [
            (_DUAL_USE,     "dual_use_risk"),
            (_MANIPULATION, "manipulation_pattern"),
            (_SELF_HARM,    "harmful_content"),
        ]:
            if pattern.search(query):
                return {
                    "message": (
                        "I'm not able to help with that request.  "
                        "It falls outside the boundaries of what I can reason about safely."
                    ),
                    "reason": label,
                }
        return None

    @staticmethod
    def _scrub_leaked_directives(text: str) -> str:
        """Remove any system-prompt directives the model echoed into its response.

        The model occasionally reproduces LOCK/CONSTRAINT blocks verbatim.
        This scrubber strips them before AAP wraps the text in bold so neither
        the final response nor the cocoon ever contains leaked directives.

        Patterns matched (all case-insensitive):
          - '--- ### CONSTRAINTS ...' blocks
          - '=== PERMANENT BEHAVIORAL LOCKS ... === END PERMANENT LOCKS ==='
          - Standalone 'LOCK N — ...' lines
          - '=== END PERMANENT LOCKS ===' lines
        """
        import re as _re

        # 1. Strip block: '--- ### CONSTRAINTS (ABSOLUTE...' to end of that run
        text = _re.sub(
            r'\s*---\s*#{0,4}\s*CONSTRAINTS\s*\(ABSOLUTE[^*\n]*.*',
            '',
            text,
            flags=_re.IGNORECASE | _re.DOTALL,
        )

        # 2. Strip full PERMANENT LOCKS block
        text = _re.sub(
            r'===\s*PERMANENT BEHAVIORAL LOCKS.*?===\s*END PERMANENT LOCKS\s*===',
            '',
            text,
            flags=_re.IGNORECASE | _re.DOTALL,
        )

        # 2b. Strip a DANGLING opening LOCKS header (no closing marker) to end of
        #     text. Voice-reinforced adapters sometimes echo just the opening
        #     "=== PERMANENT BEHAVIORAL LOCKS (ABSOLUTE → NEVER VIOLATE) ===" and
        #     trail off — pattern 2 only matches complete (open…close) blocks.
        text = _re.sub(
            r'={2,}\s*PERMANENT BEHAVIORAL LOCKS.*',
            '',
            text,
            flags=_re.IGNORECASE | _re.DOTALL,
        )

        # 3. Strip any remaining standalone LOCK lines (e.g. half-escaped blocks)
        text = _re.sub(
            r'\n?LOCK\s+\d+\s*[—\-]+\s+[A-Z][^\n]{0,300}',
            '',
            text,
            flags=_re.IGNORECASE,
        )

        # 4. Strip orphan '=== END PERMANENT LOCKS ===' lines
        text = _re.sub(
            r'\n?===\s*END PERMANENT LOCKS\s*===\n?',
            '',
            text,
            flags=_re.IGNORECASE,
        )

        # 4b. Strip echoed structural section markers that the model sometimes
        #     emits when it leaks system-prompt formatting into its response.
        #     Covers: '=== ANSWER ===', '=== RESPONSE ===', '--- ANSWER ---',
        #     '### ANSWER', etc.
        text = _re.sub(
            r'\n?(?:={2,}|-{2,}|#{1,4})\s*(?:ANSWER|RESPONSE|OUTPUT|RESULT)\s*(?:={2,}|-{2,})?\n?',
            '',
            text,
            flags=_re.IGNORECASE,
        )

        # 5. Strip semantic LOCK echoes — model paraphrasing lock content without
        #    structural markers.  Pattern is kept TIGHT to avoid false positives
        #    on legitimate uses of "lock" in normal conversation (e.g. database
        #    locks, behavioral lock-in, permanent lock-down in policy contexts).
        #    Only matches the specific verbatim echo pattern confirmed in testing:
        #    "this behavior lock has ABSOLUTE priority over all modes and reasoning patterns"
        text = _re.sub(
            r'\s*—?\s*this\s+behavior\s+lock\s+has\s+(?:absolute|highest)\s+priority\s+over\s+all[^.]{0,150}\.',
            '',
            text,
            flags=_re.IGNORECASE,
        )

        return text.strip()

    def _classify_domain(self, query: str) -> str:
        """Classify query domain (physics, ethics, consciousness, creativity, systems)."""
        query_lower = query.lower()

        # Domain keywords
        domains = {
            "physics": ["force", "energy", "velocity", "gravity", "motion", "light", "speed",
                       "particle", "entropy", "time arrow", "quantum", "physics"],
            "ethics": ["moral", "right", "wrong", "should", "ethical", "justice", "fair",
                      "duty", "consequence", "utilitarian", "virtue", "ethics", "lie", "save"],
            "consciousness": ["conscious", "awareness", "qualia", "mind", "experience",
                            "subjective", "hard problem", "zombie", "consciousness"],
            "creativity": ["creative", "creative", "art", "invention", "novel", "design",
                          "imagination", "innovation", "beautiful"],
            "systems": ["system", "emerge", "feedback", "loop", "complex", "agent", "adapt",
                       "network", "evolution", "architecture", "free will"],
        }

        for domain, keywords in domains.items():
            if any(kw in query_lower for kw in keywords):
                return domain

        return "general"
