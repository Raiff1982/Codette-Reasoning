FROM nvcr.io/nvidia/tritonserver:26.06-vllm-python-py3

RUN pip install --no-cache-dir 
    llama-cpp-python 
    pydantic 
    numpy

COPY Codette-Reasoning /codette
WORKDIR /codette

RUN pip install --no-cache-dir -r requirements.txt

RUN huggingface-cli download Raiff1982/codette-llama-3.1-8b-gguf 
      --include "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" 
      --local-dir models/base/

RUN huggingface-cli download Raiff1982/codette-lora-adapters 
      --include "behavioral-gguf/*" 
      --local-dir behavioral-lora-f16-gguf/

EXPOSE 7860

CMD ["python", "inference/codette_server.py", "--port", "7860"]
