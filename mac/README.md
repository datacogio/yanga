# Mac M4 Pro Deployment Guide

This directory contains configuration files optimized for deploying the Sensory Agent on an Apple Silicon Mac (M1/M2/M3/M4).

## Why use this configuration?
The M4 Pro has powerful Neural Engine and GPU capabilities.
-   **Native Ollama**: Running Ollama as a native Mac app allows it to fully utilize Apple's Metal API for hardware acceleration, providing much faster token generation than running it inside Docker.
-   **Dockerized Agent**: The rest of the system (Python agent, Redis, Postgres) runs in Docker for isolation and easy management.

## Prerequisites
-   **Docker Desktop for Mac**: Must be installed and running.
-   **Ollama**: The setup script can install it, or you can download it from [ollama.com](https://ollama.com).

## Deployment Steps

1.  **Clone the Repository** (if you haven't already)
    ```bash
    git clone <your-repo-url>
    cd sensory_agent
    ```

2.  **Run the Setup Script**
    ```bash
    chmod +x mac/setup.sh
    ./mac/setup.sh
    ```
    This script will:
    -   Check for Homebrew, Docker, and Ollama.
    -   Install missing dependencies (if Homebrew is available).
    -   Ensure Ollama is running.
    -   Start the agent containers.

3.  **Access the Agent**
    -   Open Finder -> Go -> Connect to Server.
    -   Enter `vnc://localhost:5901`.
    -   Click "Connect".

## Troubleshooting

-   **Ollama Connection**: If the agent cannot connect to Ollama, ensure Ollama is running in your menu bar and that you didn't block connections (though `host.docker.internal` should bypass local firewalls usually).
-   **Performance**: If Ollama feels slow, check if other heavy GPU apps are running.
