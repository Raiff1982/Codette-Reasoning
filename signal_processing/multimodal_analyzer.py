"""Multimodal input analysis — PORTED, not written here.

Source: HorizonCoreLab Studio (the DAW project), at
    N:/Horizon/HorizonDAW/DAW/Codette/src/components/multimodal_analyzer.py
Ported verbatim 2026-08-12. sha256 of the source at port time:
    5efb2fcd6fd913546da4cca2a021cade6c62fe0d2fc3ccb9ac6cf627404bdcf5

Why it is here: `signal_processing/twin_frequency_trust.py` has had ZERO callers
since it was written, because it takes a WAV path and nothing in codette-clean
ingests audio — `inference/codette_server.py` has no audio path at all. Jonathan,
2026-08-12: *"N:/ look in here all her audio capabilities are in the DAW
project"* and *"we can use what ive done there to fix what we got"*. They were
never missing; they were in the other tree, which is the recurring shape in this
repository (see CLAUDE.md, and the components/* gap that closed the same way).

DIVERGENCE FROM THE DAW COPY, recorded as this header requires:

  `import imghdr` is guarded. imghdr was REMOVED from the standard library in
  Python 3.13, and both trees run 3.14, so the DAW copy raises ModuleNotFoundError
  on import today — which also breaks `src/components/ai_core_identityscan.py` and
  `src/components/ai_core_system.py`, both of which import this module. It is used
  in exactly one place, sniffing an image format, and nothing on the audio path
  touches it. Guarded here so the audio ingestion works; the DAW copy still needs
  the same fix.

Do not edit this to diverge further from the DAW copy without saying so here. If the two
need to differ, record why — the house rule is that lineage stays legible.

The DAW keeps it under `src/components/`; codette-clean has no `components/`
package, so it sits beside the module that needed it.

--- original module docstring follows ---
"""

"""
Codette Multimodal Analyzer

Provides lightweight, dependency-safe analysis helpers for text, image,
audio and video inputs. Functions accept either raw bytes, a filesystem
path (str) or simple Python objects (e.g. numpy arrays for audio).

This module intentionally avoids heavy mandatory dependencies. If
optional libraries (Pillow, OpenCV) are installed, the analyzer will use
them for richer metadata extraction; otherwise it falls back to safe
heuristics and headers.
"""

from typing import Dict, Any, List, Union, Optional
import io
import os
try:  # removed from the standard library in Python 3.13
    import imghdr  # type: ignore
except ImportError:  # pragma: no cover - the 3.13+ path
    imghdr = None
import mimetypes
import wave
import struct

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import cv2
except Exception:
    cv2 = None

try:
    import numpy as np
except Exception:
    np = None


