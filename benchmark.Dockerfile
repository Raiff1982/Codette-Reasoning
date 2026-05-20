# [Systems Arch Lens] Optimized for Reasoning Isolation
FROM python:3.11-slim

WORKDIR /app

# Install dependencies for reasoning and metrics
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the benchmarking and core logic
COPY benchmarks/ /app/benchmarks/
COPY reasoning_forge/ /app/reasoning_forge/
COPY evaluation/ /app/evaluation/

# Entry point triggers the main suite condition
ENTRYPOINT ["python", "benchmarks/codette_benchmark_suite.py"]