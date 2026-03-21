# twin_frequency_trust.py
import numpy as np
import wave
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict

def _frame_hop_sampler(wav_path: str, frame_ms: float = 200.0, hop_ms: float = 100.0):
    """Yield mono float32 frames from a WAV file with overlap, normalized to [-1,1]."""
    with wave.open(wav_path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        frame_size = int(framerate * frame_ms / 1000.0)
        hop_size = int(framerate * hop_ms / 1000.0)

        raw = wf.readframes(n_frames)
        dtype = {1: np.int8, 2: np.int16, 3: np.int32, 4: np.int32}[sampwidth]
        data = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        if n_channels > 1:
            data = data.reshape(-1, n_channels).mean(axis=1)
        max_abs = np.max(np.abs(data)) or 1.0
        data = data / max_abs

        for start in range(0, len(data) - frame_size + 1, hop_size):
            frame = data[start:start + frame_size].copy()
            yield frame, framerate

def _magnitude_spectrum(x: np.ndarray, samplerate: int, fft_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
    if fft_size is None:
        target = max(512, int(2 ** np.ceil(np.log2(len(x)))))
        fft_size = min(target, 16384)
    if len(x) < fft_size:
        pad = np.zeros(fft_size, dtype=np.float32)
        pad[:len(x)] = x
        xw = pad
    else:
        xw = x[:fft_size]
    win = np.hanning(len(xw)).astype(np.float32)
    xw = xw * win
    X = np.fft.rfft(xw, n=fft_size)
    mag = np.abs(X).astype(np.float32)
    mag[0] = 0.0
    mag = np.log1p(mag)
    kernel = np.ones(5, dtype=np.float32) / 5.0
    env = np.convolve(mag, kernel, mode='same') + 1e-6
    mag_w = mag / env
    norm = np.linalg.norm(mag_w) or 1.0
    mag_n = mag_w / norm
    freqs = np.fft.rfftfreq(fft_size, d=1.0 / samplerate).astype(np.float32)
    return mag_n, freqs

def _find_peaks(mag: np.ndarray, freqs: np.ndarray, min_hz: float = 40.0, max_hz: float = 8000.0,
                top_k: int = 10, threshold_quantile: float = 0.90) -> Tuple[np.ndarray, np.ndarray]:
    mask = (freqs >= min_hz) & (freqs <= max_hz)
    cand_mags = mag[mask]
    cand_freqs = freqs[mask]
    if cand_mags.size == 0:
        return np.array([]), np.array([])
    thresh = np.quantile(cand_mags, threshold_quantile)
    idx = np.where(cand_mags >= thresh)[0]
    order = np.argsort(cand_mags[idx])[::-1][:top_k]
    sel_mags = cand_mags[idx][order]
    sel_freqs = cand_freqs[idx][order]
    return sel_freqs, sel_mags

@dataclass
class SpectralSignature:
    fft_size: int
    samplerate: int
    ref_vector: np.ndarray
    peak_freqs: np.ndarray
    peak_mags: np.ndarray

def build_reference_signature(wav_path: str, frame_ms: float = 400.0) -> SpectralSignature:
    frames = list(_frame_hop_sampler(wav_path, frame_ms=frame_ms, hop_ms=frame_ms))
    if not frames:
        raise ValueError("No frames read from WAV.")
    n_avg = min(5, len(frames))
    mags = []
    for i in range(n_avg):
        frame, sr = frames[i]
        mag, freqs = _magnitude_spectrum(frame, sr)
        mags.append(mag)
    ref_vec = np.mean(np.stack(mags, axis=0), axis=0).astype(np.float32)
    ref_vec = ref_vec / (np.linalg.norm(ref_vec) or 1.0)
    peak_freqs, peak_mags = _find_peaks(ref_vec, freqs)
    return SpectralSignature(fft_size=len(ref_vec) * 2 - 2, samplerate=sr,
                             ref_vector=ref_vec, peak_freqs=peak_freqs, peak_mags=peak_mags)

def spectral_cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        n = min(len(a), len(b))
        a = a[:n]
        b = b[:n]
    denom = (np.linalg.norm(a) or 1.0) * (np.linalg.norm(b) or 1.0)
    return float(np.dot(a, b) / denom)

def peak_overlap_score(freqs_a: np.ndarray, freqs_b: np.ndarray, tol_hz: float = 5.0) -> float:
    if len(freqs_a) == 0 or len(freqs_b) == 0:
        return 0.0
    hits = 0
    for fa in freqs_a:
        if np.any(np.abs(freqs_b - fa) <= tol_hz):
            hits += 1
    return hits / max(1, len(freqs_a))

@dataclass
class TwinTrustConfig:
    frame_ms: float = 200.0
    hop_ms: float = 100.0
    min_hz: float = 40.0
    max_hz: float = 8000.0
    top_k_peaks: int = 10
    peak_tol_hz: float = 5.0
    alpha_cosine: float = 0.7
    alpha_peaks: float = 0.3

class TwinFrequencyTrust:
    def __init__(self, signature: SpectralSignature, cfg: Optional[TwinTrustConfig] = None):
        self.sig = signature
        self.cfg = cfg or TwinTrustConfig()

    def score_frame(self, frame: np.ndarray, samplerate: int) -> Dict[str, float]:
        mag, freqs = _magnitude_spectrum(frame, samplerate, fft_size=self.sig.fft_size)
        cos = spectral_cosine_similarity(mag, self.sig.ref_vector)
        pf, pm = _find_peaks(mag, freqs, min_hz=self.cfg.min_hz, max_hz=self.cfg.max_hz, top_k=self.cfg.top_k_peaks)
        peak_score = peak_overlap_score(pf, self.sig.peak_freqs, tol_hz=self.cfg.peak_tol_hz)
        trust = self.cfg.alpha_cosine * cos + self.cfg.alpha_peaks * peak_score
        return {"cosine": float(cos), "peak_overlap": float(peak_score), "trust": float(trust)}

    def stream_score_wav(self, wav_path: str) -> List[Dict[str, float]]:
        scores = []
        for frame, sr in _frame_hop_sampler(wav_path, frame_ms=self.cfg.frame_ms, hop_ms=self.cfg.hop_ms):
            s = self.score_frame(frame, sr)
            scores.append(s)
        return scores

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description="Twin Frequency Trust: real-time-ish spectral twin detection.")
    parser.add_argument("--ref", required=True, help="Path to reference WAV file.")
    parser.add_argument("--test", required=True, help="Path to test WAV file to score.")
    parser.add_argument("--frame_ms", type=float, default=200.0)
    parser.add_argument("--hop_ms", type=float, default=100.0)
    parser.add_argument("--peak_tol_hz", type=float, default=5.0)
    args = parser.parse_args()

    sig = build_reference_signature(args.ref, frame_ms=400.0)
    cfg = TwinTrustConfig(frame_ms=args.frame_ms, hop_ms=args.hop_ms, peak_tol_hz=args.peak_tol_hz)
    model = TwinFrequencyTrust(sig, cfg)
    scores = model.stream_score_wav(args.test)
    print(json.dumps(scores[:10], indent=2))  # show first few frames
