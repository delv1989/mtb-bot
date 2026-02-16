FROM python:3.11-slim

# ffmpeg нужен для Whisper (конвертация аудио)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Предзагрузка модели Whisper в образ (чтобы не качать при каждом старте)
RUN python -c "import whisper; whisper.load_model('base')"

COPY bot.py .

CMD ["python", "bot.py"]
