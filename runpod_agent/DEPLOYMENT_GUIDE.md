# RunPod Deployment Guide for Monolithic Agent

## 1. Prerequisites
- Docker installed and running locally.
- A Docker Registry account (Docker Hub, GitHub Container Registry, etc.).
- A RunPod account with credits.

## 2. Build and Push Docker Image (Automated via GitHub Actions)
 
 Instead of building locally (which can be slow or fail on Apple Silicon), we use **GitHub Actions** to automatically build and push the image.
 
 ### Step 2.1: Configure GitHub Secrets
 1. Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
 2. Click **New repository secret**.
 3. Add the following secrets:
    - `DOCKER_USERNAME`: `yanga4`
    - `DOCKER_PASSWORD`: Your Docker Hub Access Token (or password).
 
 ### Step 2.2: Trigger the Build
 Simply push your code to the `main` branch.
 ```bash
 git add .
 git commit -m "Update agent"
 git push origin main
 ```
 
 ### Step 2.3: Verify Build
 1. Go to the **Actions** tab in your GitHub repository.
 2. You should see a workflow named "Build and Push RunPod Agent" running.
 3. Once green, the image `yanga4/zoom-agent:latest` will be available on Docker Hub.

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
