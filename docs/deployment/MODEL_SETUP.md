# Codette Model Setup & Configuration

## Model Downloads

**All models are hosted on HuggingFace**: https://huggingface.co/Raiff1982

See `MODEL_DOWNLOAD.md` for download instructions and alternatives.

### Model Options

| Model | Location | Size | Type | Recommended Use |
|-------|----------|------|------|-----------------|
| **Llama 3.1 8B (Q4)** | `models/base/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | 4.6 GB | Quantized 4-bit | **Production (Default)** |
| **Llama 3.2 1B (Q8)** | `models/base/llama-3.2-1b-instruct-q8_0.gguf` | 1.3 GB | Quantized 8-bit | CPU/Edge devices |
| **Llama 3.1 8B (F16)** | `models/base/Meta-Llama-3.1-8B-Instruct.F16.gguf` | 3.4 GB | Full precision | High quality (slower) |

## Quick Start

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Load Default Model (Llama 3.1 8B Q4)
```bash
python inference/codette_server.py
# Automatically loads: models/base/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
# Server starts on http://localhost:7860
```

### Step 3: Verify Models Loaded
```bash
# Check model availability
python -c "
from inference.model_loader import ModelLoader
loader = ModelLoader()
print(f'Available models: {loader.list_available_models()}')
print(f'Default model: {loader.get_default_model()}')
"
# Output: 3 models detected, Meta-Llama-3.1-8B selected
```

## Configuration

### Default Model Selection

Edit `inference/model_loader.py` or set environment variable:

```bash
# Use Llama 3.2 1B (lightweight)
export CODETTE_MODEL_PATH="models/base/llama-3.2-1b-instruct-q8_0.gguf"
python inference/codette_server.py

# Use Llama 3.1 F16 (high quality)
export CODETTE_MODEL_PATH="models/base/Meta-Llama-3.1-8B-Instruct.F16.gguf"
python inference/codette_server.py
```

### Model Parameters

Configure in `inference/codette_server.py`:

```python
MODEL_CONFIG = {
    "model_path": "models/base/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
    "n_gpu_layers": 32,        # GPU acceleration (0 = CPU only)
    "n_ctx": 2048,              # Context window
    "n_threads": 8,             # CPU threads
    "temperature": 0.7,         # Creativity (0.0-1.0)
    "top_k": 40,                # Top-K sampling
    "top_p": 0.95,              # Nucleus sampling
}
```

## Hardware Requirements

### CPU-Only (Llama 3.2 1B)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Storage**: 2 GB for model + 1 GB for dependencies
- **Performance**: ~2-5 tokens/sec

### GPU-Accelerated (Llama 3.1 8B Q4)
- **GPU Memory**: 6 GB minimum (RTX 3070), 8 GB+ recommended
- **System RAM**: 16 GB recommended
- **Storage**: 5 GB for model + 1 GB dependencies
- **Performance**:
  - RTX 3060: ~12-15 tokens/sec
  - RTX 3090: ~40-60 tokens/sec
  - RTX 4090: ~80-100 tokens/sec

### Optimal (Llama 3.1 8B F16 + High-End GPU)
- **GPU Memory**: 24 GB+ (RTX 4090, A100)
- **System RAM**: 32 GB
- **Storage**: 8 GB
- **Performance**: ~100+ tokens/sec (production grade)

## Adapter Integration

Codette uses behavioral GGUF adapters for multi-perspective reasoning:

```
behavioral-lora-f16-gguf/
├── consciousness-lora-f16.gguf       (Meta-cognitive insights)
├── davinci-lora-f16.gguf              (Creative reasoning)
├── empathy-lora-f16.gguf              (Emotional intelligence)
├── newton-lora-f16.gguf               (Logical analysis)
├── philosophy-lora-f16.gguf           (Philosophical depth)
├── quantum-lora-f16.gguf              (Probabilistic thinking)
├── multi_perspective-lora-f16.gguf    (Synthesis)
└── systems_architecture-lora-f16.gguf (Complex reasoning)
```

### Adapter Auto-Loading

Adapters automatically load when inference engine detects them:

```python
# In reasoning_forge/forge_engine.py
self.adapters_path = "behavioral-lora-f16-gguf/"
self.loaded_adapters = self._load_adapters()  # Auto-loads all .gguf files
```

### Manual Adapter Selection

```python
from reasoning_forge.forge_engine import ForgeEngine

engine = ForgeEngine()
engine.set_active_adapter("davinci")  # Use Da Vinci perspective only
response = engine.reason(query)
```

## Troubleshooting

### Issue: "CUDA device not found"
```bash
# Check if GPU is available
python -c "import torch; print(torch.cuda.is_available())"

# If False, use CPU mode:
export CODETTE_GPU=0
python inference/codette_server.py
```

### Issue: "out of memory" errors
```bash
# Reduce GPU layers allocation
export CODETTE_GPU_LAYERS=16  # (default 32)
python inference/codette_server.py

