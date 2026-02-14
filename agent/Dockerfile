FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    xvfb \
    x11vnc \
    ffmpeg \
    pulseaudio \
    procps \
    # Playwright dependencies
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY agent /app/agent
COPY startup.sh /app/startup.sh

# Make startup script executable
RUN chmod +x /app/startup.sh

# Environment variables
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

CMD ["/app/startup.sh"]
