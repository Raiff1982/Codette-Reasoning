"""VRAM is measured, and unreadable reads as unmeasured -- never a number.

2026-09-29, Jonathan: "she's not measuring vram". The substrate monitor read
only system RAM while the model ran on the GPU. No GPU or openvino exists where
these tests run, so OpenVINO is replaced by a stand-in Core.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "inference"))
psutil = pytest.importorskip("psutil")
import substrate_awareness as sa  # noqa: E402

GB = 1024 ** 3


class _Core:
    def __init__(self, props):
        self.props = props

    def get_property(self, device, name):
        if name not in self.props:
            raise RuntimeError(f"{name} unsupported")
        return self.props[name]


def test_reads_used_and_total(monkeypatch):
    monkeypatch.setattr(sa, "_OV_CORE", _Core({
        "GPU_DEVICE_TOTAL_MEM_SIZE": 16 * GB,
        "GPU_MEMORY_STATISTICS": {"usm_device": 5 * GB, "cl_mem": 1 * GB},
    }))
    v = sa.gpu_memory("GPU")
    assert (v["used_gb"], v["total_gb"], v["pct"]) == (6.0, 16.0, 37.5)
    assert v["source"] == "openvino GPU"


def test_total_only_says_usage_unreadable(monkeypatch):
    monkeypatch.setattr(sa, "_OV_CORE", _Core({"GPU_DEVICE_TOTAL_MEM_SIZE": 8 * GB}))
    v = sa.gpu_memory("GPU")
    assert v["total_gb"] == 8.0 and v["used_gb"] is None and v["pct"] is None
    assert "usage not readable" in v["source"]


def test_nothing_readable_is_unmeasured_not_zero(monkeypatch):
    monkeypatch.setattr(sa, "_OV_CORE", _Core({}))
    v = sa.gpu_memory("GPU")
    assert v["used_gb"] is None and v["total_gb"] is None
    assert v["source"].startswith("unmeasured")


def test_snapshot_carries_vram_fields(monkeypatch):
    monkeypatch.setattr(sa, "_OV_CORE", _Core({}))
    snap = sa.SubstrateMonitor().snapshot()
    for key in ("vram_used_gb", "vram_total_gb", "vram_pct", "vram_source",
                "memory_measured"):
        assert key in snap
    assert snap["vram_used_gb"] is None


def test_unreadable_ram_is_not_sixteen_gigabytes(monkeypatch):
    def boom():
        raise OSError("no")
    monkeypatch.setattr(sa.psutil, "virtual_memory", boom)
    monkeypatch.setattr(sa, "_OV_CORE", _Core({}))
    snap = sa.SubstrateMonitor().snapshot()
    assert snap["memory_measured"] is False
    assert snap["memory_available_gb"] is None


# ── Paging (2026-09-29, "we also are paging remember") ───────────────────────

def test_snapshot_reports_paging(monkeypatch):
    class _Sw:
        used, total, percent = 6 * GB, 24 * GB, 25.0
    monkeypatch.setattr(sa.psutil, "swap_memory", lambda: _Sw)
    monkeypatch.setattr(sa, "_OV_CORE", _Core({}))
    snap = sa.SubstrateMonitor().snapshot()
    assert (snap["paging_used_gb"], snap["paging_total_gb"], snap["paging_pct"]) == (6.0, 24.0, 25.0)


def test_unreadable_paging_is_unmeasured(monkeypatch):
    def boom():
        raise OSError("no")
    monkeypatch.setattr(sa.psutil, "swap_memory", boom)
    monkeypatch.setattr(sa, "_OV_CORE", _Core({}))
    snap = sa.SubstrateMonitor().snapshot()
    assert snap["paging_used_gb"] is None and snap["paging_pct"] is None
