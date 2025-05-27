FROM python:3.11-slim

# Install ffmpeg and build dependencies
RUN apt-get update \
    && apt-get install -y ffmpeg build-essential python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create downloads directory
RUN mkdir -p downloads && chmod 777 downloads

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Start the bot
CMD ["python", "main.py"]