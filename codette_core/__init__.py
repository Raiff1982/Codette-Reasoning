"""
codette_core Python bridge.

Tries to import the compiled Rust extension. If not built yet, falls back to
pure Python/numpy equivalents with identical signatures so nothing breaks.

To build the Rust extension:
    pip install maturin
    cd codette_core && maturin develop --release
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

_RUST_AVAILABLE = False

try:
    from codette_core.codette_core import (  # type: ignore
        cocoon_stability_check,
        nexis_fft_analysis,
        cosine_similarity,
    )
    _RUST_AVAILABLE = True
    logger.info("[codette_core] Rust extension loaded — FFT running at native speed")

except ImportError:
    logger.info("[codette_core] Rust extension not built — using numpy fallback")

    import numpy as np

    def cocoon_stability_check(
        text: str,
        energy_threshold: float = 0.85,
        vocab_threshold: float = 0.40,
    ) -> tuple[bool, float, float]:
        fft_size = 256
        char_codes = np.array(
            [ord(c) % 256 for c in text[:1000]], dtype=np.float32
        )
        if len(char_codes) == 0:
            return True, 0.0, 1.0

        padded = np.zeros(fft_size, dtype=np.float32)
        padded[: len(char_codes)] = char_codes
        spectrum = np.abs(np.fft.fft(padded)) ** 2
        total = spectrum.sum()

        energy_concentration = float(
            np.sort(spectrum)[::-1][:10].sum() / total
        ) if total > 0 else 0.0

        words = text.split()
        unique_ratio = (
            len(set(w.lower() for w in words)) / len(words) if words else 1.0
        )

        is_stable = energy_concentration < energy_threshold and unique_ratio >= vocab_threshold
        return is_stable, energy_concentration, float(unique_ratio)

    def nexis_fft_analysis(text: str, salt: int = 0) -> list[float]:
        freqs = [(ord(c) + salt) % 13 for c in text if c.isalpha()]
        if not freqs:
            return [0.0] * 8
        spectrum = np.fft.fft(freqs)
        result = spectrum.real[:8].tolist()
        result += [0.0] * (8 - len(result))
        return result

    def cosine_similarity(a: list[float], b: list[float]) -> float:
        va, vb = np.array(a), np.array(b)
        na, nb = np.linalg.norm(va), np.linalg.norm(vb)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))


__all__ = [
    "cocoon_stability_check",
    "nexis_fft_analysis",
    "cosine_similarity",
    "_RUST_AVAILABLE",
]
