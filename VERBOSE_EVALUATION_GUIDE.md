# Real-Time Agent Thinking — Verbose Evaluation Guide

## Quick Start

See agents thinking in real-time as they analyze and debate:

```bash
python evaluation/run_evaluation_verbose.py --questions 1
```

## What You'll See

### 1. **Orchestrator Initialization** (40 seconds)
```
INFO:codette_orchestrator  | INFO     | Loading base model (one-time)...
INFO:codette_orchestrator  | INFO     |   GPU layers: 35 (0=CPU only, 35+=full GPU offload)
INFO:codette_orchestrator  | INFO     | ✓ GPU acceleration ENABLED (35 layers offloaded)
INFO:codette_orchestrator  | INFO     | Base model loaded in 8.2s
```

### 2. **Agent Setup**
```
[AGENT SETUP INSPECTION]
  Orchestrator available: True
  Available adapters: ['newton', 'davinci', 'empathy', 'philosophy', 'quantum', 'consciousness', 'multi_perspective', 'systems_architecture']

  Agent LLM modes:
    Newton       ✓ LLM        (orch=True, adapter=newton)
    Quantum      ✓ LLM        (orch=True, adapter=quantum)
    DaVinci      ✓ LLM        (orch=True, adapter=davinci)
    Philosophy   ✓ LLM        (orch=True, adapter=philosophy)
    Empathy      ✓ LLM        (orch=True, adapter=empathy)
    Ethics       ✓ LLM        (orch=True, adapter=philosophy)
```

### 3. **Real-Time Agent Thinking (Round 0)**

As each agent analyzes the concept:

```
[Newton] Analyzing 'What is the speed of light in vacuum?...'
  Adapter: newton
  System prompt: Examining the methodological foundations of this concept through dimen...
  Generated: 1247 chars, 342 tokens
  Response preview: "Speed of light represents a fundamental velocity constant arising from Maxwell's equations...

[Quantum] Analyzing 'What is the speed of light in vacuum?...'
  Adapter: quantum
  System prompt: Probing the natural frequencies of 'What is the speed of light in...
  Generated: 1089 chars, 298 tokens
  Response preview: "Light exists in superposition of possibilities until measurement: it is both wave and partic...

[DaVinci] Analyzing 'What is the speed of light in vacuum?...'
  Adapter: davinci
  System prompt: Examining 'What is the speed of light in vacuum?...' through symmetry analysis...
  Generated: 1345 chars, 378 tokens
  Response preview: "Cross-domain insight: light's speed constant connects electromagnetic theory to relativi...

[Philosophy] Analyzing 'What is the speed of light in vacuum?...'
  Adapter: philosophy
  System prompt: Interrogating the epistemological boundaries of 'What is the speed o...
  Generated: 1203 chars, 334 tokens
  Response preview: "Epistemologically, light speed represents a boundary between measurable constants and th...

[Empathy] Analyzing 'What is the speed of light in vacuum?...'
  Adapter: empathy
  System prompt: Mapping the emotional landscape of 'What is the speed of light in...
  Generated: 891 chars, 245 tokens
  Response preview: "Humans experience light as fundamental to consciousness: vision, warmth, time perception...
```

Each line shows:
- **Agent name** (Newton, Quantum, etc.)
- **Concept being analyzed** (truncated)
- **Adapter being used** (e.g., "newton", "quantum")
- **System prompt preview** (first 100 chars)
- **Output size**: chars generated + tokens consumed
- **Response preview**: first 150 chars of what the agent generated

### 4. **Conflict Detection (Round 0)**
```
Domain-gated activation: detected 'physics' → 3 agents active

[CONFLICTS DETECTED] Round 0: 42 conflicts found
  Top conflicts:
  - Newton vs Quantum: 0.68 (Causality vs Probability)
  - Newton vs DaVinci: 0.45 (Analytical vs Creative)
  - Quantum vs Philosophy: 0.52 (Measurement vs Meaning)
```

