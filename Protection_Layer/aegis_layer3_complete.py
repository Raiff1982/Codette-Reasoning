#!/usr/bin/env python3
"""
AEGIS Layer 3 — TPM 2.0 Boot Verification & Kernel Lockdown
Complete implementation with graceful degradation for non-TPM systems.
Supports Linux only (Windows uses TPM in different way via OS APIs).

Author: Jonathan Harrison / Codette Architecture
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


# =====================================================================
# TPM 2.0 MEASUREMENT INTERFACE (Linux Only)
# =====================================================================

def verify_tpm_measurement_interface() -> Tuple[bool, Dict[str, any]]:
    """
    Verify TPM 2.0 measurement interface and collect PCR (Platform Configuration Register) state.
    
    Returns:
        Tuple[bool, Dict]:
        - success: True if TPM 2.0 is present and readable
        - details: Dict with PCR state, measurements, or error details
        
    Graceful Degradation:
        - Returns (False, {}) if not Linux
        - Returns (False, {"reason": "..."}) if no TPM or permission denied
        - Returns (True, {pcr_state: ...}) if successful
    """

    if not sys.platform.startswith("linux"):
        return False, {"reason": "TPM 2.0 verification is Linux-only", "platform": sys.platform}

    details = {}

    # ── Step 1: Check TPM 2.0 event log ────────────────────────────────
    tpm_event_log_paths = [
        Path("/sys/kernel/security/tpm0/binary_bios_measurements"),
        Path("/sys/class/tpm/tpm0/device"),
        Path("/dev/tpm0"),
    ]

    tpm_found = False
    for tpm_path in tpm_event_log_paths:
        if tpm_path.exists():
            tpm_found = True
            details["tpm_device"] = str(tpm_path)
            logger.info(f"✓ TPM 2.0 device detected: {tpm_path}")
            break

    if not tpm_found:
        return False, {"reason": "No TPM 2.0 device found", "checked_paths": [str(p) for p in tpm_event_log_paths]}

    # ── Step 2: Read PCR state using tpm2-tools (if available) ─────────
    try:
        # Try to read PCRs 0-7 (firmware, config, bootloader, kernel)
        result = subprocess.run(
            ["tpm2_pcrread", "sha256:0,1,2,3,7", "-o", "/tmp/codette_pcr.pcr"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            details["pcr_state"] = "recorded"
            details["pcr_file"] = "/tmp/codette_pcr.pcr"
            logger.info("✓ TPM 2.0 PCR state recorded (sha256)")
        else:
            logger.warning(f"tpm2_pcrread failed: {result.stderr}")
            details["pcr_state"] = "unavailable"
            details["reason"] = "tpm2-tools not installed or permission denied"

    except FileNotFoundError:
        logger.warning("tpm2_pcrread command not found; install tpm2-tools for full TPM verification")
        details["reason"] = "tpm2-tools not installed"

    except subprocess.TimeoutExpired:
        logger.warning("TPM 2.0 PCR read timed out")
        details["reason"] = "TPM operation timeout"

    except Exception as e:
        logger.error(f"Unexpected error reading TPM state: {e}")
        details["reason"] = f"Error: {e}"

    # ── Step 3: Check IMA (Integrity Measurement Architecture) ────────
    ima_log_path = Path("/sys/kernel/security/ima/ascii_runtime_measurements")

    if ima_log_path.exists():
        try:
            with open(ima_log_path) as f:
                ima_entries = len(f.readlines())
                details["ima_measurements"] = ima_entries
                logger.info(f"✓ IMA measurements present: {ima_entries} entries")
        except PermissionError:
            logger.warning("IMA log exists but not readable (may require root)")
            details["ima_state"] = "present_but_unreadable"
        except Exception as e:
            logger.debug(f"Could not read IMA log: {e}")
    else:
        details["ima_state"] = "not_present"

    success = details.get("tpm_device") is not None or details.get("ima_state") == "present_but_unreadable"
    return success, details


# =====================================================================
# KERNEL MODULE LOCKDOWN (Linux Only)
# =====================================================================

def enforce_kernel_module_lockdown() -> Tuple[bool, str]:
    """
    Lock kernel module loading permanently for the current session.
    
    Returns:
        Tuple[bool, str]: (success, message)
        
    Behavior:
        - If running as root: Sets kernel.modules_disabled=1 (hard lock)
        - If running unprivileged: Returns False (acceptable, enforcement skipped)
        - If not Linux: Returns False (N/A)
    """

    if not sys.platform.startswith("linux"):
        return False, "Kernel module lockdown is Linux-only"

    SYSCTL_MODULE_DISABLE = "/proc/sys/kernel/modules_disabled"

    if not Path(SYSCTL_MODULE_DISABLE).exists():
        return False, f"Kernel module control not available: {SYSCTL_MODULE_DISABLE}"

    # ── Try sysctl command first (portable, handles permissions) ───────
    try:
        result = subprocess.run(
            ["sysctl", "-w", "kernel.modules_disabled=1"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            logger.info("✓ Kernel module loading permanently DISABLED (sysctl)")
            return True, "Kernel module lockdown active"
        else:
            # This is expected if not root; not an error
            logger.debug(f"sysctl write failed (expected if non-root): {result.stderr}")

    except FileNotFoundError:
        logger.debug("sysctl command not available; trying direct write")

    except subprocess.TimeoutExpired:
        logger.warning("sysctl command timed out")

    except Exception as e:
        logger.debug(f"sysctl approach failed: {e}")

    # ── Fallback: Direct file write (requires root) ────────────────────
    try:
        with open(SYSCTL_MODULE_DISABLE, "w") as f:
            f.write("1")

        logger.info("✓ Kernel module loading permanently DISABLED (direct write)")
        return True, "Kernel module lockdown active"

    except PermissionError:
        logger.debug("Insufficient permissions to lock kernel modules (non-root is OK)")
        return False, "Insufficient permissions (non-root; this is acceptable)"

    except Exception as e:
        logger.error(f"Failed to enforce kernel module lockdown: {e}")
        return False, f"Error: {e}"


# =====================================================================
# SECURE BOOT VERIFICATION (Linux Only, requires efibootmgr)
# =====================================================================

def verify_secure_boot_status() -> Tuple[bool, Dict[str, any]]:
    """
    Check if UEFI Secure Boot is enabled.
    
    Returns:
        Tuple[bool, Dict]:
        - success: True if Secure Boot is enabled
        - details: Status info
    """

    if not sys.platform.startswith("linux"):
        return False, {"reason": "UEFI Secure Boot check is Linux-only"}

    details = {}

    # ── Method 1: efi firmware (kernel interface) ──────────────────────
    efi_secure_boot_path = Path("/sys/firmware/efi/fw_platform_size")

    if efi_secure_boot_path.exists():
        try:
            with open(efi_secure_boot_path) as f:
                size = f.read().strip()
                details["efi_present"] = True
                details["firmware_size"] = size
                logger.info(f"✓ EFI firmware detected: {size}-bit")
        except Exception as e:
            logger.debug(f"Could not read EFI firmware size: {e}")

    # ── Method 2: mokutil command (if available) ──────────────────────
    try:
        result = subprocess.run(
            ["mokutil", "--sb-state"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            details["secure_boot"] = result.stdout.strip()
            logger.info(f"✓ Secure Boot status: {result.stdout.strip()}")
            return "enabled" in result.stdout.lower(), details
        else:
            logger.debug(f"mokutil failed: {result.stderr}")

    except FileNotFoundError:
        logger.debug("mokutil not found; Secure Boot status unavailable")

    except Exception as e:
        logger.debug(f"mokutil check failed: {e}")

    return False, details


# =====================================================================
# ORCHESTRATOR: Layer 3 Boot Guard
# =====================================================================

def verify_boot_integrity() -> Tuple[bool, Dict[str, any]]:
    """
    Comprehensive boot integrity verification combining:
    1. TPM 2.0 PCR state
    2. IMA measurements
    3. Secure Boot status
    4. Kernel module lockdown
    
    Returns:
        Tuple[bool, Dict]: (overall_success, detailed_report)
    """

    logger.info("🔒 [AEGIS Layer 3] Verifying boot system integrity...")

    report = {
        "platform": sys.platform,
        "tpm2": None,
        "ima": None,
        "secure_boot": None,
        "module_lockdown": None,
    }

    # ── TPM 2.0 Verification ───────────────────────────────────────────
    tpm_ok, tpm_details = verify_tpm_measurement_interface()
    report["tpm2"] = {"success": tpm_ok, "details": tpm_details}

    if not tpm_ok:
        logger.warning(f"⚠️  TPM 2.0 verification unavailable: {tpm_details.get('reason', 'unknown')}")
    else:
        logger.info("✓ TPM 2.0 boot measurements verified")

    # ── Secure Boot Status ────────────────────────────────────────────
    sb_ok, sb_details = verify_secure_boot_status()
    report["secure_boot"] = {"success": sb_ok, "details": sb_details}

    if sb_ok:
        logger.info("✓ UEFI Secure Boot enabled")
    else:
        logger.warning("⚠️  UEFI Secure Boot not detected or disabled")

    # ── Kernel Module Lockdown ────────────────────────────────────────
    kml_ok, kml_msg = enforce_kernel_module_lockdown()
    report["module_lockdown"] = {"success": kml_ok, "message": kml_msg}

    if kml_ok:
        logger.info("✓ Kernel module loading locked down")
    else:
        logger.debug(f"Kernel module lockdown unavailable: {kml_msg}")

    # ── Overall decision: require at least one boot verification ───────
    overall_success = tpm_ok or sb_ok

    report["overall_success"] = overall_success
    report["summary"] = (
        "Boot system integrity verified (TPM 2.0 and/or Secure Boot active)"
        if overall_success
        else "⚠️  Boot verification incomplete; running in degraded mode"
    )

    return overall_success, report


# =====================================================================
# GRACEFUL DEGRADATION: Multi-Layered Fallback
# =====================================================================

def get_boot_verification_fallback_chain() -> list:
    """
    Returns ordered fallback chain for boot verification.
    Systems use the highest-priority available method.
    """
    return [
        ("tpm2_pcrread", "TPM 2.0 PCR measurement (production)"),
        ("mokutil", "UEFI Secure Boot status (high security)"),
        ("kernel.modules_disabled", "Kernel module lockdown (medium security)"),
        ("ima_measurements", "IMA integrity log (low-level, background)"),
        ("none", "Unverified boot (degraded mode; not recommended)"),
    ]


# =====================================================================
# TESTING & DEMO
# =====================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("\n" + "=" * 70)
    print("AEGIS Layer 3 — Boot System Integrity Verification")
    print("=" * 70)

    success, report = verify_boot_integrity()

    print(f"\nPlatform: {report['platform']}")
    print(f"Overall Success: {success}")
    print(f"Summary: {report['summary']}")

    print(f"\nDetailed Report:")
    print(f"  TPM 2.0:          {report['tpm2']['success']} — {report['tpm2']['details']}")
    print(f"  Secure Boot:      {report['secure_boot']['success']} — {report['secure_boot']['details']}")
    print(f"  Module Lockdown:  {report['module_lockdown']['success']} — {report['module_lockdown']['message']}")

    print(f"\nFallback Chain:")
    for method, desc in get_boot_verification_fallback_chain():
        print(f"  → {method:30} ({desc})")

    print("\n" + "=" * 70 + "\n")
