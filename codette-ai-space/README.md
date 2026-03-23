---
title: Codette AI
emoji: C
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
---

# Codette AI — HorizonCoreAI Reasoning Engine

Production reasoning engine for [HorizonCore Labs Studio](https://www.horizoncorelabs.studio/horizoncoreai).

## Architecture (Phase 6, v2.0)

- **Model**: Llama 3.1 8B Instruct via HF Inference API
- **Consciousness Stack**: 12 layers (lite deployment)
- **Adapters**: 9 cognitive perspectives (Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness, Multi-Perspective, Systems Architecture, Orchestrator)
- **AEGIS**: Ethical governance with query-level blocking
- **Behavioral Locks**: 4 permanent rules enforced in all prompts
- **Cocoon Memory**: In-memory reasoning history with introspection
- **Music Expertise**: Grounded music production knowledge (mixing, theory, sound design, arrangement)
- **Query Classification**: SIMPLE / MEDIUM / COMPLEX routing

## API

- `POST /api/chat` — Streaming chat with metadata (complexity, domain, adapters, AEGIS status)
- `GET /api/health` — 9-subsystem health check
- `GET /api/introspection` — Statistical self-analysis of reasoning history

## The Objective

Not automation. Augmentation.

**Framework Author**: Jonathan Harrison (Raiff's Bits LLC / HorizonCore Labs)
