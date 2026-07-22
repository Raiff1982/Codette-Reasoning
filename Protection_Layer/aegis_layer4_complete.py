#!/usr/bin/env python3
"""
AEGIS Protection Layer 4 — ML-KEM-768 + ML-DSA-65 Post-Quantum Cryptography.

Real lattice-based cryptography via liboqs-python (Open Quantum Safe project).
Algorithms: ML-KEM-768 (NIST FIPS 203) for key encapsulation,
            ML-DSA-65  (NIST FIPS 204) for digital signatures.

First import triggers C library compilation (~5 min on first run, cached after).
Keys are persisted at ~/.codette/pqc/ — regeneration invalidates existing seals.

Install: pip install liboqs-python
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Algorithm resolution ──────────────────────────────────────────────────────
# Try NIST FIPS names first (liboqs >= 0.10), fall back to legacy Kyber/Dilithium names.
_KEM_CANDIDATES = ("ML-KEM-768", "Kyber768")
_SIG_CANDIDATES = ("ML-DSA-65", "Dilithium3")

_resolved_kem: Optional[str] = None
_resolved_sig: Optional[str] = None


def _resolve_algorithms() -> Tuple[str, str]:
    global _resolved_kem, _resolved_sig
    if _resolved_kem and _resolved_sig:
        return _resolved_kem, _resolved_sig
    try:
        import oqs
    except ImportError as exc:
        raise RuntimeError(
            "liboqs-python not importable. Run: pip install liboqs-python\n"
            "First import compiles the C library and may take several minutes."
        ) from exc

    enabled_kems = set(oqs.get_enabled_kem_mechanisms())
    enabled_sigs = set(oqs.get_enabled_sig_mechanisms())

    for name in _KEM_CANDIDATES:
        if name in enabled_kems:
            _resolved_kem = name
            break
    for name in _SIG_CANDIDATES:
        if name in enabled_sigs:
            _resolved_sig = name
            break

    if not _resolved_kem:
        raise RuntimeError(f"No usable KEM found. Available: {sorted(enabled_kems)}")
    if not _resolved_sig:
        raise RuntimeError(f"No usable signature scheme found. Available: {sorted(enabled_sigs)}")

    logger.info(f"[Layer4] PQC resolved — KEM: {_resolved_kem}, Sig: {_resolved_sig}")
    return _resolved_kem, _resolved_sig


# ── Key bundle ────────────────────────────────────────────────────────────────

@dataclass
class _PQCKeyBundle:
    kem_public: bytes
    kem_private: bytes
    sig_public: bytes
    sig_private: bytes


# ── PQCKeyStore ───────────────────────────────────────────────────────────────

_DEFAULT_KEY_DIR = Path.home() / ".codette" / "pqc"
_FILE_MAGIC = b"CODETTE_PQC_V1\x00"


class PQCKeyStore:
    """
    Persistent ML-KEM-768 + ML-DSA-65 keypair manager.
    Keys are binary-encoded with a magic header at ~/.codette/pqc/.

    WARNING: Calling generate(force=True) destroys existing keys and invalidates
    all cocoon seals written with the old keypair.
    """

    def __init__(self, key_dir: Optional[Path] = None) -> None:
        self._dir = Path(key_dir) if key_dir else _DEFAULT_KEY_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._bundle: Optional[_PQCKeyBundle] = None

    def _path(self, name: str) -> Path:
        return self._dir / f"{name}.bin"

    def _write(self, name: str, data: bytes) -> None:
        self._path(name).write_bytes(_FILE_MAGIC + data)

    def _read(self, name: str) -> bytes:
        raw = self._path(name).read_bytes()
        if not raw.startswith(_FILE_MAGIC):
            raise ValueError(f"Key file {name}.bin has wrong magic — corrupted?")
        return raw[len(_FILE_MAGIC):]

    def generate(self, force: bool = False) -> _PQCKeyBundle:
        """Generate a fresh keypair. If keys already exist and force=False, loads them."""
        if not force and self._path("kem_public").exists():
            return self.load()

        import oqs
        kem_alg, sig_alg = _resolve_algorithms()

        with oqs.KeyEncapsulation(kem_alg) as kem:
            kem_pub = kem.generate_keypair()
            kem_priv = kem.export_secret_key()

        with oqs.Signature(sig_alg) as sig:
            sig_pub = sig.generate_keypair()
            sig_priv = sig.export_secret_key()

        bundle = _PQCKeyBundle(kem_pub, kem_priv, sig_pub, sig_priv)
        for name, blob in (
            ("kem_public", kem_pub),
            ("kem_private", kem_priv),
            ("sig_public", sig_pub),
            ("sig_private", sig_priv),
        ):
            self._write(name, blob)

        logger.info(f"[Layer4] Generated new PQC keypair at {self._dir}")
        self._bundle = bundle
        return bundle

    def load(self) -> _PQCKeyBundle:
        """Load existing keypair. Raises FileNotFoundError if no keys saved yet."""
        bundle = _PQCKeyBundle(
            kem_public=self._read("kem_public"),
            kem_private=self._read("kem_private"),
            sig_public=self._read("sig_public"),
            sig_private=self._read("sig_private"),
        )
        self._bundle = bundle
        return bundle

    def load_or_generate(self) -> _PQCKeyBundle:
        try:
            return self.load()
        except FileNotFoundError:
            return self.generate()

    @property
    def bundle(self) -> _PQCKeyBundle:
        if self._bundle is None:
            self._bundle = self.load_or_generate()
        return self._bundle


# ── CocoonSeal ────────────────────────────────────────────────────────────────

@dataclass
class CocoonSeal:
    """Seal metadata stored alongside a cocoon record."""
    kem_ciphertext: bytes
    hmac_tag: bytes
    alg: str


# ── PQCCocoonSealer ───────────────────────────────────────────────────────────

class PQCCocoonSealer:
    """
    Seals cocoon memory records using ML-KEM-768 key encapsulation.

    Protocol (per seal):
      1. Encapsulate against persistent ML-KEM-768 public key
         → (ciphertext, shared_secret)  [one-time ephemeral shared secret]
      2. Derive seal key: SHA3-256(shared_secret || b"CODETTE_COCOON_SEAL_v1")
      3. Compute HMAC-SHA3-256(payload, seal_key) → tag
      4. Store (ciphertext, tag) as seal metadata alongside the cocoon

    Verification:
      1. Decapsulate ciphertext with persistent ML-KEM-768 private key
         → shared_secret  [same as step 1 due to KEM correctness]
      2. Re-derive seal key
      3. Verify HMAC — attacker without the private key cannot forge valid tags
    """

    _SALT = b"CODETTE_COCOON_SEAL_v1"

    def __init__(self, store: Optional[PQCKeyStore] = None) -> None:
        self._store = store or PQCKeyStore()

    def _seal_key(self, shared_secret: bytes) -> bytes:
        return hashlib.sha3_256(shared_secret + self._SALT).digest()

    def seal(self, payload: bytes) -> CocoonSeal:
        import oqs
        kem_alg, _ = _resolve_algorithms()
        pub = self._store.bundle.kem_public

        with oqs.KeyEncapsulation(kem_alg) as kem:
            ciphertext, shared_secret = kem.encap_secret(pub)

        key = self._seal_key(shared_secret)
        tag = _hmac.new(key, payload, hashlib.sha3_256).digest()
        return CocoonSeal(kem_ciphertext=ciphertext, hmac_tag=tag, alg=kem_alg)

    def verify(self, payload: bytes, seal: CocoonSeal) -> bool:
        import oqs
        kem_alg, _ = _resolve_algorithms()
        priv = self._store.bundle.kem_private

        try:
            with oqs.KeyEncapsulation(kem_alg, secret_key=priv) as kem:
                shared_secret = kem.decap_secret(seal.kem_ciphertext)
        except Exception as exc:
            logger.warning(f"[Layer4] Decapsulation failed: {exc}")
            return False

        key = self._seal_key(shared_secret)
        expected = _hmac.new(key, payload, hashlib.sha3_256).digest()
        return _hmac.compare_digest(expected, seal.hmac_tag)

    def seal_dict(self, record: dict) -> dict:
        """Return record with '_pqc_seal' field added."""
        payload = json.dumps(record, sort_keys=True, ensure_ascii=False).encode()
        s = self.seal(payload)
        return {
            **record,
            "_pqc_seal": {
                "kem_ciphertext": s.kem_ciphertext.hex(),
                "hmac_tag": s.hmac_tag.hex(),
                "alg": s.alg,
            },
        }

    def verify_dict(self, record: dict) -> bool:
        """Verify a record that was sealed with seal_dict."""
        raw = record.get("_pqc_seal")
        if not raw:
            return False
        clean = {k: v for k, v in record.items() if k != "_pqc_seal"}
        payload = json.dumps(clean, sort_keys=True, ensure_ascii=False).encode()
        seal = CocoonSeal(
            kem_ciphertext=bytes.fromhex(raw["kem_ciphertext"]),
            hmac_tag=bytes.fromhex(raw["hmac_tag"]),
            alg=raw["alg"],
        )
        return self.verify(payload, seal)


# ── PQCBootVerifier ───────────────────────────────────────────────────────────

@dataclass
class FileSignatureRecord:
    path: str
    sha3_256: str
    signature: str
    sig_public_key: str
    alg: str


_DEFAULT_CRITICAL_FILES = [
    "reasoning_forge/forge_engine.py",
    "inference/codette_server.py",
    "inference/codette_orchestrator.py",
    "Protection_Layer/aegis_orchestrator.py",
    "Protection_Layer/aegis_layer4_complete.py",
]


class PQCBootVerifier:
    """
    Signs SHA3-256 hashes of critical source files with ML-DSA-65.
    Run sign_files() once after any trusted code change.
    Call verify_files() at server startup to detect tampering.
    """

    _MANIFEST = "boot_manifest.json"

    def __init__(
        self,
        critical_files: Optional[List[str]] = None,
        store: Optional[PQCKeyStore] = None,
        manifest_dir: Optional[Path] = None,
    ) -> None:
        self._files = critical_files if critical_files is not None else _DEFAULT_CRITICAL_FILES
        self._store = store or PQCKeyStore()
        self._manifest_dir = manifest_dir or _DEFAULT_KEY_DIR

    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha3_256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def sign_files(self, base_dir: Optional[str] = None) -> List[FileSignatureRecord]:
        """Hash all critical files and sign each hash with ML-DSA-65."""
        import oqs
        _, sig_alg = _resolve_algorithms()
        bundle = self._store.bundle
        base = Path(base_dir) if base_dir else Path.cwd()
        records: List[FileSignatureRecord] = []

        with oqs.Signature(sig_alg, secret_key=bundle.sig_private) as signer:
            for rel in self._files:
                full = base / rel
                if not full.exists():
                    logger.warning(f"[Layer4] sign_files: skipping missing {rel}")
                    continue
                digest = self._hash_file(full)
                sig = signer.sign(digest.encode())
                records.append(FileSignatureRecord(
                    path=rel,
                    sha3_256=digest,
                    signature=sig.hex(),
                    sig_public_key=bundle.sig_public.hex(),
                    alg=sig_alg,
                ))

        manifest = self._manifest_dir / self._MANIFEST
        manifest.write_text(
            json.dumps([vars(r) for r in records], indent=2),
            encoding="utf-8",
        )
        logger.info(f"[Layer4] Signed {len(records)} files → {manifest}")
        return records

    def verify_files(self, base_dir: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Verify all signed files against the saved manifest.
        Returns (all_ok, list_of_failures).
        """
        import oqs
        _, sig_alg = _resolve_algorithms()
        manifest = self._manifest_dir / self._MANIFEST
        if not manifest.exists():
            return False, ["[boot manifest missing — run sign_files() first]"]

        records = json.loads(manifest.read_text(encoding="utf-8"))
        base = Path(base_dir) if base_dir else Path.cwd()
        failures: List[str] = []

        with oqs.Signature(sig_alg) as verifier:
            for rec in records:
                full = base / rec["path"]
                if not full.exists():
                    failures.append(f"{rec['path']} [missing]")
                    continue
                current = self._hash_file(full)
                if current != rec["sha3_256"]:
                    failures.append(f"{rec['path']} [hash mismatch]")
                    continue
                ok = verifier.verify(
                    current.encode(),
                    bytes.fromhex(rec["signature"]),
                    bytes.fromhex(rec["sig_public_key"]),
                )
                if not ok:
                    failures.append(f"{rec['path']} [signature invalid]")

        if failures:
            logger.error(f"[Layer4] Boot verification FAILED: {failures}")
        else:
            logger.info("[Layer4] Boot verification PASSED")
        return len(failures) == 0, failures


