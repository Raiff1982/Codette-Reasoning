"""Tests for the audio ingestion path that `twin_frequency_trust` never had.

`twin_frequency_trust.py` has had zero callers since it was written, because it
takes a WAV path and nothing in codette-clean ingests audio. The capability was
not missing — it was in the DAW project on N:, which is the same shape as every
other gap here. `voice_input` is the join.

Every test synthesises its own audio. Nothing reads a real recording, nothing
touches a microphone, and no identity verification is performed anywhere — that
is a separate decision and it is Jonathan's.
"""

import io
import math
import struct
import wave

import pytest

np = pytest.importorskip("numpy")

from signal_processing import voice_input  # noqa: E402
from signal_processing.twin_frequency_trust import (  # noqa: E402
    TwinFrequencyTrust,
    TwinTrustConfig,
)

RATE = 16000


def _tone_wav(freq=220.0, seconds=1.0, rate=RATE, channels=1, width=2) -> bytes:
    """A WAV of a pure tone, in memory. Harmonics added so the spectrum has
    structure to whiten rather than a single bin."""
    n = int(rate * seconds)
    frames = []
    for i in range(n):
        t = i / rate
        v = (math.sin(2 * math.pi * freq * t)
             + 0.5 * math.sin(2 * math.pi * freq * 2 * t)
             + 0.25 * math.sin(2 * math.pi * freq * 3 * t))
        s = int(max(-1.0, min(1.0, v / 1.75)) * 32000)
        frames.append(s)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        payload = b"".join(struct.pack("<h", s) for s in frames for _ in range(channels))
        wf.writeframes(payload)
    return buf.getvalue()


# ── decoding, from every input shape the DAW analyzer accepts ───────────────

def test_decode_bytes():
    d = voice_input.decode(_tone_wav())
    assert d.samplerate == RATE
    assert d.samples.dtype == np.float32
    assert 0.9 <= float(np.max(np.abs(d.samples))) <= 1.0
    assert d.duration_s == pytest.approx(1.0, abs=0.01)


def test_decode_path(tmp_path):
    p = tmp_path / "tone.wav"
    p.write_bytes(_tone_wav())
    assert voice_input.decode(str(p)).samplerate == RATE


def test_decode_numpy_requires_a_samplerate():
    arr = np.sin(np.linspace(0, 100, 1000)).astype(np.float32)
    with pytest.raises(ValueError):
        voice_input.decode(arr)
    assert voice_input.decode(arr, samplerate=RATE).samplerate == RATE


def test_stereo_is_mixed_to_mono():
    d = voice_input.decode(_tone_wav(channels=2))
    assert d.samples.ndim == 1
    assert d.duration_s == pytest.approx(1.0, abs=0.01)


def test_silence_does_not_divide_by_zero():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(RATE)
        wf.writeframes(b"\x00\x00" * RATE)
    d = voice_input.decode(buf.getvalue())
    assert float(np.max(np.abs(d.samples))) == 0.0


def test_unsupported_input_is_rejected():
    with pytest.raises(TypeError):
        voice_input.decode(12345)  # type: ignore[arg-type]


# ── framing matches what twin_frequency_trust expects ───────────────────────

def test_frames_have_the_configured_size_and_overlap():
    got = list(voice_input.frames(_tone_wav(seconds=1.0),
                                  frame_ms=200.0, hop_ms=100.0))
    assert len(got) == 9  # 1000ms, 200ms frames, 100ms hop
    frame, rate = got[0]
    assert rate == RATE
    assert len(frame) == int(RATE * 0.2)


def test_audio_shorter_than_one_frame_yields_nothing():
    """Not an error. A caller that gets no frames has its answer."""
    assert list(voice_input.frames(_tone_wav(seconds=0.05), frame_ms=200.0)) == []


# ── the join: twin_frequency_trust actually scores through it ───────────────

def _signature_from(audio_bytes):
    """Uses the module's own builder rather than reimplementing his maths — the
    first version of this test duplicated `build_reference_signature` and got
    the dataclass signature wrong, which is exactly the argument for the join
    living in the module instead of in the test."""
    return voice_input.reference_signature(audio_bytes)


def test_twin_frequency_trust_scores_through_this_path():
    """The whole point: the module that had no callers now has one."""
    sig = _signature_from(_tone_wav(freq=220.0))
    trust = TwinFrequencyTrust(sig, TwinTrustConfig())

    scores = [trust.score_frame(f, r)
              for f, r in voice_input.frames(_tone_wav(freq=220.0))]

    assert scores, "no frames reached the scorer"
    for s in scores:
        assert set(s) == {"cosine", "peak_overlap", "trust"}
        assert 0.0 <= s["trust"] <= 1.0


def test_the_same_source_scores_higher_than_a_different_one():
    """The instrument has to move in both directions to be worth anything —
    the standing rule. Same tone should out-score a clearly different one."""
    sig = _signature_from(_tone_wav(freq=220.0))
    trust = TwinFrequencyTrust(sig, TwinTrustConfig())

    same = np.mean([trust.score_frame(f, r)["trust"]
                    for f, r in voice_input.frames(_tone_wav(freq=220.0))])
    other = np.mean([trust.score_frame(f, r)["trust"]
                     for f, r in voice_input.frames(_tone_wav(freq=880.0))])

    assert same > other, (same, other)


# ── description falls back rather than failing ──────────────────────────────

def test_describe_reports_audio():
    info = voice_input.describe(_tone_wav())
    assert info["type"] == "audio"
    assert info["has_content"] is True