# Or use smaller model
export CODETTE_MODEL_PATH="models/base/llama-3.2-1b-instruct-q8_0.gguf"
python inference/codette_server.py
```

### Issue: Model loads but server is slow
```bash
# Increase CPU threads
export CODETTE_THREADS=16
python inference/codette_server.py

# Or switch to GPU
export CODETTE_GPU_LAYERS=32
```

### Issue: Adapters not loading
```bash
# Verify adapter files exist
ls -lh behavioral-lora-f16-gguf/

# Check adapter loading logs
python -c "
from reasoning_forge.forge_engine import ForgeEngine
engine = ForgeEngine()
print(engine.get_loaded_adapters())
"
```

## Model Attribution & Licensing

### Base Models
- **Llama 3.1 8B**: Meta AI, under Llama 2 Community License
- **Llama 3.2 1B**: Meta AI, under Llama 2 Community License
- **GGUF Quantization**: Ollama/ggerganov (BSD License)

### Adapters
- All adapters trained with PEFT (Parameter-Efficient Fine-Tuning)
- Licensed under Sovereign Innovation License (Jonathan Harrison)
- See `LICENSE` for full details

## Performance Benchmarks

### Inference Speed (Tokens per Second)

| Model | CPU | RTX 3060 | RTX 3090 | RTX 4090 |
|-------|-----|----------|----------|----------|
| Llama 3.2 1B | 5 | 20 | 60 | 150 |
| Llama 3.1 8B Q4 | 2.5 | 12 | 45 | 90 |
| Llama 3.1 8B F16 | 1.5 | 8 | 30 | 70 |

### Memory Usage

| Model | Load Time | Memory Usage | Inference Batch |
|-------|-----------|------|---|
| Llama 3.2 1B | 2-3s | 1.5 GB | 2-4 tokens |
| Llama 3.1 8B Q4 | 3-5s | 4.8 GB | 8-16 tokens |
| Llama 3.1 8B F16 | 4-6s | 9.2 GB | 4-8 tokens |

## Next Steps

1. **Run correctness benchmark**:
   ```bash
   python correctness_benchmark.py
   ```
   Expected: 78.6% accuracy with adapters engaged

2. **Test with custom query**:
   ```bash
   curl -X POST http://localhost:7860/api/chat \
     -H "Content-Type: application/json" \
     -d '{"query": "Explain quantum computing", "max_adapters": 3}'
   ```

3. **Fine-tune adapters** (optional):
   ```bash
   python reasoning_forge/train_adapters.py --dataset custom_data.jsonl
   ```

4. **Deploy to production**:
   - Use Llama 3.1 8B Q4 (best balance)
   - Configure GPU layers based on your hardware
   - Set up model monitoring
   - Implement rate limiting

## Production Checklist

- [ ] Run all 52 unit tests (`pytest test_*.py -v`)
- [ ] Do baseline benchmark (`python correctness_benchmark.py`)
- [ ] Test with 100 sample queries
- [ ] Verify adapter loading (all 8 should load)
- [ ] Monitor memory during warmup
- [ ] Check inference latency profile
- [ ] Validate ethical layers (Colleen, Guardian)
- [ ] Document any custom configurations

## Verification

After completing model setup, verify that Codette's reasoning and audit layers are working correctly:

**1. Run the cocoon smoke test** — this is the single most important verification step:

```bash
make cocoon-smoke
```

Expected output: `Cocoon smoke: 27/27 passed`. This confirms that the v3 schema, integrity validator, echo/collapse detector, subsystem contracts, and quarantine routing are all functioning. If any check fails, the model or runtime is misconfigured.

**2. Inspect the first live cocoon** — start the server, send one query, then check what got written:

```bash
make dev                   # starts server at localhost:7860, writes to dev_cocoons/
# In another terminal:
curl -X POST http://localhost:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain entropy", "max_adapters": 2}'
make inspect-latest        # human-readable view of the cocoon just written
```

A healthy cocoon shows `cocoon_integrity: complete` (or `partial` on the lightweight path), `echo_risk: low`, and a non-zero `cocoon_integrity_score`.

**3. Check overall system health:**

```bash
make health
```

Look for `HEALTH: OK` and `v3_missing_fallback_count: 0`. A non-zero fallback count means a response was written without full v3 provenance — investigate before deploying.

For a full explanation of what each cocoon field means and how the integrity score is computed, see:
- [docs/cocoons_quickstart.md](../cocoons_quickstart.md)
- [docs/cocoon_pipeline.md](../cocoon_pipeline.md)

---

**Last Updated**: 2026-05-02
**Status**: Production Ready ✅
**Models Included**: 3 (Llama 3.1 8B Q4, Llama 3.2 1B, Llama 3.1 8B F16)
**Adapters**: 8 specialized LORA weights (924 MB total)

For questions, see `DEPLOYMENT.md` and `README.md`
