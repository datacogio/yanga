#!/bin/bash
set -e

echo "Starting PulseAudio..."
pulseaudio -D --exit-idle-time=-1

echo "Starting Xvfb on :99..."
Xvfb :99 -screen 0 1920x1080x24 &
sleep 2

echo "Starting x11vnc..."
x11vnc -display :99 -forever -shared -rfbport 5900 -bg

echo "Exporting display..."
export DISPLAY=:99

echo "Initializing Playwright..."
# Ensure browsers are installed (though they should be in Dockerfile)
# python -m playwright install chromium

echo "Starting Agent..."
exec python -m agent.main
