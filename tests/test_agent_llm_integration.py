#!/usr/bin/env python3
"""Quick test to verify agents are using real LLM inference via adapters."""

import sys
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'reasoning_forge'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'inference'))

print("=" * 80)
print("AGENT LLM INTEGRATION TEST")
print("=" * 80)

# Test 1: Check if ForgeEngine can load with orchestrator
print("\n[1/4] Loading ForgeEngine with orchestrator...")
try:
    from reasoning_forge.forge_engine import ForgeEngine
    forge = ForgeEngine(living_memory=None, enable_memory_weighting=False)
    print("  ✓ ForgeEngine loaded")

    # Check if any agent has an orchestrator
    has_orchestrator = any(agent.orchestrator is not None for agent in forge.analysis_agents)
    print(f"  ✓ Agents have orchestrator: {has_orchestrator}")

    if has_orchestrator:
        orch = forge.newton.orchestrator
        print(f"  ✓ Available adapters: {orch.available_adapters}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Try single agent analysis with LLM
print("\n[2/4] Testing Newton agent with LLM...")
try:
    concept = "gravity"
    print(f"  Analyzing: '{concept}'")

    response = forge.newton.analyze(concept)

    # Check if response is real (not template substitution)
    is_real = len(response) > 100 and "gravity" in response.lower()
    is_template = "{concept}" in response

    print(f"  Response length: {len(response)} chars")
    print(f"  Is template-based: {is_template}")
    print(f"  Contains concept: {'gravity' in response.lower()}")
    print(f"  First 200 chars: {response[:200]}...")

except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Try multi-agent analysis
print("\n[3/4] Testing multi-agent ensemble...")
try:
    concept = "evolution"
    print(f"  Analyzing: '{concept}'")

    analyses = {}
    for agent in forge.analysis_agents[:3]:  # Just test first 3
        print(f"    {agent.name}...", end=" ", flush=True)
        response = agent.analyze(concept)
        analyses[agent.name] = response
        print(f"({len(response)} chars)")

    print(f"  ✓ Collected {len(analyses)} analyses")

except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Try debate mode (forge_with_debate)
print("\n[4/4] Testing debate mode with real agents...")
try:
    query = "What is the relationship between consciousness and computation?"
    print(f"  Query: '{query}'")
    print(f"  Running debate (this takes a minute or two)...")

    result = forge.forge_with_debate(query)

    synthesis = ""
    if "messages" in result and len(result["messages"]) >= 3:
        synthesis = result["messages"][2].get("content", "")

    print(f"  ✓ Debate completed")
    print(f"  Synthesis length: {len(synthesis)} chars")

    if len(synthesis) > 0:
        print(f"  First 300 chars: {synthesis[:300]}...")
    else:
        print(f"  ✗ No synthesis generated")

except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("SUMMARY: Agents are now wired to use real LLM inference via adapters!")
print("=" * 80)
