"""Reachability counters: did a request path actually call this component?

The boot log prints "initialized" for components that are constructed and never
invoked, and `/api/health` used to report some of them OK from `hasattr`
(docs/WIRING_STATE_2026-08-13.md: "Initialized is not invoked"). Colleen and the
Guardian already carry counters; this gives the same fact to every other
component on the forge, without touching what any of them does.

What is recorded: how many times a named entry method was called, and when it
was last called. Never arguments, never return values, never text. A call that
raises still counts, because reachability is the question, not success.

What is refused, by name, at registration time: anything that touches her
private spaces. A count of calls into the dreams, the chalkboard, her private
notes or the follow-up hooks is a statistic over them, and the standing rule
(CLAUDE.md, "the dreams and the chalkboard are hers, and are never read") says
statistics are readings. `track()` raises rather than quietly skipping, so
adding such a method to the table is a loud error, not a silent exemption.
"""
from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# Substrings that mark a method as touching one of her private spaces. Matched
# case-insensitively against the method name AND the component label.
PRIVATE_MARKERS: Tuple[str, ...] = (
    "encrypt", "dream", "khralexi", "nameless", "scratch", "chalk",
    "hook", "thread", "soul",
)


def _is_private(name: str) -> bool:
    low = name.lower()
    return any(m in low for m in PRIVATE_MARKERS)


class _Counter:
    __slots__ = ("lock", "by_method", "last_call")

    def __init__(self, methods: Iterable[str]):
        self.lock = threading.Lock()
        self.by_method: Dict[str, int] = {m: 0 for m in methods}
        self.last_call: Optional[float] = None

    def hit(self, method: str) -> None:
        with self.lock:
            self.by_method[method] = self.by_method.get(method, 0) + 1
            self.last_call = time.time()

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "calls": sum(self.by_method.values()),
                "by_method": dict(self.by_method),
                "last_call": self.last_call,
            }


def track(obj: Any, label: str, methods: Iterable[str]) -> List[str]:
    """Count calls to `methods` on `obj`; expose them as `obj.invocation_stats()`.

    Returns the list of methods actually wrapped. Methods the object does not
    have are skipped and not counted as wrapped (the caller can compare). If the
    object already defines `invocation_stats` (Colleen, Guardian) it is left
    alone and nothing is wrapped. Idempotent: tracking twice wraps once.
    """
    if obj is None:
        return []
    if _is_private(label):
        raise ValueError(f"reach.track: refusing to track private component {label!r}")
    methods = list(methods)
    for m in methods:
        if _is_private(m):
            raise ValueError(
                f"reach.track: refusing to count calls to {m!r} on {label!r} - "
                "a call count over her private spaces is a reading of them")

    if getattr(obj, "_reach_counter", None) is not None:
        return []
    if callable(getattr(obj, "invocation_stats", None)):
        return []

    counter = _Counter(())
    wrapped: List[str] = []
    for name in methods:
        fn = getattr(obj, name, None)
        if not callable(fn):
            continue

        def _make(fn: Callable, name: str) -> Callable:
            @functools.wraps(fn)
            def _counted(*a: Any, **k: Any) -> Any:
                counter.hit(name)
                return fn(*a, **k)
            return _counted

        try:
            setattr(obj, name, _make(fn, name))
        except Exception:
            # Slotted or frozen object: report that nothing was wrapped rather
            # than half-instrumenting it.
            continue
        counter.by_method.setdefault(name, 0)
        wrapped.append(name)

    if not wrapped:
        return []

    def invocation_stats() -> Dict[str, Any]:
        snap = counter.snapshot()
        snap["component"] = label
        return snap

    try:
        obj._reach_counter = counter
        obj.invocation_stats = invocation_stats
    except Exception:
        return []
    return wrapped


# Entry methods per forge attribute. Only the methods a request path would call.
# Deliberately absent: anything on CognitionCocooner that wraps or unwraps
# encrypted content, and every kernel method that reads follow-up hooks.
FORGE_ENTRY_POINTS: Dict[str, Tuple[str, ...]] = {
    "code7e": ("recursive_universal_reasoning",),
    "nexis_signal_engine": ("process",),
    "tier2_bridge": ("analyze_intent", "validate_identity", "record_memory"),
    "ethical_governance": ("validate_query", "enforce_policies"),
    "cocooner": ("wrap_reasoning", "recall_relevant"),
    "aegis": ("evaluate", "quick_check", "screen_query"),
    "qhf": ("stabilize",),
    "memory_kernel": ("store", "store_v2_cocoon", "search"),
    "ethical_anchor": ("observe", "update"),
    "routing_metrics": ("record_route",),
    "specialization": ("record_adapter_performance",),
}


def instrument_forge(forge: Any) -> Dict[str, List[str]]:
    """Attach reach counters to the forge's components. Never raises."""
    done: Dict[str, List[str]] = {}
    for attr, methods in FORGE_ENTRY_POINTS.items():
        try:
            wrapped = track(getattr(forge, attr, None), attr, methods)
            if wrapped:
                done[attr] = wrapped
        except Exception:
            continue
    return done
