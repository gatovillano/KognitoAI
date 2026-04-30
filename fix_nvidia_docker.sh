#!/bin/bash
# Script to fix NVIDIA GPU access in Docker
# Error: could not select device driver "nvidia" with capabilities: [[gpu]]

echo "=== Fixing NVIDIA Docker GPU Access ==="

# Step 1: Add the package repositories
echo "Step 1: Adding NVIDIA package repositories..."
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)   # e.g., ubuntu24.04
echo "Distribution: $distribution"
# Use a known supported distribution for the repository (ubuntu22.04) if the current one is not supported
repo_distribution="ubuntu22.04"
echo "Using repository for: $repo_distribution"

# Add NVIDIA's GPG key
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -

# Add the repository
curl -s -L https://nvidia.github.io/nvidia-docker/$repo_distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Step 2: Update and install the toolkit
echo "Step 2: Updating packages and installing nvidia-container-toolkit..."
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Step 3: Restart Docker
echo "Step 3: Restarting Docker..."
sudo systemctl restart docker

# Step 4: Verify
echo "Step 4: Verifying installation..."
sudo docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

echo "=== Installation complete ==="
echo "If you see GPU information above, the fix was successful."
echo "You can now try running your docker-compose again."