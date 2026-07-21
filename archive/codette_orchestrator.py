#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path

# Add backend directory to path if not already there
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE.parent / "openvino_backend"))

from openvino_backend.backend import OpenVINOBackend

# ── Orchestrator (State Engine v8 + OpenVINO) ────────────────────────────────

class CodetteOrchestrator:
    """Orchestrates multi-adapter inference using OpenVINO GenAI backend."""

    def __init__(self, n_ctx=4096, verbose=True, memory_weighting=None):
        self.verbose = verbose
        self.n_ctx = n_ctx
        
        # 1. Initialize OpenVINO backend with EXPLICIT GPU binding
        # Hardcoding device="GPU" here skips the "AUTO" probe which causes 
        # the ~60s wait in your logs.
        print(f"  [State Engine v8] Initializing OpenVINO backend (GPU)...", flush=True)
        self._backend = OpenVINOBackend(
            device="GPU", 
            verbose=verbose,
            n_ctx=n_ctx,
            memory_weighting=memory_weighting
        )
        
        self.available_adapters = self._backend.available_adapters
        self.router = self._backend.router
        
        print(f"  ✓ Orchestrator ready: {len(self.available_adapters)} adapters loaded.")

    def route_and_generate(self, query: str, max_adapters=2,
                           strategy="keyword", force_adapter=None,
                           enable_tools=True) -> dict:
        """Entry point: Routes query and generates response via backend."""
        # Backend handles adapter hot-swapping and pipeline management
        return self._backend.route_and_generate(
            query=query,
            max_adapters=max_adapters,
            strategy=strategy,
            force_adapter=force_adapter
        )

    def generate(self, query: str, adapter_name=None, system_prompt=None,
                 enable_tools=True):
        """Standardized generation call for forge bridge."""
        return self._backend.generate(
            query=query,
            adapter_name=adapter_name,
            system_prompt=system_prompt,
            enable_tools=enable_tools
        )

    def set_memory_kernel(self, memory_kernel):
        """Wire memory kernel into backend for context enrichment."""
        self._backend.set_memory_kernel(memory_kernel)

    def _build_memory_context(self) -> str:
        """Retrieve memory context from backend."""
        return self._backend._build_memory_context()

# ── Main Entry Point ──────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Codette Orchestrator (OV)")
    parser.add_argument("--query", "-q", type=str, help="Single query")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    orchestrator = CodetteOrchestrator(verbose=args.verbose)

    if args.query:
        result = orchestrator.route_and_generate(args.query)
        print(f"\nCodette:\n{result['response']}")
    else:
        print("  [System] Orchestrator running. Web UI should be used for full interaction.")

if __name__ == "__main__":
    main()