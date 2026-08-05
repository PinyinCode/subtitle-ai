FROM python:3.11-slim

# Cài FFmpeg + Git + các tool cần thiết
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    ca-certificates \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cài yt-dlp
RUN pip install --no-cache-dir yt-dlp

# ✅ Cài Faster-Whisper + các thư viện khác (KHÔNG CẦN requirements.txt)
RUN pip install --no-cache-dir \
    faster-whisper \
    deep-translator \
    pypinyin \
    requests \
    PyGithub \
    gdown

# ✅ Pre-download Faster-Whisper model medium
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"

# Thư mục làm việc
WORKDIR /app

# Copy scripts
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY output/ ./output/

# Tạo thư mục cần thiết
RUN mkdir -p data/audio output

# Verify cài đặt
RUN python -c "from faster_whisper import WhisperModel; print('✅ Faster-Whisper OK')" && \
    ffmpeg -version | head -1 && \
    git --version && \
    yt-dlp --version

CMD ["python", "scripts/generate_subtitles.py", "--latest"]
