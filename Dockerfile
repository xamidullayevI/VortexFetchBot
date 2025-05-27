FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install build dependencies first
COPY telegram-bot/requirements.txt .
RUN pip install --no-cache-dir wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY telegram-bot .

# Create downloads directory
RUN mkdir -p downloads && chmod 777 downloads

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]