class MultimodalAnalyzer:
    def __init__(self):
        self.supported_modalities = {
            "text": self._analyze_text,
            "image": self._analyze_image,
            "audio": self._analyze_audio,
            "video": self._analyze_video,
        }

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for modality, data in content.items():
            handler = self.supported_modalities.get(modality)
            if handler is None:
                results[modality] = {"error": "Unsupported modality"}
                continue
            try:
                results[modality] = handler(data)
            except Exception as e:
                results[modality] = {"error": str(e)}
        return results

    def _analyze_text(self, text: Union[str, bytes]) -> Dict[str, Any]:
        if isinstance(text, bytes):
            try:
                text = text.decode("utf-8", errors="replace")
            except Exception:
                text = str(text)
        text = text or ""
        words = [w for w in text.split() if w]
        unique_words = set(w.strip(".,!?;:\"()[]{}") for w in words)
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        has_questions = "?" in text
        has_exclamations = "!" in text
        language = "en" if all(ord(c) < 128 for c in text) else "non-en"
        return {
            "type": "text",
            "length": len(text),
            "word_count": len(words),
            "unique_word_count": len(unique_words),
            "avg_word_length": round(avg_word_len, 2),
            "has_content": bool(text.strip()),
            "has_questions": has_questions,
            "has_exclamations": has_exclamations,
            "language_estimate": language,
        }

    def _read_bytes_or_path(self, data: Union[bytes, str]) -> Optional[bytes]:
        if data is None:
            return None
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            if os.path.exists(data):
                try:
                    with open(data, "rb") as f:
                        return f.read()
                except Exception:
                    return None
            # treat string as raw small payload
            return data.encode("utf-8", errors="replace")
        return None

    def _analyze_image(self, image_data: Union[bytes, str, None]) -> Dict[str, Any]:
        raw = self._read_bytes_or_path(image_data)
        info: Dict[str, Any] = {"type": "image", "has_content": bool(raw)}
        if not raw:
            return info
        fmt = None
        try:
            fmt = imghdr.what(None, h=raw) if imghdr is not None else None
        except Exception:
            fmt = None
        if fmt:
            info["format"] = fmt
        else:
            # fallback to mime type by filename if provided
            if isinstance(image_data, str):
                mt, _ = mimetypes.guess_type(image_data)
                info["format"] = mt or "unknown"
            else:
                info["format"] = "unknown"
        if Image is not None:
            try:
                img = Image.open(io.BytesIO(raw))
                info.update({
                    "width": img.width,
                    "height": img.height,
                    "mode": img.mode,
                    "has_alpha": "A" in img.getbands(),
                })
                img.close()
            except Exception:
                pass
        return info

    def _analyze_audio(self, audio_data: Union[bytes, str, Any, None]) -> Dict[str, Any]:
        info: Dict[str, Any] = {"type": "audio", "has_content": False, "format": "unknown"}
        if audio_data is None:
            return info
        if np is not None and isinstance(audio_data, np.ndarray):
            arr = audio_data
            info["has_content"] = getattr(arr, "size", 0) > 0
            info["format"] = "numpy.ndarray"
            try:
                samples = arr.astype(float)
                rms = float(np.sqrt(np.mean(samples ** 2)))
                info["rms"] = float(rms)
                info["duration_seconds_estimate"] = None
            except Exception:
                pass
            return info

        raw = self._read_bytes_or_path(audio_data)
        if not raw:
            return info
        info["has_content"] = True
        # Try WAV detection
        try:
            bio = io.BytesIO(raw)
            with wave.open(bio, "rb") as w:
                nchannels = w.getnchannels()
                sampwidth = w.getsampwidth()
                framerate = w.getframerate()
                nframes = w.getnframes()
                duration = nframes / float(framerate) if framerate else None
                info.update({
                    "format": "wav",
                    "channels": nchannels,
                    "sample_width": sampwidth,
                    "frame_rate": framerate,
                    "n_frames": nframes,
                    "duration_seconds": duration,
                })
                try:
                    frames = w.readframes(min(nframes, 44100))
                    if frames:
                        # unpack frames to numpy array for RMS
                        if sampwidth == 1:
                            dtype = np.uint8
                        elif sampwidth == 2:
                            dtype = np.int16
                        elif sampwidth == 4:
                            dtype = np.int32
                        else:
                            dtype = np.int16
                        samples = np.frombuffer(frames, dtype=dtype).astype(float)
                        if nchannels > 1:
                            samples = samples.reshape(-1, nchannels)
                            samples = samples.mean(axis=1)
                        rms = float(np.sqrt(np.mean((samples) ** 2)))
                        info["rms"] = rms
                except Exception:
                    pass
                return info
        except wave.Error:
            pass
        except Exception:
            pass
        # fallback: try to guess mime type by filename
        if isinstance(audio_data, str):
            mt, _ = mimetypes.guess_type(audio_data)
            if mt:
                info["format"] = mt
        return info

    def _analyze_video(self, video_data: Union[bytes, str, None]) -> Dict[str, Any]:
        info: Dict[str, Any] = {"type": "video", "has_content": False, "format": "unknown"}
        raw = self._read_bytes_or_path(video_data)
        if not raw:
            return info
        info["has_content"] = True
        if isinstance(video_data, str):
            mt, _ = mimetypes.guess_type(video_data)
            if mt:
                info["format"] = mt
        # If OpenCV is available, try to extract metadata
        if cv2 is not None and isinstance(video_data, str) and os.path.exists(video_data):
            try:
                cap = cv2.VideoCapture(video_data)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS) or None
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                    duration = frame_count / fps if fps else None
                    info.update({
                        "fps": fps,
                        "frame_count": frame_count,
                        "width": width,
                        "height": height,
                        "duration_seconds": duration,
                    })
                cap.release()
            except Exception:
                pass
        return info

    def combine_modalities(self, analyses: Dict[str, Any]) -> Dict[str, Any]:
        modalities_present = [k for k, v in analyses.items() if not v.get("error")]
        summary = {
            "modalities_present": modalities_present,
            "modality_count": len(modalities_present),
            "complete_analysis": all(not v.get("error") for v in analyses.values()),
            "analyses": analyses,
        }
        if "text" in analyses and "image" in analyses:
            t = analyses.get("text", {})
            img = analyses.get("image", {})
            summary["text_and_image"] = {
                "text_length": t.get("length"),
                "image_size": (img.get("width"), img.get("height")),
            }
        return summary

    def get_supported_modalities(self) -> List[str]:
        return list(self.supported_modalities.keys())