# ── EpistemicQuantumGate ──────────────────────────────────────────────────────

@dataclass
class PerspectiveVector:
    name: str
    weights: List[float]

    def normalize(self) -> "PerspectiveVector":
        total = sum(self.weights) or 1.0
        return PerspectiveVector(self.name, [w / total for w in self.weights])


class EpistemicQuantumGate:
    """
    Computes perspective tension:
        ξ_t = (1/k) Σᵢ ||Aᵢ − Ā||²

    Aᵢ is the probability distribution of perspective i, Ā is their mean.
    Analogous to quantum decoherence across competing measurement bases.

    Accepts real ForgeEngine perspective vectors; falls back to deterministic
    pseudo-random synthetic vectors derived from perspective names for contexts
    where the ForgeEngine is not in the call stack.
    """

    def __init__(self, vocab_size: int = 128) -> None:
        self._vocab = vocab_size
        self._history: List[float] = []

    def compute_tension(self, vectors: List[PerspectiveVector]) -> float:
        if not vectors:
            return 0.0
        normed = [v.normalize() for v in vectors]
        k = len(normed)
        dim = len(normed[0].weights)
        mean = [sum(v.weights[i] for v in normed) / k for i in range(dim)]
        tension = sum(
            sum((v.weights[i] - mean[i]) ** 2 for i in range(dim))
            for v in normed
        ) / k
        self._history.append(tension)
        return tension

    def synthetic_tension(self, perspective_names: List[str]) -> float:
        """Deterministic fallback: derive vectors from perspective name hashes."""
        vectors = []
        for name in perspective_names:
            seed = int(hashlib.sha3_256(name.encode()).hexdigest(), 16) % (2 ** 32)
            state = seed
            weights = []
            for _ in range(self._vocab):
                state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
                weights.append(state / 0xFFFFFFFF)
            vectors.append(PerspectiveVector(name, weights))
        return self.compute_tension(vectors)

    @property
    def history(self) -> List[float]:
        return list(self._history)

    @property
    def mean_tension(self) -> float:
        return sum(self._history) / len(self._history) if self._history else 0.0


