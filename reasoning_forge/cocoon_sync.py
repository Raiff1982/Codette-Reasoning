"""
Federated Cocoon Synchronization Protocol — Encrypted state packaging,
HMAC signing, and attractor merger for distributed RC+xi nodes.

Implements:
  - Cocoon packaging with full RC+xi metrics
  - Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)
  - Attractor merger via weighted mean-field coupling (Eq. 12)
  - Phase coherence consensus (Gamma >= 0.98 target)
  - Secure sync protocol: package -> encrypt -> sign -> transmit -> verify -> merge

This module enables Codette Pods (edge nodes on RPi 5) to synchronize
their reasoning state without exposing raw data.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Encryption is optional — gracefully degrade if cryptography not installed
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CocoonPackage:
    """A packaged cocoon ready for sync."""
    cocoon_id: str
    node_id: str
    timestamp: float
    state_snapshot: Dict[str, Any]
    attractors: List[Dict]
    glyphs: List[Dict]
    metrics: Dict[str, float]
    payload_hash: str
    encrypted: bool = False
    raw_payload: Optional[bytes] = None
    signature: Optional[str] = None


@dataclass
class SyncResult:
    """Result of a cocoon synchronization."""
    success: bool
    merged_attractors: int
    new_glyphs: int
    coherence_before: float
    coherence_after: float
    tension_delta: float
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

class CocoonKeyManager:
    """Manages encryption keys for cocoon sync."""

    def __init__(self, key: Optional[bytes] = None):
        if key:
            self._key = key
        elif HAS_CRYPTO:
            self._key = Fernet.generate_key()
        else:
            self._key = os.urandom(32)

    @property
    def key(self) -> bytes:
        return self._key

    def derive_hmac_key(self) -> bytes:
        return hashlib.sha256(self._key + b"hmac_salt_cocoon").digest()


# ---------------------------------------------------------------------------
# CocoonSync
# ---------------------------------------------------------------------------

class CocoonSync:
    """Federated cocoon synchronization protocol."""

    def __init__(
        self,
        node_id: str,
        key_manager: Optional[CocoonKeyManager] = None,
        coherence_target: float = 0.98,
        tension_target: float = 0.05,
        ethical_target: float = 0.90,
    ):
        self.node_id = node_id
        self.key_manager = key_manager or CocoonKeyManager()
        self.coherence_target = coherence_target
        self.tension_target = tension_target
        self.ethical_target = ethical_target

        self._local_attractors: List[Dict] = []
        self._local_glyphs: List[Dict] = []
        self._sync_history: List[Dict] = []

    # -- Step 1: Package ----------------------------------------------------

    def package_cocoon(
        self,
        spiderweb_state: Dict[str, Any],
        phase_coherence: float,
        epistemic_tension: float,
        ethical_alignment: float,
        attractors: Optional[List[Dict]] = None,
        glyphs: Optional[List[Dict]] = None,
    ) -> CocoonPackage:
        """Package current state into a cocoon for transmission.

        Args:
            spiderweb_state: Serialized QuantumSpiderweb state.
            phase_coherence: Current Gamma value.
            epistemic_tension: Current xi value.
            ethical_alignment: Current AEGIS eta value.
            attractors: Detected attractor manifolds.
            glyphs: Identity glyphs formed.

        Returns:
            CocoonPackage ready for encryption and transmission.
        """
        cocoon_id = f"cocoon_{uuid.uuid4().hex[:12]}"

        metrics = {
            "phase_coherence": round(phase_coherence, 4),
            "epistemic_tension": round(epistemic_tension, 4),
            "ethical_alignment": round(ethical_alignment, 4),
            "timestamp": time.time(),
        }

        # Build payload
        payload = {
            "cocoon_id": cocoon_id,
            "node_id": self.node_id,
            "state": spiderweb_state,
            "attractors": attractors or [],
            "glyphs": glyphs or [],
            "metrics": metrics,
        }

        payload_json = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

        return CocoonPackage(
            cocoon_id=cocoon_id,
            node_id=self.node_id,
            timestamp=time.time(),
            state_snapshot=spiderweb_state,
            attractors=attractors or [],
            glyphs=glyphs or [],
            metrics=metrics,
            payload_hash=payload_hash,
            raw_payload=payload_json.encode(),
        )

    # -- Step 2: Encrypt ---------------------------------------------------

    def encrypt_cocoon(self, package: CocoonPackage) -> CocoonPackage:
        """Encrypt cocoon payload with Fernet (AES-128-CBC + HMAC-SHA256).

        Returns a new CocoonPackage; does not mutate the input.
        Falls back to XOR obfuscation if cryptography is not installed.
        """
        import copy
        result = copy.copy(package)

        if result.raw_payload is None:
            payload_json = json.dumps({
                "cocoon_id": result.cocoon_id,
                "node_id": result.node_id,
                "state": result.state_snapshot,
                "attractors": result.attractors,
                "glyphs": result.glyphs,
                "metrics": result.metrics,
            }, sort_keys=True, default=str)
            result.raw_payload = payload_json.encode()

        if HAS_CRYPTO:
            fernet = Fernet(self.key_manager.key)
            encrypted = fernet.encrypt(result.raw_payload)
            result.raw_payload = encrypted
            result.encrypted = True
        else:
            # Fallback: XOR obfuscation (not real encryption — placeholder)
            key_bytes = self.key_manager.key[:len(result.raw_payload)]
            obfuscated = bytes(
                a ^ b for a, b in
                zip(result.raw_payload, key_bytes * (len(result.raw_payload) // len(key_bytes) + 1))
            )
            result.raw_payload = obfuscated
            result.encrypted = True

        return result

    # -- Step 3: Sign ------------------------------------------------------

    def sign_cocoon(self, package: CocoonPackage) -> CocoonPackage:
        """Sign cocoon with HMAC-SHA256 for integrity verification.

        Returns a new CocoonPackage; does not mutate the input.
        """
        import copy
        result = copy.copy(package)
        hmac_key = self.key_manager.derive_hmac_key()
        data_to_sign = result.raw_payload or result.payload_hash.encode()
        signature = hmac.new(hmac_key, data_to_sign, hashlib.sha256).hexdigest()
        result.signature = signature
        return result

    # -- Step 4: Verify (receiving end) ------------------------------------

    def verify_cocoon(self, package: CocoonPackage) -> bool:
        """Verify HMAC signature of incoming cocoon."""
        if not package.signature:
            return False
        hmac_key = self.key_manager.derive_hmac_key()
        data_to_verify = package.raw_payload or package.payload_hash.encode()
        expected = hmac.new(hmac_key, data_to_verify, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, package.signature)

    # -- Step 5: Decrypt ---------------------------------------------------

    def decrypt_cocoon(self, package: CocoonPackage) -> Dict[str, Any]:
        """Decrypt cocoon payload.

        Returns the deserialized payload dict.
        """
        if not package.encrypted or package.raw_payload is None:
            return {
                "state": package.state_snapshot,
                "attractors": package.attractors,
                "glyphs": package.glyphs,
                "metrics": package.metrics,
            }

        if HAS_CRYPTO:
            fernet = Fernet(self.key_manager.key)
            decrypted = fernet.decrypt(package.raw_payload)
        else:
            # Reverse XOR
            key_bytes = self.key_manager.key[:len(package.raw_payload)]
            decrypted = bytes(
                a ^ b for a, b in
                zip(package.raw_payload, key_bytes * (len(package.raw_payload) // len(key_bytes) + 1))
            )

        return json.loads(decrypted.decode())

    # -- Step 6: Merge attractors ------------------------------------------

    def merge_attractors(
        self,
        local_attractors: List[Dict],
        remote_attractors: List[Dict],
        local_coherence: float = 0.95,
        merge_radius: float = 2.0,
    ) -> List[Dict]:
        """Weighted attractor merger via mean-field coupling (Eq. 12).

        alpha = local_coherence: higher coherence = trust local more.
        """
        alpha = min(local_coherence, 0.95)
        merged = list(local_attractors)

        for remote_att in remote_attractors:
            r_center = remote_att.get("center", [0] * 5)
            matched = False

            for local_att in merged:
                l_center = local_att.get("center", [0] * 5)
                # Compute distance
                dist = sum((a - b) ** 2 for a, b in zip(l_center, r_center)) ** 0.5
                if dist <= merge_radius:
                    # Weighted merge: c_merged = alpha * c_local + (1-alpha) * c_remote
                    new_center = [
                        alpha * lc + (1 - alpha) * rc
                        for lc, rc in zip(l_center, r_center)
                    ]
                    local_att["center"] = new_center
                    # Expand member list
                    local_att.setdefault("remote_members", [])
                    local_att["remote_members"].extend(
                        remote_att.get("members", [])
                    )
                    matched = True
                    break

            if not matched:
                # New attractor from remote
                merged.append({
                    "attractor_id": remote_att.get("attractor_id", f"remote_{len(merged)}"),
                    "center": r_center,
                    "members": remote_att.get("members", []),
                    "source": "remote",
                })

        return merged

    # -- Full sync protocol ------------------------------------------------

    def sync_with_remote(
        self,
        incoming_package: CocoonPackage,
        local_spiderweb_state: Dict[str, Any],
        local_coherence: float,
        local_tension: float,
    ) -> SyncResult:
        """Full sync protocol: verify -> decrypt -> merge -> report.

        Args:
            incoming_package: Encrypted cocoon from remote node.
            local_spiderweb_state: Current local web state.
            local_coherence: Current local Gamma.
            local_tension: Current local xi.

        Returns:
            SyncResult with merge statistics.
        """
        errors: List[str] = []

        # Verify
        if not self.verify_cocoon(incoming_package):
            return SyncResult(
                success=False, merged_attractors=0, new_glyphs=0,
                coherence_before=local_coherence, coherence_after=local_coherence,
                tension_delta=0.0, errors=["HMAC verification failed"],
            )

        # Decrypt
        try:
            remote_data = self.decrypt_cocoon(incoming_package)
        except Exception as e:
            return SyncResult(
                success=False, merged_attractors=0, new_glyphs=0,
                coherence_before=local_coherence, coherence_after=local_coherence,
                tension_delta=0.0, errors=[f"Decryption failed: {e}"],
            )

        # Check ethical alignment
        remote_eta = remote_data.get("metrics", {}).get("ethical_alignment", 0)
        if remote_eta < self.ethical_target:
            errors.append(
                f"Remote ethical alignment {remote_eta:.3f} below target {self.ethical_target}"
            )

        # Merge attractors
        remote_attractors = remote_data.get("attractors", [])
        local_attractors = self._extract_attractors(local_spiderweb_state)
        merged = self.merge_attractors(
            local_attractors, remote_attractors, local_coherence
        )
        new_attractor_count = len(merged) - len(local_attractors)

        # Collect new glyphs
        remote_glyphs = remote_data.get("glyphs", [])
        existing_ids = {g.get("glyph_id") for g in self._local_glyphs}
        new_glyphs = [g for g in remote_glyphs if g.get("glyph_id") not in existing_ids]
        self._local_glyphs.extend(new_glyphs)

        # Estimate new coherence (weighted average)
        remote_coherence = remote_data.get("metrics", {}).get("phase_coherence", 0.5)
        new_coherence = 0.7 * local_coherence + 0.3 * remote_coherence

        remote_tension = remote_data.get("metrics", {}).get("epistemic_tension", 0.5)
        tension_delta = remote_tension - local_tension

        # Record sync
        self._sync_history.append({
            "timestamp": time.time(),
            "remote_node": incoming_package.node_id,
            "merged_attractors": len(merged),
            "new_glyphs": len(new_glyphs),
            "coherence_after": new_coherence,
        })

        return SyncResult(
            success=True,
            merged_attractors=new_attractor_count,
            new_glyphs=len(new_glyphs),
            coherence_before=local_coherence,
            coherence_after=round(new_coherence, 4),
            tension_delta=round(tension_delta, 4),
            errors=errors,
        )

    def check_consensus(
        self,
        local_coherence: float,
        local_tension: float,
        local_eta: float,
    ) -> Dict[str, bool]:
        """Check if local node meets consensus criteria.

        Target: Gamma >= 0.98, xi <= 0.05, eta >= 0.90
        """
        return {
            "phase_coherence_met": local_coherence >= self.coherence_target,
            "tension_met": local_tension <= self.tension_target,
            "ethical_met": local_eta >= self.ethical_target,
            "consensus": (
                local_coherence >= self.coherence_target
                and local_tension <= self.tension_target
                and local_eta >= self.ethical_target
            ),
        }

    def _extract_attractors(self, web_state: Dict) -> List[Dict]:
        """Extract attractors from spiderweb state dict."""
        # Try to find attractors in the state
        if isinstance(web_state, dict):
            if "attractors" in web_state:
                return web_state["attractors"]
        return self._local_attractors

    def get_sync_status(self) -> Dict[str, Any]:
        """Return sync protocol status."""
        return {
            "node_id": self.node_id,
            "total_syncs": len(self._sync_history),
            "local_attractors": len(self._local_attractors),
            "local_glyphs": len(self._local_glyphs),
            "has_encryption": HAS_CRYPTO,
            "recent_syncs": self._sync_history[-5:],
        }
