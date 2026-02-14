#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Sensory Agent Mac M4 Setup ===${NC}"

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew not found. It is recommended for installing tools on Mac.${NC}"
    echo "Please install Homebrew from https://brew.sh/ or install Docker/Ollama manually."
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed."
    if command -v brew &> /dev/null; then
         echo "Installing Docker via Homebrew..."
         brew install --cask docker
         echo -e "${YELLOW}Please start Docker Desktop from your Applications folder and wait for it to initialize.${NC}"
         read -p "Press Enter when Docker is running..."
    else
         echo "Please install Docker Desktop for Mac manually: https://www.docker.com/products/docker-desktop/"
         exit 1
    fi
else
    echo -e "${GREEN}✓ Docker is installed${NC}"
fi

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "Ollama is not installed."
    if command -v brew &> /dev/null; then
         echo "Installing Ollama via Homebrew..."
         brew install --cask ollama
    else
         echo "Please install Ollama manually: https://ollama.com/download/mac"
         exit 1
    fi
else
    echo -e "${GREEN}✓ Ollama is installed${NC}"
fi

# Ensure Ollama is running
if ! pgrep -x "Ollama" > /dev/null && ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    open -a Ollama
    echo "Waiting for Ollama to initialize..."
    sleep 5
else
    echo -e "${GREEN}✓ Ollama is running${NC}"
fi

# Pull basic model if strictly necessary, but user might already have models
# echo "Pulling default model..."
# ollama pull deepseek-r1:8b

# Build and Run Docker Containers
echo -e "${BLUE}Building and Starting Agent Containers...${NC}"
# Use the Mac-specific compose file
docker compose -f mac/docker-compose.yml up --build -d

echo -e "${GREEN}=== Setup Complete ===${NC}"
echo "1. Connect to VNC: Open Finder -> Go -> Connect to Server -> vnc://localhost:5901"
echo "2. Logs: docker compose -f mac/docker-compose.yml logs -f"
echo "3. Monitor Ollama: Check the Ollama icon in your menu bar."
