#!/usr/bin/env python3
"""
Codette Vulkan GPU Environment Setup
=====================================

Installs all dependencies required to use Vulkan compute acceleration
in Codette's inference and training pipelines.

This script will:

1. Install the kompute library (Vulkan compute for ML)
2. Install vulkan Python bindings (device enumeration)
3. Verify that a Vulkan-capable GPU is detected
4. Run a basic compute shader test

Prerequisites:
  - Vulkan-capable GPU (NVIDIA, AMD, Intel Arc, Qualcomm)
  - Vulkan runtime/drivers installed:
      NVIDIA: Included with driver 470+
      AMD:    Included with Adreno driver / Mesa
      Intel:  Included with Arc driver 31.0.101+
  - Python 3.9+
"""

import subprocess
import sys
import importlib
import os


def run(cmd: list[str]):
    """Run shell command and stream output."""
    print("\n>>>", " ".join(cmd))
    subprocess.check_call(cmd)


def pip_install(*packages):
    run([sys.executable, "-m", "pip", "install", *packages])


def check_vulkan_runtime() -> bool:
    """Check if the Vulkan runtime is available on the system."""
    print("\n--- Checking Vulkan Runtime ---")

    # Check for vulkaninfo or Vulkan DLLs
    if sys.platform == "win32":
        vulkan_dll = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            "System32", "vulkan-1.dll"
        )
        if os.path.exists(vulkan_dll):
            print(f"  Found: {vulkan_dll}")
            return True
        print(f"  Not found: {vulkan_dll}")
        return False
    else:
        # Linux/Mac: check for libvulkan.so
        import ctypes
        try:
            ctypes.CDLL("libvulkan.so.1")
            print("  Found: libvulkan.so.1")
            return True
        except OSError:
            try:
                ctypes.CDLL("libvulkan.dylib")
                print("  Found: libvulkan.dylib")
                return True
            except OSError:
                print("  Vulkan runtime library not found")
                return False


def install_kompute():
    """Install the kompute Vulkan compute library."""
    print("\n--- Installing kompute (Vulkan compute for ML) ---")
    try:
        pip_install("kp")
        return True
    except subprocess.CalledProcessError:
        print("  WARNING: kompute installation failed.")
        print("  This may require Vulkan SDK headers. See: https://kompute.cc")
        return False


def install_vulkan_bindings():
    """Install Python vulkan bindings for device enumeration."""
    print("\n--- Installing vulkan Python bindings ---")
    try:
        pip_install("vulkan")
        return True
    except subprocess.CalledProcessError:
        print("  WARNING: vulkan bindings installation failed.")
        return False


def verify_vulkan_compute() -> bool:
    """Verify Vulkan compute is functional."""
    print("\n--- Verifying Vulkan Compute ---")

    # Add inference directory to path for our adapter
    inference_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "inference"
    )
    if inference_dir not in sys.path:
        sys.path.insert(0, inference_dir)

    try:
        from vulkan_compute import VulkanComputeAdapter, detect_vulkan_devices

        devices = detect_vulkan_devices()
        if not devices:
            print("\n  No Vulkan-capable GPUs detected by Python bindings.")
            print("  Ensure Vulkan drivers are properly installed.")
            return False

        print(f"\n  Found {len(devices)} Vulkan device(s):")
        for dev in devices:
            print(f"    [{dev.device_id}] {dev.name} ({dev.vendor}, {dev.device_type})")

        # Functional test
        adapter = VulkanComputeAdapter()
        if adapter.initialize():
            adapter.create_tensor("test_a", [1.0, 2.0, 3.0])
            adapter.create_tensor("test_b", [4.0, 5.0, 6.0])
            adapter.vector_add("test_a", "test_b", "test_c")
            result = adapter.read_tensor("test_c")
            expected = [5.0, 7.0, 9.0]

            if result == expected:
                print(f"\n  Compute test PASSED: {result}")
                adapter.shutdown()
                return True
            else:
                print(f"\n  Compute test FAILED: got {result}, expected {expected}")
                adapter.shutdown()
                return False
        else:
            print("\n  Adapter initialization failed (device detected but compute unavailable)")
            return False

    except ImportError as e:
        print(f"\n  Import error: {e}")
        return False
    except Exception as e:
        print(f"\n  Verification error: {e}")
        return False


def main():
    print("\n" + "=" * 55)
    print("  Codette Vulkan GPU Setup")
    print("=" * 55)

    # Step 1: Check Vulkan runtime
    print("\nStep 1: Checking Vulkan runtime")
    runtime_ok = check_vulkan_runtime()
    if not runtime_ok:
        print("\n  ERROR: Vulkan runtime not found.")
        print("  Please install GPU drivers with Vulkan support:")
        print("    NVIDIA: https://www.nvidia.com/drivers")
        print("    AMD:    https://www.amd.com/en/support")
        print("    Intel:  https://www.intel.com/content/www/us/en/download-center")
        print("\n  After installing drivers, re-run this script.")
        return

    # Step 2: Install kompute
    print("\nStep 2: Installing kompute")
    kompute_ok = install_kompute()

    # Step 3: Install vulkan bindings
    print("\nStep 3: Installing vulkan Python bindings")
    vulkan_ok = install_vulkan_bindings()

    if not kompute_ok and not vulkan_ok:
        print("\n  ERROR: Neither kompute nor vulkan bindings could be installed.")
        print("  Vulkan compute will not be available.")
        return

    # Step 4: Verify
    print("\nStep 4: Verifying Vulkan compute")
    ok = verify_vulkan_compute()

    print("\n" + "=" * 55)
    if ok:
        print("  SUCCESS: Vulkan GPU compute is ready for Codette")
        print("\n  Usage in code:")
        print("    from vulkan_compute import VulkanComputeAdapter")
        print("    adapter = VulkanComputeAdapter()")
        print("    adapter.initialize()")
    else:
        print("  PARTIAL: Vulkan libraries installed but compute test inconclusive")
        print("  The adapter will fall back to CPU operations where needed.")
    print("=" * 55)


if __name__ == "__main__":
    main()
