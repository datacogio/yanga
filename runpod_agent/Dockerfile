# Base image with CUDA support for Ollama
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"
ENV OLLAMA_HOST=localhost:11434
ENV OLLAMA_MODELS=/workspace/ollama_models

# Set working directory to /workspace (RunPod's default persistent volume)
# Configure APT retries and timeouts
RUN echo 'Acquire::Retries "10";' > /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::ftp::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries

RUN for i in 1 2 3; do apt-get update && break || sleep 5; done && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    zstd \
    && rm -rf /var/lib/apt/lists/*

RUN for i in 1 2 3; do apt-get update && break || sleep 5; done && \
    apt-get install -y --no-install-recommends \
    python3.11 \
    python3-pip \
    git \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN for i in 1 2 3; do apt-get update && break || sleep 5; done && \
    apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    python3-numpy \
    pulseaudio \
    socat \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN for i in 1 2 3; do apt-get update && break || sleep 5; done && \
    apt-get install -y --no-install-recommends \
    libnss3 \
    libgconf-2-4 \
    libxi6 \
    libxcursor1 \
    libxss1 \
    libxcomposite1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libx11-xcb1 \
    libxrandr2 \
    libgtk-3-0 \
    libgbm1 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome Stable
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb --no-install-recommends && \
    rm google-chrome-stable_current_amd64.deb && \
    rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Python dependencies
# We'll copy requirements.txt first to leverage Docker cache
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
# Note: In development/RunPod, we might mount /workspace, so this is a fallback
COPY src/ ./src/
COPY start.sh .

# Ensure start script is executable
RUN chmod +x start.sh

# Expose ports
# 8000: FastAPI
# 11434: Ollama (optional, providing local access)
EXPOSE 8000 11434 5900 6080

# Define the entrypoint
ENTRYPOINT ["./start.sh"]
