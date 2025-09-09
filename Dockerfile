FROM python:3.12-slim

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential cmake && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Model volume and environment
RUN mkdir -p /models
VOLUME /models
ENV MODEL_PATH=/models/model.gguf

WORKDIR /workspace

CMD ["bash"]
