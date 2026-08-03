FROM nvcr.io/nvidia/tritonserver:26.06-vllm-python-py3

RUN pip install --no-cache-dir \
    llama-cpp-python \
    pydantic \
    numpy

WORKDIR /codette

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY inference/ ./inference/
COPY reasoning_forge/ ./reasoning_forge/
COPY signal_processing/ ./signal_processing/

EXPOSE 7860

CMD ["python", "inference/codette_server.py", "--port", "7860"]
