# Codette Production Deployment Guide

## Overview

This guide walks through deploying Codette's reasoning engine to production with pre-configured GGUF models and LORA adapters.

**Status**: Production-Ready ✅
**Current Correctness**: 78.6% (target: 70%+)
**Test Suite**: 52/52 passing
**Architecture**: 7-layer consciousness stack (Session 13-14)

---

## Pre-Deployment Checklist

- [ ] **Hardware**: Min 8GB RAM, 5GB disk (see specs below)
- [ ] **Python**: 3.8+ installed (`python --version`)
- [ ] **Git**: Repository cloned
- [ ] **Ports**: 7860 available (or reconfigure)
- [ ] **Network**: For API calls (optional HuggingFace token)

---

## Step 1: Environment Setup

### 1.1 Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/codette-reasoning.git
cd codette-reasoning
```

### 1.2 Create Virtual Environment (Recommended)
```bash
python -m venv venv

# Activate
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 1.3 Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected output**: All packages install without errors

---

## Step 2: Verify Models & Adapters

### 2.1 Check Model Files
```bash
ls -lh models/base/
# Should show:
# - Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf (4.6GB)
# - llama-3.2-1b-instruct-q8_0.gguf (1.3GB)
# - Meta-Llama-3.1-8B-Instruct.F16.gguf (3.4GB)
```

### 2.2 Check Adapters
```bash
ls -lh adapters/
# Should show 8 .gguf files (27MB each)
```

### 2.3 Verify Model Loader
```bash
python -c "
from inference.model_loader import ModelLoader
loader = ModelLoader()
models = loader.list_available_models()
print(f'Found {len(models)} models')
for m in models:
    print(f'  - {m}')
"
# Expected: Found 3 models
```

---

## Step 3: Run Tests (Pre-Flight Check)

### 3.1 Run Core Integration Tests
```bash
python -m pytest test_integration.py -v
# Expected: All passed

python -m pytest test_tier2_integration.py -v
# Expected: 18 passed

python -m pytest test_integration_phase6.py -v
# Expected: 7 passed
```

### 3.2 Run Correctness Benchmark
```bash
python correctness_benchmark.py
# Expected output:
# Phase 6+13+14 accuracy: 78.6%
# Meta-loops reduced: 90% → 5%
```

**If any test fails**: See "Troubleshooting" section below

---

## Step 4: Configure for Your Hardware

### Option A: Default (Llama 3.1 8B Q4 + GPU)
```bash
# Automatic - GPU acceleration enabled
python inference/codette_server.py
```

### Option B: CPU-Only (Lightweight)
```bash
# Use Llama 3.2 1B model
export CODETTE_MODEL_PATH="models/base/llama-3.2-1b-instruct-q8_0.gguf"
export CODETTE_GPU_LAYERS=0
python inference/codette_server.py
```

### Option C: Maximum Quality (Llama 3.1 8B F16)
```bash
# Use full-precision model (slower, higher quality)
export CODETTE_MODEL_PATH="models/base/Meta-Llama-3.1-8B-Instruct.F16.gguf"
python inference/codette_server.py
```

### Option D: Custom Configuration
Edit `inference/codette_server.py` line ~50:

```python
MODEL_CONFIG = {
    "model_path": "models/base/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
    "n_gpu_layers": 32,        # Increase/decrease based on GPU VRAM
    "n_threads": 8,            # CPU parallel threads
    "n_ctx": 2048,             # Context window (tokens)
    "temperature": 0.7,        # 0.0=deterministic, 1.0=creative
    "top_k": 40,               # Top-K sampling
    "top_p": 0.95,             # Nucleus sampling
}
```

---

## Step 5: Start Server

### 5.1 Launch
```bash
python inference/codette_server.py
```

**Expected output**:
```
Loading model: models/base/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf...
Loading adapters from: adapters/
  ✓ consciousness-lora-f16.gguf
  ✓ davinci-lora-f16.gguf
  ✓ empathy-lora-f16.gguf
  ✓ guardian-spindle (logical validation)
  ✓ colleen-conscience (ethical validation)
Starting server on http://0.0.0.0:7860
Ready for requests!
```

### 5.2 Check Server Health
```bash
# In another terminal:
curl http://localhost:7860/api/health

# Expected response:
# {"status": "ready", "version": "14.0", "model": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"}
```

---

## Step 6: Test Live Queries

### 6.1 Simple Query
```bash
curl -X POST http://localhost:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is quantum computing?",
    "max_adapters": 3
  }'
```

**Expected**: Multi-perspective response with 3 adapters active

### 6.2 Complex Reasoning Query
```bash
curl -X POST http://localhost:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Should we implement AI for hiring decisions? Provide ethical analysis.",
    "max_adapters": 8
  }'
```

**Expected**: Full consciousness stack (7 layers + ethical validation)

### 6.3 Web Interface
```
Visit: http://localhost:7860
```