### 5. **Debate Rounds (Round 1+)**
```
[R1] Newton vs Quantum
  Challenge: "Where do you agree with Quantum's superposition view? Where is causality essential?"
  Newton's response: 1234 chars
  Quantum's reply: 1089 chars

[R1] Quantum vs Philosophy
  Challenge: "How does the measurement problem relate to epistemology?"
  Quantum's response: 945 chars
  Philosophy's reply: 1123 chars
```

### 6. **Final Synthesis**
```
====================================================================================
[FINAL SYNTHESIS] (2847 characters)

The speed of light represents a fundamental constant that emerges from the intersection
of multiple ways of understanding reality. From Newton's causal-analytical perspective,
it's a boundary condition derived from Maxwell's equations and relativistic principles...

[From Quantum perspective: Light exhibits wave-particle duality...]
[From DaVinci's creative lens: Speed-of-light connects to broader patterns...]
[From Philosophy: Epistemologically grounded in measurement and uncertainty...]
[From Empathy: Light as human experience connects consciousness to physics...]
====================================================================================
```

### 7. **Metadata Summary**
```
[METADATA]
  Conflicts detected: 42
  Gamma (coherence): 0.784
  Debate rounds: 2
  GPU time: 2.3 sec total
```

## Command Options

```bash
# See 1 question with full thinking (default)
python evaluation/run_evaluation_verbose.py

# See 3 questions
python evaluation/run_evaluation_verbose.py --questions 3

# Pipe to file for analysis
python evaluation/run_evaluation_verbose.py --questions 2 > debug.log 2>&1
```

## What Each Log Line Means

| Log Pattern | Meaning |
|------------|---------|
| `[Agent] Analyzing 'X'...` | Agent starting to analyze concept |
| `Adapter: newton` | Which trained adapter is being used |
| `System prompt: ...` | The reasoning framework being provided |
| `Generated: 1247 chars, 342 tokens` | Output size and LLM tokens consumed |
| `Response preview: ...` | First 150 chars of actual reasoning |
| `Domain-gated: detected 'physics' → 3 agents` | Only these agents are active for this domain |
| `[R0] Newton → 1247 chars. Preview: ...` | Round 0 initial analysis excerpt |
| `[R1] Newton vs Quantum` | Debate round showing which agents are engaging |

## Debugging Tips

### If you see "TEMPLATE" instead of LLM output:
```
Response preview: "Tracing the causal chain within 'gravity': every observable..."
```
→ This is the template. Agent didn't get the orchestrator!

### If you see real reasoning:
```
Response preview: "Gravity is fundamentally a curvature of spacetime according to..."
```
→ Agent is using real LLM! ✓

### If GPU isn't being used:
```
Base model loaded in 42s
⚠ CPU mode (GPU disabled)
```
→ GPU isn't loaded. Check n_gpu_layers setting.

### If GPU is working:
```
Base model loaded in 8.2s
✓ GPU acceleration ENABLED (35 layers offloaded)
```
→ GPU is accelerating inference! ✓

## Performance Metrics to Watch

- **Base model load time**: <15s = GPU working, >30s = CPU only
- **Per-agent inference**: <5s = GPU mode, >15s = CPU mode
- **Token generation rate**: >50 tok/s = GPU, <20 tok/s = CPU
- **GPU memory**: Should show VRAM usage in task manager

## Comparing to Templates

To see the difference, create a test script:

```python
# View template-based response
from reasoning_forge.agents.newton_agent import NewtonAgent
agent = NewtonAgent(orchestrator=None)  # No LLM!
template_response = agent.analyze("gravity")

# View LLM-based response
from reasoning_forge.forge_engine import ForgeEngine
forge = ForgeEngine()
llm_response = forge.newton.analyze("gravity")
```

Template output will be generic substitution.
LLM output will be domain-specific reasoning.

---

Ready to see agents thinking! Run it and let me know what you see. 🎯
