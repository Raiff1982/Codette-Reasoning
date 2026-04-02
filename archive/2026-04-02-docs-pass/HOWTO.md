# Codette Training Lab — HOWTO Guide
## For Jonathan (and Future Jonathan Who Forgot Everything)

---

## Quick Reference: What Goes Where

```
codette-training-lab/
├── adapters/                    # GGUF LoRA adapter files (~27MB each)
│   ├── newton-lora-f16.gguf     # Trained, working
│   ├── davinci-lora-f16.gguf    # Trained, working
│   └── (6 more after HF job)   # empathy, philosophy, quantum, etc.
│
├── bartowski/                   # Base GGUF model (Q4_K_M, ~4.6GB)
│   └── Meta-Llama-3.1-8B-Instruct-GGUF/
│       └── Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
│
├── datasets/                    # Training data (8 JSONL files, ~20K examples total)
│   ├── newton_reasoning.jsonl   # 3000 examples
│   ├── davinci_reasoning.jsonl  # 2500 examples
│   └── (6 more...)
│
├── inference/                   # Everything for RUNNING Codette
│   ├── codette_orchestrator.py  # Main brain: routes queries to adapters
│   ├── adapter_router.py        # Keyword/LLM routing engine
│   ├── model_loader.py          # Transformers-based model loader (GPU path)
│   ├── codette_chat_ui.py       # Legacy tkinter chat UI (still works!)
│   ├── codette_server.py        # NEW: Web UI backend (FastAPI-free)
│   ├── codette_session.py       # NEW: Cocoon-backed session manager
│   └── static/                  # NEW: Web UI frontend
│       ├── index.html           # Single-page chat app
│       ├── style.css            # Dark theme + adapter colors
│       ├── app.js               # Chat logic + streaming
│       └── spiderweb.js         # Canvas visualization of agent network
│
├── reasoning_forge/             # RC+xi reasoning engine (v2.0)
│   ├── forge_engine.py          # Main forge: 3 modes (single, feedback, debate)
│   ├── epistemic_metrics.py     # Tension/coherence/coverage scoring
│   ├── quantum_spiderweb.py     # 5D belief graph + attractors + glyphs
│   ├── cocoon_sync.py           # Fernet-encrypted state sync protocol
│   ├── synthesis_engine.py      # Multi-perspective synthesis
│   └── critic_agent.py          # Meta-evaluation agent
│
├── training/                    # Everything for TRAINING adapters
│   ├── train_hf_job_v3.py       # HuggingFace cloud GPU training (A10G)
│   ├── train_cpu_lean.py        # Local CPU Pipeline 1 (~18GB RAM)
│   ├── train_cpu_offload.py     # Local CPU Pipeline 2 (~8-12GB RAM)
│   └── (other training scripts)
│
├── dataset_engine/              # Dataset generation from concepts
├── evaluation/                  # Eval scripts
├── research/                    # Papers, frameworks, experiments
├── configs/                     # YAML configs for adapters/pipeline
│
├── codette_chat.bat             # Double-click: launch tkinter chat UI
├── train_local.bat              # Launch local CPU training
└── codette_web.bat              # NEW: Double-click: launch web UI
```

---

## How To: Launch Codette (Chat)

### Option A: Web UI (Recommended)
```
Double-click: codette_web.bat
   OR
J:\python.exe J:\codette-training-lab\inference\codette_server.py
   THEN open: http://localhost:7860
```

### Option B: Legacy Tkinter UI
```
Double-click: codette_chat.bat
   OR
J:\python.exe J:\codette-training-lab\inference\codette_chat_ui.py
```

### Option C: Command Line
```
J:\python.exe J:\codette-training-lab\inference\codette_orchestrator.py
J:\python.exe J:\codette-training-lab\inference\codette_orchestrator.py --query "How does gravity work?"
J:\python.exe J:\codette-training-lab\inference\codette_orchestrator.py --adapter newton --query "F=ma"
```

---

## How To: Train Adapters

### Cloud (HuggingFace GPU — Fast, ~10-20 min per adapter)
1. Go to huggingface.co/jobs
2. Submit `training/train_hf_job_v3.py` as a UV job
3. Select `a10g-small` flavor, 8h timeout
4. Add secret: `HF_TOKEN=$HF_TOKEN`
5. Trained adapters auto-upload to `Raiff1982/codette-lora-adapters`

### Local CPU (Slow but free)
```
train_local.bat lean newton          # Pipeline 1: ~18GB RAM, ~30-90s/step
train_local.bat offload empathy      # Pipeline 2: ~8-12GB RAM, ~2-5min/step
train_local.bat lean --list          # Show available adapters
```

### After Training: Convert to GGUF
```
J:\python.exe J:\TheAI\llama.cpp\convert_lora_to_gguf.py ^
  --base J:\codette-training-lab\bartowski\Meta-Llama-3.1-8B-Instruct-GGUF\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf ^
  --lora /path/to/trained/adapter ^
  --outfile J:\codette-training-lab\adapters\ADAPTERNAME-lora-f16.gguf
```