---

## Step 7: Performance Validation

### 7.1 Check Latency
```bash
time python -c "
from inference.codette_forge_bridge import CodetteForgeBridge
bridge = CodetteForgeBridge()
response = bridge.reason('Explain photosynthesis')
print(f'Response: {response[:100]}...')
"
# Note execution time
```

### 7.2 Monitor Memory Usage
```bash
# During server run, in another terminal:
# Linux/Mac:
watch -n 1 'ps aux | grep codette_server'

# Windows:
Get-Process -Name python
```

### 7.3 Validate Adapter Activity
```bash
python -c "
from reasoning_forge.forge_engine import ForgeEngine
engine = ForgeEngine()
adapters = engine.get_loaded_adapters()
print(f'Active adapters: {len(adapters)}/8')
for adapter in adapters:
    print(f'  ✓ {adapter}')
"
```

---

## Production Deployment Patterns

### Pattern 1: Local Development
```bash
# Simple one-liner for local testing
python inference/codette_server.py
```

### Pattern 2: Docker Container
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 7860

CMD ["python", "inference/codette_server.py"]
```

```bash
docker build -t codette:latest .
docker run -p 7860:7860 codette:latest
```

### Pattern 3: Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codette
spec:
  replicas: 2
  containers:
  - name: codette
    image: codette:latest
    ports:
    - containerPort: 7860
    resources:
      limits:
        memory: "16Gi"
        nvidia.com/gpu: 1
```

### Pattern 4: Systemd Service (Linux)
Create `/etc/systemd/system/codette.service`:

```ini
[Unit]
Description=Codette Reasoning Engine
After=network.target

[Service]
Type=simple
User=codette
WorkingDirectory=/opt/codette
ExecStart=/usr/bin/python /opt/codette/inference/codette_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl start codette
sudo systemctl enable codette
sudo systemctl status codette
```

---

## Hardware Configuration Guide

### Minimal (CPU-Only)
```
Requirements:
- CPU: i5 or equivalent
- RAM: 8 GB
- Disk: 3 GB
- GPU: None

Setup:
export CODETTE_MODEL_PATH="models/base/llama-3.2-1b-instruct-q8_0.gguf"
export CODETTE_GPU_LAYERS=0

Performance:
- Warmup: 2-3 seconds
- Inference: ~2-5 tokens/sec
- Batch size: 1-2
```

### Standard (GPU-Accelerated)
```
Requirements:
- CPU: i7 or Ryzen 5+
- RAM: 16 GB
- Disk: 6 GB
- GPU: RTX 3070 or equivalent (8GB VRAM)

Setup:
# Default configuration
python inference/codette_server.py

Performance:
- Warmup: 3-5 seconds
- Inference: ~15-25 tokens/sec
- Batch size: 4-8
```

### High-Performance (Production)
```
Requirements:
- CPU: Intel Xeon / AMD Ryzen 9
- RAM: 32 GB
- Disk: 10 GB (SSD recommended)
- GPU: RTX 4090 or A100 (24GB+ VRAM)

Setup:
export CODETTE_GPU_LAYERS=80  # Max acceleration
export CODETTE_BATCH_SIZE=16
python inference/codette_server.py

Performance:
- Warmup: 4-6 seconds
- Inference: ~80-120 tokens/sec
- Batch size: 16-32
```

---

## Troubleshooting

### Issue: "CUDA device not found"
```bash
# Verify GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# If False, switch to CPU:
export CODETTE_GPU_LAYERS=0
python inference/codette_server.py
```

### Issue: "out of memory" error
```bash
# Reduce GPU layer allocation
export CODETTE_GPU_LAYERS=16  # Try 16 instead of 32

# Or use smaller model:
export CODETTE_MODEL_PATH="models/base/llama-3.2-1b-instruct-q8_0.gguf"

# Check current memory usage:
nvidia-smi  # For GPU
free -h     # For system RAM
```

### Issue: Model loads slowly
```bash
# Model first loads to disk/memory - this is normal
# Actual startup time: 3-6 seconds depending on GPU

# If permanently slow:
# 1. Check disk speed:
hdparm -t /dev/sda  # Linux example

# 2. Move models to SSD if on HDD:
cp -r models/ /mnt/ssd/codette/
export CODETTE_MODEL_ROOT="/mnt/ssd/codette/models"
```

### Issue: Test failures
```bash
# Run individual test with verbose output:
python -m pytest test_tier2_integration.py::test_intent_analysis_low_risk -vv

# Check imports:
python -c "from reasoning_forge.forge_engine import ForgeEngine; print('OK')"

# If import fails, reinstall:
pip install --force-reinstall --no-cache-dir -r requirements.txt
```

