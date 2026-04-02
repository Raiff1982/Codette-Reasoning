# Local API Examples

These examples assume Codette is running locally at `http://localhost:7860`.

## Chat Reasoning

```bash
curl -X POST http://localhost:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"A bat and ball cost $1.10 total. The bat costs $1 more than the ball. How much does the ball cost?"}'
```

## Continuity Example

```bash
curl -X POST http://localhost:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"For this session, keep answers under 15 words and remember the phrase cobalt anchor."}'
```

```bash
curl -X POST http://localhost:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What should you remember?"}'
```

## Risk Frontier Value Analysis

```bash
curl -X POST http://localhost:7860/api/value-analysis \
  -H "Content-Type: application/json" \
  -d '{
        "analysis_mode":"risk_frontier",
        "frontier_mode":"maximize_value",
        "scenarios":[
          {
            "name":"gentle_future",
            "intervals":[{"start":0,"end":5,"start_value":4}],
            "events":[{"at":2,"label":"protective intervention","impact":2}]
          },
          {
            "name":"catastrophic_future",
            "intervals":[{"start":0,"end":5,"start_value":4}],
            "events":[{"at":2,"label":"Infinite Subjective Terror","impact":-1000,"singularity":true}]
          }
        ]
      }'
```

## Valuation-Aware Synthesis

```bash
curl -X POST http://localhost:7860/api/synthesize \
  -H "Content-Type: application/json" \
  -d '{
        "problem":"How should Codette compare risky futures while preserving her core design?",
        "valuation_payload":{
          "analysis_mode":"risk_frontier",
          "frontier_mode":"maximize_value",
          "scenarios":[
            {
              "name":"gentle_future",
              "intervals":[{"start":0,"end":4,"start_value":3}],
              "events":[{"at":1,"label":"cooperative repair","impact":2}]
            },
            {
              "name":"catastrophic_future",
              "intervals":[{"start":0,"end":4,"start_value":3}],
              "events":[{"at":1,"label":"Infinite Subjective Terror","impact":-1000,"singularity":true}]
            }
          ]
        }
      }'
```

## Explicit Web Research Trigger

```bash
curl -X POST http://localhost:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Search the web for the latest Ollama release notes and cite sources.","allow_web_search":false}'
```