---

## How To: Add a New Adapter After Training

1. Convert HuggingFace adapter to GGUF (see above)
2. Place the `.gguf` file in `adapters/` folder
3. Edit `inference/codette_orchestrator.py`:
   - Uncomment the adapter in `ADAPTER_GGUF_MAP`
4. Restart Codette — the router auto-discovers available adapters

---

## The Cocoon System (How Codette Remembers)

The Cocoon is Codette's encrypted memory system:

- **QuantumSpiderweb**: A 5D graph where each reasoning agent is a node.
  Nodes have states (psi, tau, chi, phi, lambda) representing thought magnitude,
  temporal progression, processing speed, emotional valence, and semantic weight.

- **Attractors**: When agents' beliefs converge, they form attractor clusters.
  These represent stable consensus points in Codette's reasoning.

- **Glyphs**: Identity signatures formed from FFT-compressed tension history.
  They're like fingerprints of how Codette reasoned about a topic.

- **CocoonSync**: Encrypts the entire spiderweb state with Fernet (AES-128-CBC),
  signs it with HMAC-SHA256, and can sync between Codette instances.

- **Sessions**: Each conversation saves a cocoon package. When you come back,
  Codette loads the cocoon and remembers not just WHAT you discussed, but
  HOW she was thinking about it — which attractors had formed, which
  perspectives were in tension.

### Key Metrics
- **Phase Coherence (Gamma)**: 0-1, how aligned agent perspectives are. Target: >= 0.98
- **Epistemic Tension (xi)**: 0-1, productive disagreement between agents. Target: <= 0.05
- **Ethical Alignment (eta)**: 0-1, AEGIS ethical compliance. Target: >= 0.90
- **Tension Productivity**: Was disagreement resolved in synthesis? Higher = better.
- **Perspective Coverage**: Which of the 8 perspectives contributed? Shows as colored dots.

---

## Hardware Notes

### This Machine (HP OmniBook 7 Flip 16)
- CPU: Intel Core Ultra 7 256V (Lunar Lake)
- GPU: Intel Arc 140V (8GB) — XPU backend works but llama.cpp uses CPU
- RAM: 16.8 GB physical + 32 GB page file on C: = ~51 GB virtual
- Storage: C: NVMe 512GB, J: USB 4TB (Seagate), K: USB 2TB (WD)
- Python: J:\python.exe (3.10) with PYTHONPATH="J:/Lib/site-packages"
- Page file: C: drive ONLY (Windows cannot create page files on USB drives!)

### Minimum Requirements (Any User)
- 4GB RAM: Q2 GGUF, 1 adapter at a time, text metrics only
- 8GB RAM: Q4 GGUF, auto-routing, basic UI
- 16GB RAM: Full Codette with all features

### SYCL/XPU PATH Fix
Scripts auto-set this, but if you get DLL errors:
```
set PATH=J:\Lib\site-packages\Library\bin;%PATH%
```

---

## Git / Backup

### Repos
- GitHub: https://github.com/Raiff1982/codette-training-lab
- HuggingFace: https://huggingface.co/Raiff1982/codette-training-lab
- Adapters: https://huggingface.co/Raiff1982/codette-lora-adapters
- Datasets: https://huggingface.co/datasets/Raiff1982/codette-training-data

### Push to Both
```
cd J:\codette-training-lab
git add -A && git commit -m "your message"
git push origin master    # GitHub
git push hf master        # HuggingFace
```

### Important: .gitignore
Large files are excluded: `datasets/*.jsonl`, `*.png`, `*.jpg`, `*.gguf`
Datasets live on HuggingFace dataset repo, not in git.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'xxx'` | `J:\python.exe -m pip install xxx` |
| `c10_xpu.dll` not found | Set PATH (see SYCL/XPU section) |
| `total_mem` AttributeError | Use `total_memory` (PyTorch API change) |
| Page file won't create on J:/K: | USB drives can't have page files. Use C: |
| HF push rejected (large files) | Check .gitignore, scrub with filter-branch |
| Training OOM on CPU | Use Pipeline 2 (offload), reduce seq_len |
| Adapter not found | Check `adapters/` folder for .gguf files |
| Voice not working | Install: `pip install sounddevice SpeechRecognition` |

---

## Key Dependencies

```
# Core inference (already installed)
llama-cpp-python          # GGUF model loading
torch                     # For XPU/training only

# Training (cloud or local)
transformers>=4.45.0,<4.48.0
peft>=0.10.0,<0.14.0
trl==0.12.2               # Cloud only (not installed locally)

# Voice (optional)
sounddevice               # Microphone recording
SpeechRecognition         # Google STT API

# Web UI (zero extra deps — uses Python stdlib!)
# No FastAPI, no Flask, no npm, no node — pure Python http.server
```
