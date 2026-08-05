FROM python:3.11-slim

# Cài system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    ca-certificates \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# CÀI TẤT CẢ PACKAGES
RUN pip install --no-cache-dir \
    yt-dlp \
    faster-whisper \
    deep-translator \
    pypinyin \
    requests \
    PyGithub \
    gdown \
    youtube-search-python \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib

# VERIFY TẤT CẢ PACKAGES
RUN python -c "import faster_whisper; import deep_translator; import pypinyin; import youtube_search; print('✅ All packages installed successfully')"

# Download Whisper model
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

WORKDIR /app

# Copy scripts
COPY scripts/ ./scripts/

# Tạo thư mục cần thiết
RUN mkdir -p data/audio output

# 👈 SỬA LỖI: Bỏ 2>/dev/null || true
# Copy data và output (nếu có)
COPY data/ ./data/ 
COPY output/ ./output/

# VERIFY LẦN CUỐI
RUN python -c "from youtube_search import YoutubeSearch; print('✅ YoutubeSearch ready')" && \
    python -c "from faster_whisper import WhisperModel; print('✅ Faster-Whisper ready')"

ENTRYPOINT ["python", "scripts/generate_subtitles.py"]
CMD ["--latest"]