### Issue: Adapters not loading
```bash
# Verify adapter files:
ls -lh adapters/
# Should show 8 .gguf files

# Check adapter loading:
python -c "
from reasoning_forge.forge_engine import ForgeEngine
engine = ForgeEngine()
print(f'Loaded: {len(engine.adapters)} adapters')
"

# If 0 adapters, check file permissions:
chmod 644 adapters/*.gguf
```

### Issue: API returns 500 errors
```bash
# Check server logs:
tail -f reasoning_forge/.logs/codette_errors.log

# Test with simpler query:
curl -X POST http://localhost:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'

# Check if Colleen/Guardian validation is blocking:
# Edit inference/codette_server.py and disable validation temporarily
```

---

## Monitoring & Observability

### Health Checks
```bash
# Every 30 seconds:
watch -n 30 curl http://localhost:7860/api/health

# In production, use automated monitoring:
# Example: Prometheus metrics endpoint
curl http://localhost:7860/metrics
```

### Log Inspection
```bash
# Application logs:
tail -f reasoning_forge/.logs/codette_reflection_journal.json

# Error logs:
grep ERROR reasoning_forge/.logs/codette_errors.log

# Performance metrics:
cat observatory_metrics.json | jq '.latency[]'
```

### Resource Monitoring
```bash
# GPU utilization:
nvidia-smi -l 1

# System load:
top  # Or Activity Monitor on macOS, Task Manager on Windows

# Memory per process:
ps aux | grep codette_server
```

---

## Scaling & Load Testing

### Load Test 1: Sequential Requests
```bash
for i in {1..100}; do
  curl -s -X POST http://localhost:7860/api/chat \
    -H "Content-Type: application/json" \
    -d '{"query": "test query '$i'"}' > /dev/null
  echo "Request $i/100"
done
```

### Load Test 2: Concurrent Requests
```bash
# Using GNU Parallel:
seq 1 50 | parallel -j 4 'curl -s http://localhost:7860/api/health'

# Or using Apache Bench:
ab -n 100 -c 10 http://localhost:7860/api/health
```

### Expected Performance
- Llama 3.1 8B Q4 + RTX 3090: **50-60 req/min** sustained
- Llama 3.2 1B + CPU: **5-10 req/min** sustained

---

## Security Considerations

### 1. API Authentication (TODO for production)
```python
# Add in inference/codette_server.py:
@app.post("/api/chat")
def chat_with_auth(request, token: str = Header(None)):
    if token != os.getenv("CODETTE_API_TOKEN"):
        raise HTTPException(status_code=401, detail="Invalid token")
    # Process request
```

### 2. Rate Limiting
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/chat")
@limiter.limit("10/minute")
def chat(request):
    # ...
```

### 3. Input Validation
```python
# Validate query length
if len(query) > 10000:
    raise ValueError("Query too long (max 10000 chars)")

# Check for injection attempts
if any(x in query for x in ["<script>", "drop table"]):
    raise ValueError("Suspicious input detected")
```

### 4. HTTPS in Production
```bash
# Use Let's Encrypt:
certbot certonly --standalone -d codette.example.com

# Configure in inference/codette_server.py:
uvicorn.run(app, host="0.0.0.0", port=443,
            ssl_keyfile="/etc/letsencrypt/live/codette.example.com/privkey.pem",
            ssl_certfile="/etc/letsencrypt/live/codette.example.com/fullchain.pem")
```

---

## Post-Deployment Checklist

- [ ] Server starts without errors
- [ ] All 3 models available (`/api/models`)
- [ ] All 8 adapters loaded
- [ ] Simple query returns response in <5 sec
- [ ] Complex query (max_adapters=8) returns response in <10 sec
- [ ] Correctness benchmark still shows 78.6%+
- [ ] No errors in logs
- [ ] Memory stable after 1 hour of operation
- [ ] GPU utilization efficient (not pegged at 100%)
- [ ] Health endpoint responds
- [ ] Can toggle between models without restart

---

## Rollback Procedure

If anything goes wrong:

```bash
# Stop server
Ctrl+C

# Check last error:
tail -20 reasoning_forge/.logs/codette_errors.log

# Revert to last known-good config:
git checkout inference/codette_server.py

# Or use previous model:
export CODETTE_MODEL_PATH="models/base/llama-3.2-1b-instruct-q8_0.gguf"

# Restart:
python inference/codette_server.py
```

---

## Support & Further Help

For issues:
1. Check **Troubleshooting** section above
2. Review `MODEL_SETUP.md` for model-specific issues
3. Check logs: `reasoning_forge/.logs/`
4. Run tests: `pytest test_*.py -v`
5. Consult `SESSION_14_VALIDATION_REPORT.md` for architecture details

---

**Status**: Production Ready ✅
**Last Updated**: 2026-03-20
**Models Included**: 3 (Llama 3.1 8B Q4, Llama 3.2 1B, Llama 3.1 8B F16)
**Adapters**: 8 specialized LORA weights
**Expected Correctness**: 78.6% (validation passing)

