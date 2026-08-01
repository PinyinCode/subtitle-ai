FROM python:3.10-slim

# Cài FFmpeg + Git + các tool cần thiết
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    ca-certificates \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 👈 TẮT CẢNH BÁO BẰNG CÁCH SET ENV TRONG IMAGE
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1
ENV TF_CPP_MIN_LOG_LEVEL=3
ENV HF_HUB_ENABLE_HF_TRANSFER=0
ENV PYTHONWARNINGS=ignore

# 👈 TẠO TOKEN DUMMY ĐỂ TRÁNH CẢNH BÁO
ENV HF_TOKEN=dummy_token_for_build

# ✅ Cài Faster-Whisper
RUN pip install --no-cache-dir \
    faster-whisper \
    deep-translator \
    pypinyin \
    requests \
    PyGithub

# ✅ Pre-download Faster-Whisper model (dùng dummy token)
RUN python -c "import os; os.environ['HF_TOKEN']='dummy'; from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"

# Thư mục làm việc
WORKDIR /app

# Verify cài đặt
RUN python -c "from faster_whisper import WhisperModel; print('Faster-Whisper OK')" && \
    ffmpeg -version | head -1 && \
    git --version
