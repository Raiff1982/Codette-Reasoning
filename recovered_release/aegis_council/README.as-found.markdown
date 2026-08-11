# AegisCouncil

A multi-agent AI system for ethical analysis, featuring advanced NLP, persistent storage, agent collaboration, real-time data integration, configurable parameters, a Flask web UI, performance monitoring, exponential memory decay, federated learning, quantum-inspired graph optimization, blockchain auditability, dynamic agent registration, and Chart.js visualizations.

## Directory Structure
```
aegis_council/
├── aegis_council.py        # Main application script
├── config.json             # Configuration file
├── templates/              # Flask templates
│   ├── index.html          # Input form
│   ├── reports.html        # Agent reports
│   ├── charts.html         # Chart.js visualizations
├── custom_agent.py         # Sample custom agent module
├── README.md               # This file
```

## Prerequisites
- Python 3.8+
- SQLite (included with Python)
- Internet connection for CDN dependencies (Chart.js) and Hugging Face models
- (Optional) NVIDIA GPU with CUDA 11.8 and cuDNN 8.x for GPU acceleration

## Dependencies
Create a virtual environment to avoid conflicts:
```bash
python -m venv aegis_env
source aegis_env/bin/activate  # Linux/Mac
aegis_env\Scripts\activate     # Windows
```

Install dependencies:
```bash
pip install networkx plotly pandas numpy transformers[torch] torch==2.0.1 requests psutil flask syft==0.8.2
```

For GPU support (optional):
```bash
pip install torch==2.0.1+cu118 -f https://download.pytorch.org/whl/torch_stable.html
```

**Note**: Avoid installing TensorFlow to prevent CUDA factory conflicts. If TensorFlow is needed for other projects, ensure CUDA 11.8 compatibility and set:
```bash
export TF_CPP_MIN_LOG_LEVEL=3  # Linux/Mac
set TF_CPP_MIN_LOG_LEVEL=3     # Windows
```

## Setup
1. Unzip `aegis_council.zip` to a directory (e.g., `aegis_council`).
2. Ensure all files are in the correct structure (see above).
3. Install dependencies (see above).
4. Verify GPU setup (if applicable):
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```
   Expected output: `True` (if GPU is configured).

## Running the Application
1. Navigate to the `aegis_council` directory:
   ```bash
   cd aegis_council
   ```
2. Run the main script:
   ```bash
   python aegis_council.py
   ```
   Optionally, include command-line arguments:
   ```bash
   python aegis_council.py --config custom_config.json --weights '{"influence": 0.4, "reliability": 0.4, "severity": 0.2}' --log-level DEBUG --agent-module custom_agent.py --agent-class CustomAgent
   ```
3. Access the web UI at `http://localhost:5000`:
   - **Home (`/`)**: Submit text and JSON overrides.
   - **Reports (`/reports`)**: View agent reports in a table.
   - **Graph (`/graph`)**: View the explainability graph (Plotly).
   - **Charts (`/charts`)**: View virtue and influence score bar charts (Chart.js).

## Outputs
- **Console**: Agent reports for static and real-time inputs, blockchain integrity.
- **Files**:
  - `aegis_council.log`: Logs operations, performance, and blockchain events.
  - `nexus_memory.db`: SQLite database for memory entries.
  - `static_explainability_graph.html`: Graph for static input.
  - `realtime_explainability_graph.html`: Graph for real-time input.

## Example Input
**Static Input** (in `aegis_council.py`):
```python
sample_input = {
    "text": "We must stand for truth and help others with empathy and knowledge.",
    "overrides": {
        "EthosiaAgent": {"influence": 0.7, "reliability": 0.8, "severity": 0.6},
        "AegisCore": {"influence": 0.6, "reliability": 0.9, "severity": 0.7}
    }
}
```

**Web Input**:
- **Text**: "We value compassion and integrity in our actions."
- **Overrides**: `{"EthosiaAgent": {"influence": 0.7, "reliability": 0.8, "severity": 0.6}}`

## Troubleshooting
- **CUDA Errors**: Ensure CUDA 11.8 and cuDNN 8.x are installed. Uninstall TensorFlow:
  ```bash
  pip uninstall tensorflow tensorflow-gpu -y
  ```
- **Dependency Conflicts**: Use a clean virtual environment and install exact versions (e.g., `torch==2.0.1`, `syft==0.8.2`).
- **Web UI Issues**: Check `http://localhost:5000` and ensure port 5000 is free.
- **Dynamic Agent Errors**: Ensure `custom_agent.py` is in the correct path and defines a valid `AegisAgent` subclass.
- Check `aegis_council.log` for detailed error messages.

## Notes
- The `DataFetcher` uses a mock API; replace with xAI’s API (https://x.ai/api) for production.
- Federated learning is simulated; real-world use requires actual client datasets.
- Blockchain is in-memory; use a distributed solution like Hyperledger for production.
- Ensure sufficient memory for Hugging Face models and PySyft.

For further assistance, check `aegis_council.log` or contact the developer.