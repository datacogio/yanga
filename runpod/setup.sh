#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Sensory Agent RunPod Setup ===${NC}"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo -e "${GREEN}✓ Docker is installed${NC}"
fi

# Install and Start Ollama (on Host)
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo -e "${GREEN}✓ Ollama is installed${NC}"
fi

# Start Ollama service in background if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama server..."
    ollama serve > /var/log/ollama.log 2>&1 &
    sleep 5 # Wait for it to start
else
    echo -e "${GREEN}✓ Ollama is running${NC}"
fi

# Convert line endings just in case (useful when editing on Windows)
if command -v dos2unix &> /dev/null; then
    find . -type f -name "*.sh" -exec dos2unix {} +
fi

# Build and Run Docker Containers
echo -e "${BLUE}Building and Starting Agent Containers...${NC}"
# Use the RunPod-specific compose file
docker compose -f runpod/docker-compose.yml up --build -d

echo -e "${GREEN}=== Setup Complete ===${NC}"
echo "1. Connect to VNC at port 6080 to see the agent."
echo "2. Logs: docker compose -f runpod/docker-compose.yml logs -f"
echo "3. Monitor Ollama: tail -f /var/log/ollama.log"
