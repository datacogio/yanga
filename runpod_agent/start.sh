#!/bin/bash
set -e

echo "Starting Monolithic Zoom Agent..."

# 0. Start SSH
echo "Starting SSH..."
mkdir -p /var/run/sshd
/usr/sbin/sshd

# 1. Start Xvfb (Virtual Framebuffer)
echo "Starting Xvfb..."
# Cleanup potential locks from previous crashes to prevent startup failure
rm -f /tmp/.X99-lock
rm -f /tmp/.X11-unix/X99

Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

# Wait for Xvfb to be ready (up to 20s)
echo "Waiting for Xvfb..."
for i in {1..20}; do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "Xvfb is ready."
        break
    fi
    echo "Waiting for Xvfb ($i/20)..."
    sleep 1
done

# 1.5 Start x11vnc (Non-fatal)
echo "Starting x11vnc..."
# Use -bg to background. If it fails, log it but don't crash the container.
x11vnc -display :99 -forever -nopw -shared -rfbport 5900 -bg -o /var/log/x11vnc.log || echo "WARNING: x11vnc failed to start."

# 1.6 Start noVNC/websockify
echo "Starting noVNC..."
/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen 6080 &

# 2. Start PulseAudio (Fake Audio)
echo "Starting PulseAudio..."
pulseaudio -D --exit-idle-time=-1

# --- AUDIO ROUTING ARCHITECTURE ---
# Goal: 
# 1. Zoom Output (Speaker) -> Agent Input (Mic)
# 2. Agent Output (Speaker) -> Zoom Input (Mic)

# A. Create SpeakerSink (Zoom Output)
# Chrome will play audio here (Default Sink). 
# Agent will listen to SpeakerSink.monitor.
pactl load-module module-null-sink sink_name=SpeakerSink sink_properties=device.description=Speaker_Sink
pactl set-default-sink SpeakerSink

# B. Create MicSink (Zoom Input)
# Agent will play 'mpg123' here.
# Chrome will listen to MicSink.monitor (Default Source).
pactl load-module module-null-sink sink_name=MicSink sink_properties=device.description=Microphone_Sink
pactl load-module module-virtual-source source_name=MicSource master=MicSink.monitor source_properties=device.description=Microphone_Source

# Set Default Source to SPEAKER MONITOR (so Agent listens to Meeting)
# NOTE: Zoom might default to this too, causing feedback. 
# We rely on Zoom picking "Microphone_Source" intelligently or manual selection.
pactl set-default-source SpeakerSink.monitor

# Unmute everything just in case
pactl set-sink-mute SpeakerSink 0
pactl set-sink-mute MicSink 0
pactl set-source-mute MicSource 0

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
MODEL_NAME="llama3.2-vision"
if ! ollama list | grep -q "$MODEL_NAME"; then
    echo "Pulling model: $MODEL_NAME..."
    ollama pull $MODEL_NAME
else
    echo "Model $MODEL_NAME already exists."
fi

# 4. Start FastAPI Server
echo "Starting FastAPI Server..."
# Assuming src module is in current directory or PYTHONPATH
# Pipe output to both stdout (for RunPod Logs) and a file (for SSH tailing)
uvicorn src.api:app --host 0.0.0.0 --port 8000 2>&1 | tee /workspace/agent.log
