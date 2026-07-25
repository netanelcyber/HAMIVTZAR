#!/bin/bash
# Docker + Docker Compose Installation - Works on Older Systems

set -e

echo "🐳 Installing Docker (compatible with older systems)..."
echo

# Step 1: Install Docker
echo "[1/3] Installing Docker..."
sudo apt-get update
sudo apt-get install -y docker.io

# Verify
docker --version

echo "✅ Docker installed!"
echo

# Step 2: Install Docker Compose (multiple methods)
echo "[2/3] Installing Docker Compose..."

# Method 1: Try pip (works on all versions)
if command -v pip3 &> /dev/null; then
    echo "[*] Installing via pip3 (easiest)..."
    pip3 install docker-compose
    echo "✅ Docker Compose installed via pip3"
elif command -v pip &> /dev/null; then
    echo "[*] Installing via pip..."
    pip install docker-compose
    echo "✅ Docker Compose installed via pip"
else
    # Method 2: Download binary directly
    echo "[*] Downloading Docker Compose binary..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed via binary"
fi

# Verify
docker-compose --version

echo

# Step 3: Add user to docker group
echo "[3/3] Setting up permissions..."
sudo usermod -aG docker $USER

echo "✅ Docker setup complete!"
echo
echo "⚠️  IMPORTANT: Run this to apply group changes:"
echo "   newgrp docker"
echo "   # or logout/login"
echo
echo "Verify installation:"
echo "   docker --version"
echo "   docker-compose --version"
echo "   docker ps"