# ── PQCShield — orchestrator facade ──────────────────────────────────────────

class PQCShield:
    """
    Public facade for AEGIS Layer 4.
    Imported by aegis_orchestrator.py — exposes PQCKeyStore, PQCCocoonSealer,
    PQCBootVerifier, and EpistemicQuantumGate through a single object.

    All liboqs calls are lazy: the C library is loaded only when a method
    actually needs it, so importing this module never stalls the server.
    """

    def __init__(self, key_dir: Optional[str] = None) -> None:
        kd = Path(key_dir) if key_dir else _DEFAULT_KEY_DIR
        self._store = PQCKeyStore(key_dir=kd)
        self._sealer = PQCCocoonSealer(store=self._store)
        self._verifier = PQCBootVerifier(store=self._store)
        self._gate = EpistemicQuantumGate()
        self._ready = False
        self._error: Optional[str] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> bool:
        """Load or generate the PQC keypair. Must succeed before sealing/verifying."""
        try:
            self._store.load_or_generate()
            self._ready = True
            logger.info("[Layer4] PQCShield initialized")
            return True
        except Exception as exc:
            self._error = str(exc)
            logger.error(f"[Layer4] PQCShield init failed: {exc}")
            return False

    # ── Key access ────────────────────────────────────────────────────────────

    def generate_lattice_keypair(self) -> Tuple[bytes, bytes]:
        """Return (kem_public_key, sig_public_key)."""
        b = self._store.bundle
        return b.kem_public, b.sig_public

    # ── Cocoon sealing ────────────────────────────────────────────────────────

    def seal_cocoon(self, payload: bytes) -> Dict:
        """Seal raw bytes. Returns {'kem_ciphertext', 'hmac_tag', 'alg'} hex dict."""
        s = self._sealer.seal(payload)
        return {
            "kem_ciphertext": s.kem_ciphertext.hex(),
            "hmac_tag": s.hmac_tag.hex(),
            "alg": s.alg,
        }

    def verify_cocoon(self, payload: bytes, seal_meta: Dict) -> bool:
        """Verify a seal produced by seal_cocoon."""
        try:
            seal = CocoonSeal(
                kem_ciphertext=bytes.fromhex(seal_meta["kem_ciphertext"]),
                hmac_tag=bytes.fromhex(seal_meta["hmac_tag"]),
                alg=seal_meta["alg"],
            )
            return self._sealer.verify(payload, seal)
        except Exception as exc:
            logger.warning(f"[Layer4] verify_cocoon error: {exc}")
            return False

    def seal_dict(self, record: Dict) -> Dict:
        """Convenience wrapper: seal a dict record, return it with '_pqc_seal' key."""
        return self._sealer.seal_dict(record)

    def verify_dict(self, record: Dict) -> bool:
        """Verify a dict record that was sealed with seal_dict."""
        return self._sealer.verify_dict(record)

    # ── Boot verification ─────────────────────────────────────────────────────

    def sign_boot_files(self, base_dir: Optional[str] = None) -> int:
        """Sign critical files and save manifest. Returns count of signed files."""
        records = self._verifier.sign_files(base_dir=base_dir)
        return len(records)

    def verify_boot(self, base_dir: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Verify boot-time file integrity. Returns (ok, list_of_failures)."""
        return self._verifier.verify_files(base_dir=base_dir)

    # ── Epistemic tension ─────────────────────────────────────────────────────

    def compute_tension(
        self,
        perspective_names: Optional[List[str]] = None,
        vectors: Optional[List[PerspectiveVector]] = None,
    ) -> float:
        """Compute ξ_t. Uses real vectors when provided, synthetic fallback otherwise."""
        if vectors:
            return self._gate.compute_tension(vectors)
        if perspective_names:
            return self._gate.synthetic_tension(perspective_names)
        return 0.0

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def last_error(self) -> Optional[str]:
        return self._error

    def status(self) -> Dict:
        kem, sig = "unknown", "unknown"
        try:
            kem, sig = _resolve_algorithms()
        except Exception:
            pass
        return {
            "layer": 4,
            "name": "PQC Cocoon Sealing (ML-KEM-768 + ML-DSA-65)",
            "initialized": self._ready,
            "kem_algorithm": kem,
            "sig_algorithm": sig,
            "key_dir": str(self._store._dir),
            "mean_tension": self._gate.mean_tension,
            "error": self._error,
        }


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("\n" + "=" * 65)
    print("AEGIS Layer 4 — ML-KEM-768 + ML-DSA-65 Integration Test")
    print("=" * 65)

    shield = PQCShield()
    if not shield.initialize():
        print(f"[FAIL] Init failed: {shield.last_error}")
        sys.exit(1)

    kem_pub, sig_pub = shield.generate_lattice_keypair()
    print(f"\n[KEY] KEM public key:  {len(kem_pub)} bytes ({kem_pub[:8].hex()}...)")
    print(f"[KEY] Sig public key:  {len(sig_pub)} bytes ({sig_pub[:8].hex()}...)")

    # Seal / verify bytes
    payload = b'{"concept": "test", "perspective": "newton"}'
    sealed = shield.seal_cocoon(payload)
    ok = shield.verify_cocoon(payload, sealed)
    print(f"\n[SEAL] Ciphertext: {sealed['kem_ciphertext'][:16]}...")
    print(f"[SEAL] HMAC tag:   {sealed['hmac_tag'][:16]}...")
    print(f"[SEAL] Verify:     {'PASS' if ok else 'FAIL'}")

    # Tamper check
    tampered = payload + b" tampered"
    ok_bad = shield.verify_cocoon(tampered, sealed)
    print(f"[SEAL] Tamper detect: {'PASS (correctly rejected)' if not ok_bad else 'FAIL'}")

    # Seal / verify dict
    rec = {"query": "what is entropy?", "answer": "disorder"}
    sealed_rec = shield.seal_dict(rec)
    ok_dict = shield.verify_dict(sealed_rec)
    print(f"\n[DICT] Seal+verify dict: {'PASS' if ok_dict else 'FAIL'}")

    # Epistemic tension (synthetic)
    tension = shield.compute_tension(
        perspective_names=["newton", "einstein", "curie", "hawking", "quantum"]
    )
    print(f"\n[GATE] Epistemic tension ξ_t = {tension:.6f}")

    print("\n" + shield.status().__repr__())
    print("\n✓ Layer 4 complete\n")
