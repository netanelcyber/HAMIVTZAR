#!/bin/bash
# Quick Docker Installation Script

echo "🐳 Installing Docker..."

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected: Linux"

    # Ubuntu/Debian
    if command -v apt-get &> /dev/null; then
        echo "[*] Installing Docker (Ubuntu/Debian)..."
        sudo apt-get update
        sudo apt-get install -y docker.io docker-compose-plugin

        # Add user to docker group
        sudo usermod -aG docker $USER
        newgrp docker

        echo "✅ Docker installed!"
        echo "Note: Run 'newgrp docker' or logout/login to use without sudo"

    # CentOS/RHEL
    elif command -v yum &> /dev/null; then
        echo "[*] Installing Docker (CentOS/RHEL)..."
        sudo yum install -y docker docker-compose
        sudo systemctl start docker
        sudo usermod -aG docker $USER
        newgrp docker

        echo "✅ Docker installed!"

    # Arch
    elif command -v pacman &> /dev/null; then
        echo "[*] Installing Docker (Arch)..."
        sudo pacman -S docker docker-compose
        sudo systemctl start docker
        sudo usermod -aG docker $USER
        newgrp docker

        echo "✅ Docker installed!"
    fi

elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected: macOS"
    echo "[*] Installing Docker Desktop (macOS)..."
    echo "1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop"
    echo "2. Install the .dmg file"
    echo "3. Run from Applications folder"

elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "Detected: Windows"
    echo "[*] Installing Docker Desktop (Windows)..."
    echo "1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop"
    echo "2. Run the installer"
    echo "3. Enable WSL2 (Windows Subsystem for Linux)"
    echo "4. Restart your machine"

else
    echo "❓ Unknown OS: $OSTYPE"
    echo "Visit: https://docs.docker.com/get-docker/"
fi

echo ""
echo "✅ Verify installation:"
echo "   docker --version"
echo "   docker ps"
