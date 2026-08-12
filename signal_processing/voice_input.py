#!/usr/bin/env python3
"""Audio ingestion for `twin_frequency_trust` — the missing input path.

`signal_processing/twin_frequency_trust.py` has had **zero callers** since it was
written. Not because it is wrong — it is the spectral identity metric, and its
whitening is the algorithm `reasoning_forge/lexical_whitening.py` now uses — but
because it only accepts a filesystem path to a WAV, and nothing in codette-clean
ingests audio. `inference/codette_server.py` has no audio path at all.

Jonathan, 2026-08-12: *"N:/ look in here all her audio capabilities are in the
DAW project"*, then *"we can use what ive done there to fix what we got"*. They
were never missing. They were in the other tree — the same shape as every other
gap in this repository.

So this module is the join: it takes audio the way the DAW's analyzer takes it
(raw bytes, a filesystem path, or a numpy array) and produces exactly what
`TwinFrequencyTrust.score_frame` wants — overlapping mono float32 frames
normalised to [-1, 1], with their sample rate.

It deliberately does NOT open an HTTP endpoint. Accepting uploaded audio is new
attack surface sitting directly beside the identity path whose credential was
rotated on 2026-08-11, and that is a decision rather than a wiring job. This
module is importable, testable, and reachable only from code.

WHAT THIS ENABLES, and what it does not: with an input path, voice-based identity
verification becomes buildable — score a recording against a reference signature
to check it is Jonathan. **Nothing here does that**, and nothing here should
until he decides it should. Authentication is not something to switch on as a
side effect of fixing an unwired import.
"""

from __future__ import annotations

import io
import logging
import wave
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple, Union

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is present wherever this is used
    np = None  # type: ignore

# Matches TwinTrustConfig's defaults, so the two agree unless told otherwise.
DEFAULT_FRAME_MS = 200.0
DEFAULT_HOP_MS = 100.0

AudioInput = Union[bytes, str, "np.ndarray"]

_SAMPLE_DTYPES = {1: "int8", 2: "int16", 3: "int32", 4: "int32"}


@dataclass
class DecodedAudio:
    """Mono float32 in [-1, 1], plus the rate it was sampled at."""

    samples: "np.ndarray"
    samplerate: int

    @property
    def duration_s(self) -> float:
        return len(self.samples) / self.samplerate if self.samplerate else 0.0


def decode(audio: AudioInput, samplerate: Optional[int] = None) -> DecodedAudio:
    """Accept bytes, a path, or a numpy array; return mono float32 in [-1, 1].

    `samplerate` is required only for a raw numpy array, which carries no header.
    Mirrors the normalisation in `twin_frequency_trust._frame_hop_sampler` so a
    frame decoded here scores identically to one read from a WAV path there.
    """
    if np is None:
        raise RuntimeError("numpy is required to decode audio")

    if isinstance(audio, np.ndarray):
        if samplerate is None:
            raise ValueError("samplerate is required when passing a numpy array")
        data = audio.astype(np.float32)
        if data.ndim > 1:
            data = data.mean(axis=1)
        return DecodedAudio(_normalise(data), int(samplerate))

    if isinstance(audio, (bytes, bytearray)):
        handle: Union[io.BytesIO, str] = io.BytesIO(bytes(audio))
    elif isinstance(audio, str):
        handle = audio
    else:
        raise TypeError(f"unsupported audio input: {type(audio).__name__}")

    with wave.open(handle, "rb") as wf:  # type: ignore[arg-type]
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    dtype = _SAMPLE_DTYPES.get(width)
    if dtype is None:
        raise ValueError(f"unsupported sample width: {width} bytes")

    data = np.frombuffer(raw, dtype=np.dtype(dtype)).astype(np.float32)
    if channels > 1:
        # Trim a ragged tail before reshaping rather than raising — a truncated
        # final frame is common in captured audio and is not an error.
        usable = (len(data) // channels) * channels
        data = data[:usable].reshape(-1, channels).mean(axis=1)
    return DecodedAudio(_normalise(data), rate)


def _normalise(data: "np.ndarray") -> "np.ndarray":
    peak = float(np.max(np.abs(data))) if data.size else 0.0
    return (data / peak).astype(np.float32) if peak else data.astype(np.float32)


def frames(audio: AudioInput, samplerate: Optional[int] = None,
           frame_ms: float = DEFAULT_FRAME_MS,
           hop_ms: float = DEFAULT_HOP_MS) -> Iterator[Tuple["np.ndarray", int]]:
    """Yield `(frame, samplerate)` pairs ready for `TwinFrequencyTrust.score_frame`.

    Same contract as `twin_frequency_trust._frame_hop_sampler`, but sourced from
    anything rather than only from a WAV on disk. Yields nothing when the audio
    is shorter than one frame — silence is not an error, and a caller that gets
    no frames has its answer.
    """
    decoded = decode(audio, samplerate)
    size = int(decoded.samplerate * frame_ms / 1000.0)
    hop = int(decoded.samplerate * hop_ms / 1000.0)
    if size <= 0 or hop <= 0:
        return
    for start in range(0, len(decoded.samples) - size + 1, hop):
        yield decoded.samples[start:start + size].copy(), decoded.samplerate


def reference_signature(audio: AudioInput, samplerate: Optional[int] = None,
                        frame_ms: float = 400.0):
    """`build_reference_signature`, but from bytes or an array as well as a path.

    Mirrors `twin_frequency_trust.build_reference_signature` step for step —
    average the first five frames' whitened spectra, unit-normalise, take the
    peaks off the averaged vector — so a signature built here is interchangeable
    with one built there. Kept in this module rather than added to his file: the
    house rule is that his module stays his, and the join lives on this side.
    """
    from signal_processing.twin_frequency_trust import (
        SpectralSignature, _find_peaks, _magnitude_spectrum,
    )

    collected = list(frames(audio, samplerate, frame_ms=frame_ms, hop_ms=frame_ms))
    if not collected:
        raise ValueError("no frames read from audio")

    mags = []
    freqs = None
    rate = collected[0][1]
    for frame, sr in collected[:5]:
        mag, freqs = _magnitude_spectrum(frame, sr)
        mags.append(mag)
        rate = sr
    ref_vec = np.mean(np.stack(mags, axis=0), axis=0).astype(np.float32)
    ref_vec = ref_vec / (float(np.linalg.norm(ref_vec)) or 1.0)
    peak_freqs, peak_mags = _find_peaks(ref_vec, freqs)
    return SpectralSignature(fft_size=len(ref_vec) * 2 - 2, samplerate=rate,
                             ref_vector=ref_vec, peak_freqs=peak_freqs,
                             peak_mags=peak_mags)


def describe(audio: AudioInput) -> dict:
    """Metadata via the DAW's analyzer, so both trees describe audio identically.

    Falls back to this module's own decode if the analyzer is unavailable, rather
    than failing — the ported analyzer is optional dressing on a working path.
    """
    try:
        from signal_processing.multimodal_analyzer import MultimodalAnalyzer
        return MultimodalAnalyzer()._analyze_audio(audio)
    except Exception as exc:
        logger.debug("multimodal analyzer unavailable (%s); using local decode", exc)
        try:
            decoded = decode(audio)
        except Exception:
            return {"type": "audio", "has_content": False, "format": "unknown"}
        return {
            "type": "audio",
            "has_content": bool(decoded.samples.size),
            "format": "wav",
            "sample_rate": decoded.samplerate,
            "duration_s": round(decoded.duration_s, 4),
        }
