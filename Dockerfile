FROM python:3.10-slim

# Cài FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Cài Python packages
RUN pip install --no-cache-dir openai-whisper deep-translator pypinyin requests PyGithub

# Pre-download Whisper model base
RUN python -c "import whisper; whisper.load_model('base')"

WORKDIR /app
