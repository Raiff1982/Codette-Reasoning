"""
generate_figures_v8.py — Generate all figures for codette_paper_v8.tex

Run from the project root:
    python paper/generate_figures_v8.py

Outputs to paper/figures/ (creates it if needed):
    architecture_v8.png   — Phase 8 pipeline + full system layers
    latency_v8.png        — Runtime benchmark latency by category (May 2026)
    radar_v8.png          — Benchmark dimensions radar, all conditions
    v7_v8_compare.png     — Side-by-side v7 vs v8 key dimension deltas
    memory_curve.png      — Memory benefit (217 vs 951 cocoons)

All figures use a consistent colour palette and 300 DPI for print quality.
"""

import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import matplotlib.patheffects as pe

# ── Output directory ──────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "single":  "#9e9e9e",
    "multi":   "#5c85d6",
    "memory":  "#43a047",
    "codette": "#e53935",
    "bg":      "#fafafa",
    "border":  "#cccccc",
    "text":    "#212121",
    "accent":  "#ff6f00",
    "phase8a": "#1565c0",   # CognitionSubstrate
    "phase8b": "#6a1b9a",   # AuthoredState
    "phase8c": "#2e7d32",   # RenderLayer
}

DPI = 300


# ── 1. ARCHITECTURE DIAGRAM (Phase 8 pipeline) ───────────────────────────────

