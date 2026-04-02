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

import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional

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
                self.forge.cocooner.wrap_reasoning(
                    query=query,
                    response=response_text,
                    adapter=str(result.get("adapter", "unknown")),
                    metadata=cocoon_meta
                )
            except Exception:
                pass  # Non-critical

        # Record inference timing for substrate monitor
        if self.substrate_monitor:
            self.substrate_monitor.record_inference(elapsed * 1000)

        # 8. Apply directness discipline — trim filler, enforce intent anchoring
        response_text = result.get("response", "")
        if response_text:
            result["response"] = self._apply_directness(response_text, query)

        # 9. Enforce user constraints (word limits, sentence limits, etc.)
        try:
            from codette_orchestrator import extract_constraints, enforce_constraints
            constraints = extract_constraints(query)
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
