# Codette Model Downloads

All production models and adapters are available on **HuggingFace**: https://huggingface.co/Raiff1982

## Quick Download

### Option 1: Auto-Download (Recommended)
```bash
pip install huggingface-hub

# Download directly
huggingface-cli download Raiff1982/Meta-Llama-3.1-8B-Instruct-Q4 \
  --local-dir models/base/

huggingface-cli download Raiff1982/Llama-3.2-1B-Instruct-Q8 \
  --local-dir models/base/

# Download adapters
huggingface-cli download Raiff1982/Codette-Adapters \
  --local-dir adapters/
```

### Option 2: Manual Download
1. Visit: https://huggingface.co/Raiff1982
2. Select model repository
3. Click "Files and versions"
4. Download `.gguf` files to `models/base/`
5. Download adapters to `adapters/`

### Option 3: Using Git-LFS
```bash
git clone https://huggingface.co/Raiff1982/Meta-Llama-3.1-8B-Instruct-Q4
git lfs pull
```

## Available Models

All models are quantized GGUF format (optimized for llama.cpp and similar):

| Model | Size | Location | Type |
|-------|------|----------|------|
| **Llama 3.1 8B Q4** | 4.6 GB | Raiff1982/Meta-Llama-3.1-8B-Instruct-Q4 | Default (recommended) |
| **Llama 3.1 8B F16** | 3.4 GB | Raiff1982/Meta-Llama-3.1-8B-Instruct-F16 | High quality |
| **Llama 3.2 1B Q8** | 1.3 GB | Raiff1982/Llama-3.2-1B-Instruct-Q8 | Lightweight/CPU |
| **Codette Adapters** | 224 MB | Raiff1982/Codette-Adapters | 8 LORA weights |

## Setup Instructions

### Step 1: Clone Repository
```bash
git clone https://github.com/Raiff1982/Codette-Reasoning.git
cd Codette-Reasoning
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Download Models
```bash
# Quick method using huggingface-cli
huggingface-cli download Raiff1982/Meta-Llama-3.1-8B-Instruct-Q4 \
  --local-dir models/base/

huggingface-cli download Raiff1982/Llama-3.2-1B-Instruct-Q8 \
  --local-dir models/base/

huggingface-cli download Raiff1982/Codette-Adapters \
  --local-dir adapters/
```

### Step 4: Verify Setup
```bash
ls -lh models/base/     # Should show 3 GGUF files
ls adapters/*.gguf      # Should show 8 adapters
```

### Step 5: Start Server
```bash
python inference/codette_server.py
# Visit http://localhost:7860
```

## HuggingFace Profile

**All models hosted at**: https://huggingface.co/Raiff1982

Models include:
- Complete documentation
- Model cards with specifications
- License information
- Version history

## Offline Setup

If you have models downloaded locally:
```bash
# Just copy files to correct location
cp /path/to/models/*.gguf models/base/
cp /path/to/adapters/*.gguf adapters/
```

## Troubleshooting Downloads

### Issue: "Connection timeout"
```bash
# Increase timeout
huggingface-cli download Raiff1982/Meta-Llama-3.1-8B-Instruct-Q4 \
  --local-dir models/base/ \
  --resume-download
```

### Issue: "Disk space full"
Each model needs:
- Llama 3.1 8B Q4: 4.6 GB
- Llama 3.1 8B F16: 3.4 GB
- Llama 3.2 1B: 1.3 GB
- Adapters: ~1 GB
- **Total: ~10 GB minimum**

### Issue: "HuggingFace token required"
```bash
huggingface-cli login
# Paste token from: https://huggingface.co/settings/tokens
```

## Bandwidth & Speed

**Typical download times**:
- Llama 3.1 8B Q4: 5-15 minutes (100 Mbps connection)
- Llama 3.2 1B: 2-5 minutes
- Adapters: 1-2 minutes
- **Total: 8-22 minutes** (first-time setup)

## Attribution

Models:
- **Llama**: Meta AI (open source)
- **GGUF Quantization**: Ollama/ggerganov
- **Adapters**: Jonathan Harrison (Raiff1982)

License: See individual model cards on HuggingFace

---

**Once downloaded**, follow `DEPLOYMENT.md` for production setup.

For questions, visit: https://huggingface.co/Raiff1982
