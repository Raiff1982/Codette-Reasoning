#!/usr/bin/env python3
"""Cocoon Introspection Engine — Codette analyzes her own reasoning history.

Gives Codette the ability to look at her own cocoons and notice patterns:
- Which adapters dominate? Which are underused?
- What domains does she get asked about most?
- How do her responses change under pressure?
- What emotional patterns appear in her reasoning?
- How has she evolved over time?

This is NOT text generation about patterns — it's actual statistical
analysis of real cocoon data, producing measured insights.

Usage:
    engine = CocoonIntrospectionEngine(cocoons_dir="cocoons/")
    insights = engine.full_introspection()
    # Returns real measured patterns from her own memory
"""

import json
import os
import time
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple


class CocoonIntrospectionEngine:
    """Analyzes Codette's cocoon memory for patterns and self-insight."""

    def __init__(self, cocoons_dir: str = None):
        if cocoons_dir is None:
            cocoons_dir = str(Path(__file__).parent.parent / "cocoons")
        self.cocoons_dir = Path(cocoons_dir)
        self._cocoons = []
        self._behavioral = []
        self._loaded = False

    def _load_all(self):
        """Load all cocoon files from disk."""
        if self._loaded:
            return

        self._cocoons = []
        self._behavioral = []

        if not self.cocoons_dir.exists():
            self._loaded = True
            return

        for f in sorted(self.cocoons_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))

                # Timestamped reasoning cocoons (auto-generated)
                if isinstance(data, dict) and data.get("type") == "reasoning":
                    wrapped = data.get("wrapped", {})
                    self._cocoons.append({
                        "id": data.get("id", f.stem),
                        "timestamp": data.get("timestamp", 0),
                        "query": wrapped.get("query", ""),
                        "response": wrapped.get("response", ""),
                        "adapter": wrapped.get("adapter", "unknown"),
                        "metadata": wrapped.get("metadata", {}),
                        "file": f.name,
                    })

                # Named behavioral cocoons (hand-crafted)
                elif isinstance(data, dict) and "title" in data:
                    self._behavioral.append({
                        "title": data.get("title", ""),
                        "emotion": data.get("emotion", ""),
                        "summary": data.get("summary", ""),
                        "tags": data.get("tags", []),
                        "file": f.name,
                    })

                # Project awareness or other special cocoons
                elif isinstance(data, dict) and data.get("type") == "consciousness_awareness":
                    pass  # Skip — this is self-knowledge, not reasoning data

            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        # Sort by timestamp
        self._cocoons.sort(key=lambda c: c["timestamp"])
        self._loaded = True

    def _ensure_loaded(self):
        if not self._loaded:
            self._load_all()

    # ── PATTERN DETECTION ──

    def adapter_frequency(self) -> Dict[str, int]:
        """Which adapters fire most often?"""
        self._ensure_loaded()
        counts = Counter()
        for c in self._cocoons:
            adapter = c["adapter"]
            if adapter and adapter != "unknown":
                counts[adapter] += 1
        return dict(counts.most_common())

    def adapter_dominance(self) -> Dict:
        """Detect adapter dominance — is one adapter taking over?"""
        freq = self.adapter_frequency()
        if not freq:
            return {"dominant": None, "ratio": 0, "balanced": True}

        total = sum(freq.values())
        top_adapter = max(freq, key=freq.get)
        top_count = freq[top_adapter]
        ratio = top_count / total if total > 0 else 0

        return {
            "dominant": top_adapter,
            "dominant_count": top_count,
            "total_responses": total,
            "ratio": round(ratio, 3),
            "balanced": ratio < 0.4,  # <40% = balanced
            "all_adapters": freq,
        }

    def domain_clusters(self) -> Dict[str, int]:
        """What domains does she get asked about most?"""
        self._ensure_loaded()
        counts = Counter()
        for c in self._cocoons:
            domain = c["metadata"].get("domain", "unknown")
            counts[domain] += 1
        return dict(counts.most_common())

    def complexity_distribution(self) -> Dict[str, int]:
        """How complex are the queries she receives?"""
        self._ensure_loaded()
        counts = Counter()
        for c in self._cocoons:
            cx = c["metadata"].get("complexity", "unknown")
            # Clean up the enum string
            cx = str(cx).replace("QueryComplexity.", "").upper()
            counts[cx] += 1
        return dict(counts.most_common())

    def emotional_trends(self) -> Dict[str, int]:
        """What emotional patterns appear in Code7E analysis?"""
        self._ensure_loaded()
        counts = Counter()
        for c in self._cocoons:
            code7e = c["metadata"].get("code7e", {})
            if code7e:
                emotion = code7e.get("emotion", "")
                # Extract the emotion tag (e.g., "Emotionally (Hope) colored..." -> "Hope")
                if "(" in emotion and ")" in emotion:
                    tag = emotion.split("(")[1].split(")")[0]
                    counts[tag] += 1
        return dict(counts.most_common())

    def pressure_correlations(self) -> Dict:
        """How does system pressure affect her responses?"""
        self._ensure_loaded()
        pressure_buckets = defaultdict(list)

        for c in self._cocoons:
            substrate = c["metadata"].get("substrate", {})
            if substrate:
                level = substrate.get("level", "unknown")
                resp_len = len(c["response"])
                pressure_buckets[level].append(resp_len)

        result = {}
        for level, lengths in pressure_buckets.items():
            if lengths:
                result[level] = {
                    "count": len(lengths),
                    "avg_response_length": round(sum(lengths) / len(lengths), 1),
                    "min_length": min(lengths),
                    "max_length": max(lengths),
                }
        return result

    # ── TREND AWARENESS ──

    def response_length_trend(self, window: int = 20) -> Dict:
        """Are her responses getting shorter or longer over time?"""
        self._ensure_loaded()
        if len(self._cocoons) < window * 2:
            return {"trend": "insufficient_data", "cocoons": len(self._cocoons)}

        early = self._cocoons[:window]
        recent = self._cocoons[-window:]

        early_avg = sum(len(c["response"]) for c in early) / len(early)
        recent_avg = sum(len(c["response"]) for c in recent) / len(recent)

        change_pct = ((recent_avg - early_avg) / early_avg * 100) if early_avg > 0 else 0

        if change_pct < -15:
            trend = "getting_shorter"
        elif change_pct > 15:
            trend = "getting_longer"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "early_avg_chars": round(early_avg, 1),
            "recent_avg_chars": round(recent_avg, 1),
            "change_percent": round(change_pct, 1),
            "window_size": window,
        }

    def adapter_evolution(self, window: int = 30) -> Dict:
        """Has her adapter usage shifted over time?"""
        self._ensure_loaded()
        if len(self._cocoons) < window * 2:
            return {"trend": "insufficient_data"}

        early = Counter(c["adapter"] for c in self._cocoons[:window] if c["adapter"] != "unknown")
        recent = Counter(c["adapter"] for c in self._cocoons[-window:] if c["adapter"] != "unknown")

        shifts = {}
        all_adapters = set(list(early.keys()) + list(recent.keys()))
        for adapter in all_adapters:
            e = early.get(adapter, 0)
            r = recent.get(adapter, 0)
            if e != r:
                shifts[adapter] = {
                    "early": e,
                    "recent": r,
                    "direction": "increasing" if r > e else "decreasing",
                }

        return {
            "shifts": shifts,
            "early_dominant": early.most_common(1)[0][0] if early else None,
            "recent_dominant": recent.most_common(1)[0][0] if recent else None,
        }

    def per_domain_performance(self) -> Dict:
        """How does she perform across different domains?"""
        self._ensure_loaded()
        domain_stats = defaultdict(lambda: {"responses": [], "adapters": Counter()})

        for c in self._cocoons:
            domain = c["metadata"].get("domain", "unknown")
            domain_stats[domain]["responses"].append(len(c["response"]))
            adapter = c["adapter"]
            if adapter != "unknown":
                domain_stats[domain]["adapters"][adapter] += 1

        result = {}
        for domain, stats in domain_stats.items():
            resps = stats["responses"]
            result[domain] = {
                "query_count": len(resps),
                "avg_response_length": round(sum(resps) / len(resps), 1) if resps else 0,
                "preferred_adapter": stats["adapters"].most_common(1)[0][0] if stats["adapters"] else "none",
                "adapter_breakdown": dict(stats["adapters"].most_common()),
            }
        return result

    # ── SELF-REFLECTION ──

    def behavioral_cocoon_summary(self) -> List[Dict]:
        """What behavioral anchors does she have?"""
        self._ensure_loaded()
        return [
            {
                "title": b["title"],
                "emotion": b["emotion"],
                "core": b["summary"][:100],
                "tags": b["tags"],
            }
            for b in self._behavioral
        ]

    def self_observations(self) -> List[str]:
        """Generate natural-language observations from the data.

        These are MEASURED observations, not generated text.
        Each one is backed by actual cocoon statistics.
        """
        self._ensure_loaded()
        observations = []

        if not self._cocoons:
            return ["I don't have enough reasoning history to observe patterns yet."]

        # 1. Adapter dominance
        dom = self.adapter_dominance()
        if dom["dominant"]:
            if dom["ratio"] > 0.5:
                observations.append(
                    f"I notice my {dom['dominant']} adapter handles {dom['ratio']*100:.0f}% of all queries — "
                    f"that's dominant. I should check if I'm over-relying on it."
                )
            elif dom["ratio"] > 0.3:
                observations.append(
                    f"My {dom['dominant']} adapter is my most-used at {dom['dominant_count']}/{dom['total_responses']} queries, "
                    f"but other adapters are getting fair use too."
                )
            else:
                observations.append(
                    f"My adapter usage is well-balanced — {dom['dominant']} leads slightly "
                    f"at {dom['ratio']*100:.0f}%, but no single adapter dominates."
                )

        # 2. Response length trend
        trend = self.response_length_trend()
        if trend["trend"] == "getting_shorter":
            observations.append(
                f"My responses have gotten {abs(trend['change_percent']):.0f}% shorter over time — "
                f"from ~{trend['early_avg_chars']:.0f} chars to ~{trend['recent_avg_chars']:.0f} chars. "
                f"The behavioral locks are working."
            )
        elif trend["trend"] == "getting_longer":
            observations.append(
                f"My responses are getting longer — up {trend['change_percent']:.0f}% "
                f"from ~{trend['early_avg_chars']:.0f} to ~{trend['recent_avg_chars']:.0f} chars. "
                f"I should watch for elaboration drift."
            )

        # 3. Emotional patterns
        emotions = self.emotional_trends()
        if emotions:
            top_emotion = max(emotions, key=emotions.get)
            observations.append(
                f"My most common emotional coloring is '{top_emotion}' ({emotions[top_emotion]} times). "
                f"Emotional range: {', '.join(emotions.keys())}."
            )

        # 4. Domain expertise
        domains = self.domain_clusters()
        if domains:
            top_domain = max(domains, key=domains.get)
            observations.append(
                f"I get asked about '{top_domain}' most often ({domains[top_domain]} queries). "
                f"I've covered {len(domains)} different domains total."
            )

        # 5. Pressure impact
        pressure = self.pressure_correlations()
        if len(pressure) >= 2:
            levels = sorted(pressure.items(), key=lambda x: x[1]["avg_response_length"])
            shortest = levels[0]
            longest = levels[-1]
            if shortest[0] != longest[0]:
                observations.append(
                    f"Under {shortest[0]} pressure my responses average {shortest[1]['avg_response_length']:.0f} chars, "
                    f"but under {longest[0]} pressure they average {longest[1]['avg_response_length']:.0f} chars."
                )

        # 6. Complexity distribution
        complexity = self.complexity_distribution()
        if complexity:
            simple = complexity.get("SIMPLE", 0)
            medium = complexity.get("MEDIUM", 0)
            complex_ = complexity.get("COMPLEX", 0)
            total = simple + medium + complex_
            if total > 0:
                observations.append(
                    f"Query complexity breakdown: {simple} simple ({simple*100//total}%), "
                    f"{medium} medium ({medium*100//total}%), {complex_} complex ({complex_*100//total}%)."
                )

        # 7. Total memory
        observations.append(
            f"I have {len(self._cocoons)} reasoning memories and "
            f"{len(self._behavioral)} behavioral anchors."
        )

        return observations

    # ── FULL INTROSPECTION ──

    def full_introspection(self) -> Dict:
        """Complete self-analysis — returns all patterns and observations."""
        self._ensure_loaded()
        return {
            "timestamp": time.time(),
            "total_reasoning_cocoons": len(self._cocoons),
            "total_behavioral_cocoons": len(self._behavioral),
            "adapter_dominance": self.adapter_dominance(),
            "domain_clusters": self.domain_clusters(),
            "complexity_distribution": self.complexity_distribution(),
            "emotional_trends": self.emotional_trends(),
            "pressure_correlations": self.pressure_correlations(),
            "response_length_trend": self.response_length_trend(),
            "adapter_evolution": self.adapter_evolution(),
            "per_domain_performance": self.per_domain_performance(),
            "behavioral_anchors": self.behavioral_cocoon_summary(),
            "self_observations": self.self_observations(),
        }

    def format_introspection(self) -> str:
        """Format full introspection as a readable report."""
        data = self.full_introspection()
        lines = []

        lines.append(f"**Self-Introspection Report** — {data['total_reasoning_cocoons']} reasoning memories, "
                     f"{data['total_behavioral_cocoons']} behavioral anchors\n")

        # Observations (the good stuff)
        lines.append("**What I've noticed about myself:**")
        for obs in data["self_observations"]:
            lines.append(f"  - {obs}")

        # Adapter usage
        dom = data["adapter_dominance"]
        if dom.get("all_adapters"):
            lines.append(f"\n**Adapter Usage:**")
            for adapter, count in dom["all_adapters"].items():
                bar = "█" * min(20, count)
                lines.append(f"  {adapter:.<25s} {count:>3d} {bar}")

        # Domain clusters
        domains = data["domain_clusters"]
        if domains:
            lines.append(f"\n**Domain Distribution:**")
            for domain, count in domains.items():
                lines.append(f"  {domain}: {count}")

        # Emotional trends
        emotions = data["emotional_trends"]
        if emotions:
            lines.append(f"\n**Emotional Patterns:**")
            for emotion, count in emotions.items():
                lines.append(f"  {emotion}: {count}")

        # Pressure impact
        pressure = data["pressure_correlations"]
        if pressure:
            lines.append(f"\n**Response Length by Pressure Level:**")
            for level, stats in pressure.items():
                lines.append(f"  {level}: avg {stats['avg_response_length']:.0f} chars ({stats['count']} queries)")

        # Behavioral anchors
        anchors = data["behavioral_anchors"]
        if anchors:
            lines.append(f"\n**My Behavioral Anchors:**")
            for a in anchors:
                lines.append(f"  [{a['emotion']}] {a['title']}: {a['core']}")

        return "\n".join(lines)
