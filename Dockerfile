FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmp3lame0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY telegram-bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram-bot .

RUN mkdir -p downloads && chmod 777 downloads

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]