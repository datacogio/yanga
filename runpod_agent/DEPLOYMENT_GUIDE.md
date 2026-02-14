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

## 3. Deploy on RunPod (Step-by-Step)
 
 Once your GitHub Action is **Green** (Success), follow these steps:
 
 1.  **Login to RunPod:** Go to [runpod.io](https://www.runpod.io/) and log in.
 2.  **Navigate to Pods:** Click on **Pods** in the left sidebar, then click the **Deploy** button.
 3.  **Choose GPU:**
     -   Select **Secure Cloud** (Recommended) or Community Cloud.
     -   Choose a GPU. An **RTX 3090** or **RTX 4090** is good for starting.
     -   Click the **Deploy** button on your chosen GPU card.
 4.  **Configure Template:**
     -   In the "Customize Deployment" window, look for "Container Image".
     -   **Image Name:** Enter `yanga4/zoom-agent:latest`
     -   **Container Disk:** Set to `20 GB` (This holds your code & dependencies).
     -   **Volume Disk:** Set to `20 GB` (This holds the Ollama models).
     -   **Volume Mount Path:** `/workspace` (Leave as default).
     -   **Container Registry Credentials (Optional):**
         -   If your Docker Hub repo is **Private**, expanded "Container Registry Credentials".
         -   Select "Docker Hub" and enter your Username (`yanga4`) and Access Token (Password).
         -   If it is **Public**, you can skip this.
 5.  **Expose Ports:**
     -   In the **"Expose HTTP Ports"** field: `8000`
     -   **(Optional Debugging):** Add `5900` if you need to see the browser via VNC.
     -   **Security Note:** Do NOT expose `11434` unless you want the entire internet to query your Ollama model. The Agent talks to it internally via `localhost`, so you don't need to expose it.
 6.  **Environment Variables:**
     -   Click "Add Variable".
     -   **Key:** `OLLAMA_HOST`
     -   **Value:** `localhost:11434`
 7.  **Start Deployment:**
     -   Click **Set Overrides**.
     -   Click **Deploy**.
 
 ### Accessing the Agent
 1.  Wait for the Pod to show **"Running"**.
 2.  Click the **Connect** button.
 3.  Click **HTTP Service [Port 8000]**.
 4.  This opens your agent's API URL (e.g., `https://your-pod-id-8000.proxy.runpod.net`).

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
