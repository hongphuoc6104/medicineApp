# ============================================
# MedicineApp Python AI Server — GPU Dockerfile
# Base: NVIDIA CUDA 12.4 + Ubuntu 22.04
# ============================================
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install Python 3.10 + system deps
# NOTE: Using Python 3.10, NOT 3.12 — gdown/VietOCR uses pkg_resources.ImpImporter
# which was REMOVED in Python 3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3.10-dev \
    libgl1-mesa-glx libglib2.0-0 libgomp1 wget curl && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    ln -sf /usr/bin/python3.10 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.10
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

WORKDIR /app

# PaddlePaddle environment flags
ENV FLAGS_enable_pir_api=0
ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY core/ ./core/
COPY server/ ./server/

# Models and data are mounted as volumes (too large to copy into image)
# VOLUME /app/models
# VOLUME /app/data

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
