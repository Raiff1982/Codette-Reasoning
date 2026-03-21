#!/usr/bin/env python3
"""
Baseline Benchmark — Measure orchestrator latencies WITHOUT Phase 6/7

Test 30 queries (10 per complexity) to establish baseline latencies.
Then Phase 7 improvements can be compared against these numbers.
"""

import json
import time
import urllib.request
import urllib.error

# Test queries
QUERIES = {
    "SIMPLE": [
        "What is the speed of light?",
        "Define entropy",
        "Who is Albert Einstein?",
        "What year was the Internet invented?",
        "How high is Mount Everest?",
        "What is the chemical formula for water?",
        "Define photosynthesis",
        "Who wrote Romeo and Juliet?",
        "What is the capital of France?",
        "How fast can a cheetah run?",
    ],
    "MEDIUM": [
        "How does quantum mechanics relate to consciousness?",
        "What are the implications of artificial intelligence?",
        "Compare classical and quantum computing",
        "How do neural networks learn?",
        "What is the relationship between energy and mass?",
        "How does evolution explain biodiversity?",
        "What are the main differences between mitochondria and chloroplasts?",
        "How does feedback regulate biological systems?",
        "What is the connection between sleep and memory consolidation?",
        "How do economic systems balance growth and sustainability?",
    ],
    "COMPLEX": [
        "Can machines be truly conscious?",
        "What is the nature of free will and how does it relate to determinism?",
        "Is artificial intelligence the future of humanity?",
        "How should AI be ethically governed?",
        "What makes something morally right or wrong?",
        "Can subjective experience be measured objectively?",
        "How does quantum mechanics challenge our understanding of reality?",
        "What is the relationship between language and thought?",
        "How should society balance individual freedom with collective good?",
        "Is human consciousness unique, or could machines achieve it?",
    ],
}

SERVER_URL = "http://localhost:7860"

def benchmark_queries():
    """Run baseline benchmark against all 30 queries."""
    
    print("\n" + "="*70)
    print("BASELINE BENCHMARK — Orchestrator WITHOUT Phase 6/7")
    print("="*70)
    
    results = {"SIMPLE": [], "MEDIUM": [], "COMPLEX": []}
    
    # Check server (allow up to 180s for model loading on first startup)
    print("\nChecking server status (waiting up to 180s for model load)...")
    start_wait = time.time()
    timeout_per_check = 10  # Each check waits 10s
    max_total_wait = 180    # Total 3 minutes

    response = None
    while time.time() - start_wait < max_total_wait:
        try:
            response = urllib.request.urlopen(f"{SERVER_URL}/api/status", timeout=timeout_per_check)
            status = json.loads(response.read().decode('utf-8'))
            print(f"  Server state: {status.get('state')}")
            if status.get('state') != 'ready':
                print(f"  Waiting for server to reach 'ready' state...")
                time.sleep(2)
                continue
            break  # Server is ready!
        except Exception as e:
            elapsed = time.time() - start_wait
            print(f"  [{elapsed:.0f}s] Waiting for server... ({e})")
            time.sleep(2)
            continue

    if response is None:
        print(f"  ERROR: Server never became available after {max_total_wait}s")
        return results

    # Run queries
    total_start = time.time()
    completed = 0
    
    for complexity in ["SIMPLE", "MEDIUM", "COMPLEX"]:
        print(f"\n[{complexity}] Testing {len(QUERIES[complexity])} queries:")
        
        for i, query in enumerate(QUERIES[complexity], 1):
            try:
                start_time = time.time()
                
                data = json.dumps({
                    "query": query,
                    "max_adapters": 2
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    f"{SERVER_URL}/api/chat",
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                
                response = urllib.request.urlopen(req, timeout=60)
                result = json.loads(response.read().decode('utf-8'))
                
                elapsed = time.time() - start_time
                token_count = result.get('tokens', 0)
                
                # Store result
                results[complexity].append({
                    "query": query[:50],
                    "latency_ms": elapsed * 1000,
                    "tokens": token_count,
                    "success": True
                })
                
                print(f"  [{i:2d}/10] {elapsed:6.1f}ms | {query[:40]}...")
                completed += 1
                
            except urllib.error.HTTPError as e:
                print(f"  [{i:2d}/10] HTTP {e.code} | {query[:40]}...")
                results[complexity].append({
                    "query": query[:50],
                    "error": f"HTTP {e.code}",
                    "success": False
                })
            except Exception as e:
                print(f"  [{i:2d}/10] ERROR: {str(e)[:30]} | {query[:40]}...")
                results[complexity].append({
                    "query": query[:50],
                    "error": str(e)[:50],
                    "success": False
                })
    
    # Summary
    total_elapsed = time.time() - total_start
    
    print(f"\n" + "="*70)
    print(f"RESULTS: {completed}/30 queries completed")
    print(f"Total time: {total_elapsed:.1f}s\n")
    
    for complexity in ["SIMPLE", "MEDIUM", "COMPLEX"]:
        successful = [r for r in results[complexity] if r.get('success')]
        if successful:
            latencies = [r['latency_ms'] for r in successful]
            tokens = [r.get('tokens', 0) for r in successful]
            
            print(f"{complexity}:")
            print(f"  Success rate: {len(successful)}/{len(results[complexity])}")
            print(f"  Latency (avg/min/max): {sum(latencies)/len(latencies):.0f}ms / {min(latencies):.0f}ms / {max(latencies):.0f}ms")
            print(f"  Tokens (avg): {sum(tokens)/len(tokens):.0f}")
        else:
            print(f"{complexity}: ALL FAILED")
    
    # Save results
    with open('baseline_benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to baseline_benchmark_results.json")
    
    return results

if __name__ == "__main__":
    benchmark_queries()
