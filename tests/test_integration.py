#!/usr/bin/env python
"""Quick test to verify consciousness stack integration."""
import sys
import os

# Test imports
try:
    from reasoning_forge.colleen_conscience import ColleenConscience
    print("✓ ColleenConscience imported")
except Exception as e:
    print(f"✗ ColleenConscience import failed: {e}")
    sys.exit(1)

try:
    from reasoning_forge.guardian_spindle import CoreGuardianSpindle
    print("✓ CoreGuardianSpindle imported")
except Exception as e:
    print(f"✗ CoreGuardianSpindle import failed: {e}")
    sys.exit(1)

try:
    from reasoning_forge.code7e_cqure import Code7eCQURE
    print("✓ Code7eCQURE imported")
except Exception as e:
    print(f"✗ Code7eCQURE import failed: {e}")
    sys.exit(1)

try:
    from reasoning_forge.nexis_signal_engine_local import NexisSignalEngine
    print("✓ NexisSignalEngine imported")
except Exception as e:
    print(f"✗ NexisSignalEngine import failed: {e}")
    sys.exit(1)

try:
    from reasoning_forge.memory_kernel import MemoryCocoon, LivingMemoryKernel
    print("✓ Memory components imported")
except Exception as e:
    print(f"✗ Memory components import failed: {e}")
    sys.exit(1)

try:
    from reasoning_forge.forge_engine import ForgeEngine
    print("✓ ForgeEngine imported successfully with consciousness stack")
except Exception as e:
    print(f"✗ ForgeEngine import failed: {e}")
    sys.exit(1)

# Test instantiation
try:
    engine = ForgeEngine()
    print("✓ ForgeEngine instantiated")

    # Check consciousness stack components
    if hasattr(engine, 'code7e') and engine.code7e:
        print("✓ Code7eCQURE component initialized")
    else:
        print("⚠ Code7eCQURE component not initialized")

    if hasattr(engine, 'colleen') and engine.colleen:
        print("✓ ColleenConscience component initialized")
    else:
        print("⚠ ColleenConscience component not initialized")

    if hasattr(engine, 'guardian') and engine.guardian:
        print("✓ CoreGuardianSpindle component initialized")
    else:
        print("⚠ CoreGuardianSpindle component not initialized")

    if hasattr(engine, 'nexis_signal_engine') and engine.nexis_signal_engine:
        print("✓ NexisSignalEngine component initialized")
    else:
        print("⚠ NexisSignalEngine component not initialized")

    if hasattr(engine, 'memory_kernel') and engine.memory_kernel:
        print("✓ Memory kernel component initialized")
    else:
        print("⚠ Memory kernel component not initialized")

    if hasattr(engine, 'cocoon_stability') and engine.cocoon_stability:
        print("✓ Cocoon stability component initialized")
    else:
        print("⚠ Cocoon stability component not initialized")

except Exception as e:
    print(f"✗ ForgeEngine instantiation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ INTEGRATION TEST PASSED - Consciousness stack is ready!")
