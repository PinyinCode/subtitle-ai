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

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir yt-dlp

RUN pip install --no-cache-dir \
    faster-whisper \
    deep-translator \
    pypinyin \
    requests \
    PyGithub \
    gdown \
    youtube-search-python

RUN python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"

WORKDIR /app

COPY scripts/ ./scripts/
COPY data/ ./data/
COPY output/ ./output/

RUN mkdir -p data/audio output

# 👈 VERIFY ĐƠN GIẢN (BỎ YOUTUBE_SEARCH)
RUN python -c "from faster_whisper import WhisperModel; print('✅ Faster-Whisper OK')" && \
    ffmpeg -version | head -1 && \
    yt-dlp --version

CMD ["python", "scripts/generate_subtitles.py", "--latest"]
