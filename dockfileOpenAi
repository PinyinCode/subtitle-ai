FROM python:3.10-slim

# Cài FFmpeg + Git + các tool cần thiết
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài Python packages
RUN pip install --no-cache-dir \
    openai-whisper \
    deep-translator \
    pypinyin \
    requests \
    PyGithub

# Pre-download Whisper model base
RUN python -c "import whisper; whisper.load_model('base')"

# Thư mục làm việc
WORKDIR /app

# Verify cài đặt
RUN python -c "import whisper; print('Whisper OK')" && \
    ffmpeg -version | head -1 && \
    git --version
