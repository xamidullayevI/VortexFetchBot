FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmp3lame0 \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY telegram-bot/requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY telegram-bot .

# Create downloads directory
RUN mkdir -p downloads && chmod 777 downloads

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

CMD ["python", "main.py"]