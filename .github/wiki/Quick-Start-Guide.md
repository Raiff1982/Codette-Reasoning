# Quick Start Guide

Get Codette running in 5 minutes.

---

## Prerequisites

- Python 3.10+
- Ollama installed (https://ollama.ai)
- 4.9GB disk space (for Q4_K_M model)
- 8GB RAM minimum (16GB recommended)

---

## 1. Download the Model (2 minutes)

```bash
# Pull the quantized Codette model
ollama pull raiff1982/codette:q4_k_m

# Or the full-precision version (larger, slower)
ollama pull raiff1982/codette:f16
```

---

## 2. Start Ollama Server

```bash
# Start Ollama (runs on localhost:11434)
ollama serve

# In another terminal, verify it's running
curl http://localhost:11434/api/tags
```

---

## 3. Start Codette Server

```bash
cd J:\codette-clean

# Install Python dependencies
pip install -r requirements.txt

# Start the server (runs on localhost:8000)
python inference/codette_server.py
```

---

## 4. Use Codette

### Via Claude Code (Easiest)

```
User message:
"Use multi-perspective reasoning to analyze [problem]"

Codette will activate the framework automatically.
```

### Via REST API

```bash
# Test the health endpoint
curl http://localhost:8000/api/health

# Get reasoning
curl -X POST http://localhost:8000/api/reason \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Should I pivot my startup?",
    "perspectives": ["newton", "intuition", "philosophical"]
  }'

# Analyze ethical decision
curl -X POST http://localhost:8000/api/value-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "at": 1.0,
      "label": "Building community garden",
      "impact": 3.0,
      "context_weights": {"community": 1.0}
    }
  }'
```

### Via Python

```python
from codette import CodetteClient

client = CodetteClient(url="http://localhost:8000")

# Multi-perspective reasoning
result = client.reason(
    prompt="How should we handle this ethical dilemma?",
    perspectives=["newton", "philosophical", "intuition"]
)
print(result["analysis"])
print(f"Epistemic Tension: {result['epistemic_tension']}")

# Ethical analysis
ethics = client.value_analysis(
    event={
        "label": "Community garden project",
        "impact": 3.0,
        "context_weights": {"community": 1.0}
    }
)
print(f"Ethical Alignment: {ethics['aggregate_modulation']:.1%}")
print(f"Strongly Aligned: {ethics['strongly_aligned']}")
```

---

## 5. Try These Examples

### Example 1: Multi-Perspective Analysis

**Prompt**:
```
Analyze this problem from multiple perspectives:
"Should we use AI for hiring decisions?"

Use Newton (logical), Philosophical (ethical),
and Bias Mitigation (fairness) perspectives.
```

**Expected Output**:
- Newton: Efficiency gains vs. bias risks
- Philosophical: Human dignity implications
- Bias Mitigation: Legal compliance concerns
- Epistemic Tension: ~0.7 (high—conflicting values)
- Attractors: "Human oversight essential"

### Example 2: Ethical Analysis

**Request**:
```json
{
  "event": {
    "label": "Extract natural resources without sustainability plan",
    "impact": -5.0,
    "context_weights": {"extraction": 1.0}
  }
}
```

**Expected Output**:
- Aggregate Ethical Score: ~38% (low)
- Strongly Violated: Custodial Stewardship, Seven Generations
- Best Tradition: Islamic (61%), Western rights (52%)
- Insight: Cross-cultural opposition to unsustainable extraction

### Example 3: Web Research

**Prompt**:
```
Research the latest advances in quantum computing and
provide analysis from a futurist perspective.
(with allow_web_search=true)
```

**Features**:
- Searches DuckDuckGo (privacy-respecting)
- Cites sources
- Stores findings in cocoons for future use
- Integrates with multi-perspective analysis

---

## Configuration

Edit `inference/codette_server.py` for settings:

```python
# Web research (default: disabled)
allow_web_search = False

# Diagnostic mode (explicit keywords only)
diagnostic_keywords = [
    "system status", "health check", "diagnostic report"
]

# Session timeout
session_timeout_minutes = 30

# Cocoon pruning
max_cocoons_per_domain = 100
identity_confidence_decay_rate = 0.95
```

---

## Troubleshooting

### Model Fails to Load

```bash
# Check Ollama is running
ollama list

# Re-pull if needed
ollama rm raiff1982/codette:q4_k_m
ollama pull raiff1982/codette:q4_k_m
```

### Server Won't Start

```bash
# Check port 8000 isn't in use
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill conflicting process and try again
```

### Out of Memory

```bash
# Use the f16 model (slower but less memory)
ollama pull raiff1982/codette:f16

# Or allocate more RAM to Ollama
# (see Ollama settings/preferences)
```

### Web Research Fails

```bash
# Check DuckDuckGo is reachable
curl https://api.duckduckgo.com/

# Enable allow_web_search in config
allow_web_search = True
```

---

## Next Steps

1. **Read Architecture Overview** - Understand how components fit together
2. **Explore API Reference** - See all available endpoints
3. **Check Hallucination Prevention** - Understand safety mechanisms
4. **Review AEGIS Frameworks** - Learn the 25 ethical traditions
5. **Dive into RC+ξ** - Study the mathematical foundation

---

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions, share ideas
- **Documentation**: See the full wiki for detailed guides
- **Email**: research@raiff1982.com

---

**Ready?** Start with: `ollama pull raiff1982/codette:q4_k_m`
