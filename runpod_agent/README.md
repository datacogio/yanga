# RunPod Native Zoom Agent (Monolithic)

This directory contains the code to deploy a Headless Zoom Agent on RunPod. It runs as a single monolithic Docker container containing:
- **Ollama:** For local LLM inference (with GPU support).
- **Selenium (Chrome):** For headless browser automation to join Zoom.
- **PulseAudio:** For audio handling (Virtual Sink).
- **FastAPI:** To control the agent via HTTP.

## deployment on RunPod

### 1. Build & Push Image
Since RunPod needs to pull the image, you must build it and push to a registry (Docker Hub, GHCR, etc.).

```bash
# Login to your registry
docker login

# Build
docker build -t yourusername/zoom-agent:latest .

# Push
docker push yourusername/zoom-agent:latest
```

### 2. Configure RunPod GPU Pod
1.  **Template:** Select `Deploy` on a GPU Pod (e.g., RTX 3090, RTX A4000).
2.  **Image:** Enter your image name: `yourusername/zoom-agent:latest`.
3.  **Container Disk:** Allow at least **20GB** (Ollama models are large).
4.  **Volume Disk:** Recommended **20GB** for `/workspace` caching.
5.  **Expose Ports:**
    - `8000` (TCP) -> For the API.
    - `11434` (Optional) -> For direct Ollama access.

### 3. Environment Variables
Add these env vars in RunPod configuration:
- `OLLAMA_HOST`: `localhost:11434` (Default)

### 4. Advanced Settings
- **Docker Command:** Leave empty (it uses the `ENTRYPOINT` from Dockerfile).
- **Volume Mount:** `/workspace` (Standard).

## Usage

Once running, you can interact with the agent via the exposed HTTP Endpoint (RunPod will give you a public URL for port 8000).

### Join a Meeting
```bash
curl -X POST https://your-runpod-id-8000.proxy.runpod.net/join \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://zoom.us/j/123456789",
    "name": "AI Assistant"
  }'
```

### Leave Meeting
```bash
curl -X POST https://your-runpod-id-8000.proxy.runpod.net/leave
```

### Check Status
```bash
curl https://your-runpod-id-8000.proxy.runpod.net/status
```

### Audio Debug
To check if PulseAudio is running:
```bash
curl https://your-runpod-id-8000.proxy.runpod.net/audio/status
```

## Local Testing (Requires NVIDIA GPU)
```bash
docker run --gpus all -p 8000:8000 -p 11434:11434 yourusername/zoom-agent:latest
```
