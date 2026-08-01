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

# ✅ Cài Faster-Whisper (thay vì openai-whisper)
RUN pip install --no-cache-dir \
    faster-whisper \
    deep-translator \
    pypinyin \
    requests \
    PyGithub

# ✅ Pre-download Faster-Whisper model medium (chất lượng cao, nhanh hơn)
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"

# Thư mục làm việc
WORKDIR /app

# Verify cài đặt
RUN python -c "from faster_whisper import WhisperModel; print('Faster-Whisper OK')" && \
    ffmpeg -version | head -1 && \
    git --version
