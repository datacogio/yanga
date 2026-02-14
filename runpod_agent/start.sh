#!/bin/bash
set -e

echo "Starting Monolithic Zoom Agent..."

# 1. Start Xvfb (Virtual Framebuffer)
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

# 1.5 Start x11vnc
echo "Starting x11vnc..."
x11vnc -display :99 -forever -nopw -shared -rfbport 5900 -bg

# 2. Start PulseAudio (Fake Audio)
echo "Starting PulseAudio..."
pulseaudio -D --exit-idle-time=-1
# Create a virtual sink for Chrome to output audio potentially
pactl load-module module-null-sink sink_name=VirtualSink sink_properties=device.description=VirtualSink

# 3. Start Ollama Serve
echo "Starting Ollama..."
mkdir -p /workspace/ollama_models
ollama serve > /dev/null 2>&1 &

# Wait for Ollama to be ready
echo "Waiting for Ollama to initialize..."
until curl -s http://localhost:11434/api/tags >/dev/null; do
    sleep 2
    echo "Using retry..."
done
echo "Ollama is UP."

# Auto-Model Pull (Mistral by default)
MODEL_NAME="mistral"
if ! ollama list | grep -q "$MODEL_NAME"; then
    echo "Pulling model: $MODEL_NAME..."
    ollama pull $MODEL_NAME
else
    echo "Model $MODEL_NAME already exists."
fi

# 4. Start FastAPI Server
echo "Starting FastAPI Server..."
# Assuming src module is in current directory or PYTHONPATH
uvicorn src.api:app --host 0.0.0.0 --port 8000
