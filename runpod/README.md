# RunPod Deployment Guide

This directory contains configuration files optimized for deploying the Sensory Agent on RunPod.

## Why use this configuration?
Running AI models (Ollama) inside Docker on virtualized GPU instances can be tricky due to driver compatibility and "Docker-in-Docker" issues.
This setup uses a **Hybrid Approach**:
1.  **Ollama** runs directly on the RunPod host (native performance, easy GPU access).
2.  **Agent & Infrastructure** run in Docker containers (clean environment, easy networking).

## Deployment Steps

1.  **Create a RunPod Pod**
    - Select a GPU instance (e.g., RTX 3090, RTX 4090, or A100).
    - Template: Use the **RunPod PyTorch** template (or any Ubuntu-based template with CUDA).
    - Make sure to expose ports **6080** (VNC web), **5900** (VNC tcp), and **11434** (Ollama, if you want external access).

2.  **Access the Pod**
    - Connect via SSH or use the Web Terminal.

3.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd sensory_agent
    ```

4.  **Run the Setup Script**
    This script installs Ollama, Docker (if missing), and starts the agent.
    ```bash
    chmod +x runpod/setup.sh
    ./runpod/setup.sh
    ```

5.  **Access the Agent**
    - The setup script starts the agent containers.
    - Open your browser and go to `http://<YOUR_POD_IP>:6080/vnc.html` to see the agent's desktop environment.
    - Click "Connect" (no password by default).

## Troubleshooting

-   **Ollama Models**: The agent may try to pull models on first run. You can manually pull them on the host:
    ```bash
    ollama pull deepseek-r1:8b
    ```
-   **Logs**: Check agent logs:
    ```bash
    docker compose -f runpod/docker-compose.yml logs -f agent-core
    ```
