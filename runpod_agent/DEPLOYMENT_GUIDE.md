# RunPod Deployment Guide for Monolithic Agent

## 1. Prerequisites
- Docker installed and running locally.
- A Docker Registry account (Docker Hub, GitHub Container Registry, etc.).
- A RunPod account with credits.

## 2. Build and Push Docker Image

**Note:** RunPod requires the image to be publicly accessible or configured with private registry credentials.

### Step 2.1: Login to Registry
Replace `yanga4` with your Docker Hub username.
```bash
docker login
```

### Step 2.2: Build the Image
Navigate to the `sensory_agent/runpod_agent` directory.
**Important:** You must build for `linux/amd64` because RunPod uses Intel/AMD CPUs.
```bash
cd sensory_agent/runpod_agent
docker build --platform linux/amd64 -t yanga4/zoom-agent:latest .
```

### Step 2.3: Push the Image
```bash
docker push yanga4/zoom-agent:latest
```

## 3. Configure RunPod GPU Pod

1.  **Go to RunPod Console** -> **Pods** -> **Deploy**.
2.  **Select GPU:** Choose a GPU (e.g., RTX 3090, RTX 4090, or A4000).
3.  **Select Template:** Click "Deploy" then "Customize Deployment" (or "Edit Template").
4.  **Container Image:** Enter your image: `yanga4/zoom-agent:latest`.
5.  **Container Disk:** Set to **20GB** or more (Docker layers + OS).
6.  **Volume Disk:** Set to **20GB** or more (Important for Ollama models).
7.  **Volume Mount Path:** `/workspace` (Default).
8.  **Expose Ports:**
    - `8000` (HTTP API)
9.  **Environment Variables:**
    - Key: `OLLAMA_HOST` | Value: `localhost:11434`
10. **Start Pod.**

## 4. Verify Deployment across Internet

Once the Pod is "Running", click "Connect" -> "HTTP Service (Port 8000)".
This will give you a public URL like: `https://your-pod-id-8000.proxy.runpod.net`.

### Health Check
```bash
curl https://your-pod-id-8000.proxy.runpod.net/health
```
Response: `{"status": "healthy"}`

### Check Ollama Status
```bash
curl https://your-pod-id-8000.proxy.runpod.net/ollama/check
```

## 5. Usage

### Join Meeting
```bash
curl -X POST https://your-pod-id-8000.proxy.runpod.net/join \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://zoom.us/j/123456789",
    "name": "AI Agent"
  }'
```

### Leave Meeting
```bash
curl -X POST https://your-pod-id-8000.proxy.runpod.net/leave
```

## 6. Debugging

If the agent isn't working:
1.  **Check Logs:** Click "Logs" in RunPod console.
2.  **SSH Code:** You can SSH into the pod to debug manually.
    ```bash
    ssh root@your-pod-ip -p 22
    # Check if processes are running
    ps aux | grep chrome
    ps aux | grep ollama
    ```