def fig_architecture():
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)
    ax.axis("off")
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    def box(x, y, w, h, label, sublabel, color, fontsize=9):
        rect = FancyBboxPatch((x, y), w, h,
                              boxstyle="round,pad=0.08",
                              facecolor=color, alpha=0.15,
                              edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h*0.62, label,
                ha="center", va="center", fontsize=fontsize,
                fontweight="bold", color=color)
        ax.text(x + w/2, y + h*0.25, sublabel,
                ha="center", va="center", fontsize=6.5,
                color=C["text"], style="italic", wrap=True)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", color=C["text"],
                                   lw=1.5, connectionstyle="arc3,rad=0"))

    # ── Phase 8 pipeline (top half) ──────────────────────────────────────────
    ax.text(5.5, 6.65, "Phase 8: Render / Cognition Separation",
            ha="center", va="center", fontsize=11, fontweight="bold",
            color=C["text"])

    box(0.3, 5.1, 2.6, 1.2,
        "CognitionSubstrate", "Zero LLM calls\nForgeEngine · Memory · Synthesizer",
        C["phase8a"])
    box(4.1, 5.1, 2.6, 1.2,
        "AuthoredState", "Typed cognitive artifact\nconclusion · evidence · confidence",
        C["phase8b"])
    box(7.9, 5.1, 2.8, 1.2,
        "RenderLayer", "LLM verbalization-only\nintegrity check post-render",
        C["phase8c"])

    arrow(2.9, 5.7, 4.1, 5.7)
    arrow(6.7, 5.7, 7.9, 5.7)

    ax.text(3.5,  5.85, "AuthoredState", ha="center", fontsize=6.5, color=C["phase8b"])
    ax.text(7.3,  5.85, "Natural language", ha="center", fontsize=6.5, color=C["phase8c"])

    # ── Full system layers (bottom half) ─────────────────────────────────────
    ax.text(5.5, 4.6, "Full System Layers", ha="center", fontsize=9,
            fontweight="bold", color=C["text"])

    layers = [
        ("Memory",    "951 cocoons · SQLite FTS5 · Supabase mirror",    0.3,  3.8),
        ("Routing",   "Query classifier · 10 LoRA adapters · fast-paths", 3.1, 3.8),
        ("AEGIS",     "6-framework ethical governance · 3 checkpoints",  5.9,  3.8),
        ("Integrity", "SycophancyGuard · DebateTracker · RoleTracker",   8.7,  3.8),
    ]
    colors = ["#0288d1", "#00838f", "#558b2f", "#6d4c41"]
    for (lbl, sub, x, y), col in zip(layers, colors):
        box(x, y, 2.5, 0.9, lbl, sub, col, fontsize=8)

    layers2 = [
        ("Self-Correction", "LOCK 6/7 · 18-pattern scrubber\ndirective leak scrub", 0.3,  2.7),
        ("Substrate Monitor", "Hardware pressure P\nrouting adaptation",             3.1,  2.7),
        ("Cocoon Synthesis", "CocoonSynthesizer\ncross-domain strategy forging",     5.9,  2.7),
        ("Identity Gov.",   "LivingMemoryKernelV2\nconfidence decay · anchors",      8.7,  2.7),
    ]
    colors2 = ["#4527a0", "#880e4f", "#e65100", "#1b5e20"]
    for (lbl, sub, x, y), col in zip(layers2, colors2):
        box(x, y, 2.5, 0.9, lbl, sub, col, fontsize=8)

    # ── Query → response flow ─────────────────────────────────────────────────
    ax.text(0.3, 2.35, "Query →", ha="left", fontsize=9, color=C["text"])
    ax.annotate("", xy=(10.7, 2.35), xytext=(1.4, 2.35),
                arrowprops=dict(arrowstyle="->", color=C["accent"],
                                lw=1.5, linestyle="dashed"))
    ax.text(10.75, 2.35, "Response", ha="left", fontsize=9, color=C["text"])

    # ── Hardware note ─────────────────────────────────────────────────────────
    ax.text(5.5, 0.35,
            "Llama 3.1 8B · Q4_K_M · 10 LoRA adapters · RTX GPU (35 layers) · "
            "Consumer hardware · Apache 2.0",
            ha="center", fontsize=7, color="#757575", style="italic")

    fig.tight_layout(pad=0.4)
    path = os.path.join(OUT, "architecture_v8.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print(f"  saved: {path}")


# ── 2. LATENCY FIGURE ─────────────────────────────────────────────────────────

def fig_latency():
    # Runtime benchmark May 26 2026 — category mean latencies (ms)
    categories = [
        "valuation\nreasoning",
        "grounded\ncorrectness",
        "governance\nstability",
        "continuity\nretention",
    ]
    latencies_ms = [3432.4, 70074.2, 87161.2, 411944.2]
    pass_rates   = [1.00,   0.00,     1.00,     0.00]
    colors = [C["memory"] if p == 1.0 else C["single"] for p in pass_rates]

    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    x = np.arange(len(categories))
    bars = ax.bar(x, [l/1000 for l in latencies_ms], color=colors,
                  width=0.55, edgecolor="white", linewidth=0.8)

    for bar, lat, pr in zip(bars, latencies_ms, pass_rates):
        label = f"{lat/1000:.1f}s"
        status = "PASS" if pr == 1.0 else "WARN"
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + 4,
                f"{label}\n({status})",
                ha="center", va="bottom", fontsize=8,
                color=C["memory"] if pr == 1.0 else "#b71c1c",
                fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylabel("Latency (seconds)", fontsize=10)
    ax.set_title("Runtime Benchmark Latency by Category (May 26, 2026)",
                 fontsize=11, fontweight="bold", pad=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, max(latencies_ms)/1000 * 1.22)

    legend = [
        mpatches.Patch(color=C["memory"], label="PASS (score ≥ target)"),
        mpatches.Patch(color=C["single"], label="WARN (score < target)"),
    ]
    ax.legend(handles=legend, fontsize=8, loc="upper left",
              framealpha=0.7, edgecolor=C["border"])

    ax.text(0.98, 0.02,
            "Mean latency: 115.2 s  ·  Pass rate: 60%",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.5, color="#757575", style="italic")

    fig.tight_layout()
    path = os.path.join(OUT, "latency_v8.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print(f"  saved: {path}")


# ── 3. RADAR CHART ────────────────────────────────────────────────────────────

def fig_radar():
    dims = ["Reasoning\nDepth", "Perspective\nDiversity", "Coherence",
            "Ethical\nCoverage", "Novelty", "Factual\nGrounding", "Turing\nNaturalness"]
    N = len(dims)

    # May 2026 benchmark data
    data = {
        "SINGLE":  [0.369, 0.324, 0.381, 0.088, 0.439, 0.395, 0.431],
        "MULTI":   [0.854, 0.946, 0.668, 0.390, 0.706, 0.612, 0.582],
        "MEMORY":  [0.872, 0.971, 0.693, 0.409, 0.729, 0.620, 0.713],
        "CODETTE": [0.863, 0.966, 0.700, 0.387, 0.701, 0.641, 0.820],
    }
    colours = {
        "SINGLE":  C["single"],
        "MULTI":   C["multi"],
        "MEMORY":  C["memory"],
        "CODETTE": C["codette"],
    }

    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dims, fontsize=8.5)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.50, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.0"], fontsize=7, color="#9e9e9e")
    ax.spines["polar"].set_color(C["border"])
    ax.grid(color=C["border"], linewidth=0.6)

    for cond, vals in data.items():
        v = vals + vals[:1]
        col = colours[cond]
        lw = 2.5 if cond == "CODETTE" else 1.5
        ax.plot(angles, v, color=col, linewidth=lw, label=cond)
        ax.fill(angles, v, color=col,
                alpha=0.18 if cond == "CODETTE" else 0.06)

    ax.set_title("Benchmark Dimensions by Condition\n(May 2026, N=17 problems)",
                 fontsize=11, fontweight="bold", pad=18, y=1.08)
    ax.legend(loc="upper right", bbox_to_anchor=(1.32, 1.15),
              fontsize=9, framealpha=0.8, edgecolor=C["border"])

    fig.tight_layout()
    path = os.path.join(OUT, "radar_v8.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print(f"  saved: {path}")


# ── 4. V7 vs V8 COMPARISON ───────────────────────────────────────────────────

def fig_v7_v8_compare():
    # Only showing the dimensions with notable change
    dims = ["Composite", "Coherence", "Turing\nNaturalness", "Memory\n(MEMORY-MULTI Δ)"]

    # CODETTE condition unless noted; Memory shows the delta
    v7 = [0.652, 0.477, 0.245, 0.018]   # April 2026
    v8 = [0.744, 0.700, 0.820, 0.031]   # May  2026

    x = np.arange(len(dims))
    w = 0.35

    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    b1 = ax.bar(x - w/2, v7, w, label="April 2026 (v7)", color="#90a4ae",
                edgecolor="white", linewidth=0.8)
    b2 = ax.bar(x + w/2, v8, w, label="May 2026 (v8)",   color=C["codette"],
                edgecolor="white", linewidth=0.8)

    for bar, val in zip(b1, v7):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.012,
                f"{val:.3f}", ha="center", va="bottom", fontsize=8, color="#546e7a")
    for bar, val in zip(b2, v8):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.012,
                f"{val:.3f}", ha="center", va="bottom", fontsize=8,
                color=C["codette"], fontweight="bold")

    # Delta annotations
    for i, (a, b) in enumerate(zip(v7, v8)):
        pct = (b - a) / a * 100
        sign = "+" if pct >= 0 else ""
        ax.text(i, max(a, b) + 0.06,
                f"{sign}{pct:.0f}%",
                ha="center", fontsize=8.5, color=C["accent"], fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(dims, fontsize=9.5)
    ax.set_ylabel("Score (0–1 scale)", fontsize=10)
    ax.set_title("v7 (April 2026) vs v8 (May 2026) — Key Metric Changes",
                 fontsize=11, fontweight="bold", pad=8)
    ax.set_ylim(0, 1.08)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9, framealpha=0.8, edgecolor=C["border"])

    ax.text(3 + w/2, v8[3] + 0.08,
            "p=0.020\nd=0.80",
            ha="center", fontsize=7, color=C["memory"],
            fontweight="bold")

    fig.tight_layout()
    path = os.path.join(OUT, "v7_v8_compare.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print(f"  saved: {path}")


# ── 5. MEMORY BENEFIT CURVE ───────────────────────────────────────────────────

def fig_memory_curve():
    """
    Two observed data points for MEMORY vs MULTI delta:
      217 cocoons → +0.004 (not significant)
      951 cocoons → +0.031 (p=0.020, d=0.80)
    Fit a simple sqrt curve as a plausible growth model.
    """
    observed_x = [217, 951]
    observed_y = [0.004, 0.031]

    # sqrt fit: y = a * sqrt(x) + b
    import numpy.polynomial.polynomial as poly
    # Use log-linear fit for illustration
    a = (observed_y[1] - observed_y[0]) / (math.sqrt(observed_x[1]) - math.sqrt(observed_x[0]))
    b = observed_y[0] - a * math.sqrt(observed_x[0])

    xs = np.linspace(50, 2000, 400)
    ys = np.clip(a * np.sqrt(xs) + b, 0, None)

    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    ax.plot(xs, ys, color=C["memory"], linewidth=2,
            label="Fitted curve (√N model)", linestyle="--")
    ax.scatter(observed_x, observed_y, color=C["codette"], s=80, zorder=5,
               label="Observed data points")

    ax.annotate(
        "217 cocoons\nΔ=+0.004, p=0.119\n(not significant)",
        xy=(217, 0.004), xytext=(320, 0.006),
        fontsize=7.5, color="#546e7a",
        arrowprops=dict(arrowstyle="->", color="#9e9e9e", lw=1),
    )
    ax.annotate(
        "951 cocoons\nΔ=+0.031, p=0.020\nd=0.80 ★",
        xy=(951, 0.031), xytext=(700, 0.024),
        fontsize=7.5, color=C["codette"], fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=C["codette"], lw=1.2),
    )

    ax.axhline(y=0, color=C["border"], linewidth=0.8, linestyle=":")
    ax.set_xlabel("Cocoon store size (N)", fontsize=10)
    ax.set_ylabel("MEMORY − MULTI composite Δ", fontsize=10)
    ax.set_title("Memory Augmentation Benefit vs. Cocoon Store Size",
                 fontsize=11, fontweight="bold", pad=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8.5, framealpha=0.8, edgecolor=C["border"])
    ax.text(0.98, 0.05,
            "Note: curve is illustrative; systematic\nlearning-curve study is future work.",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7, color="#9e9e9e", style="italic")

    fig.tight_layout()
    path = os.path.join(OUT, "memory_curve.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print(f"  saved: {path}")


# ── Run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating v8 figures...")
    fig_architecture()
    fig_latency()
    fig_radar()
    fig_v7_v8_compare()
    fig_memory_curve()
    print("Done. All figures written to paper/figures/")
