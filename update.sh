#!/bin/bash

# Script to pull from git and rebuild Docker containers for Sip-Bridge
# Git Repository: http://10.0.0.129:3000/charles/Sip-Bridge.git
# Usage: ./update.sh

set -e  # Exit on any error

# Git configuration
GIT_REMOTE="gitea"
GIT_BRANCH="master"
GIT_REPO_URL="http://10.0.0.129:3000/charles/Sip-Bridge.git"

echo "🔄 Starting update process for Sip-Bridge..."
echo "📦 Repository: $GIT_REPO_URL"

# Step 1: Pull from git
echo "📥 Pulling latest changes from git..."

# Check if remote exists, if not add it
if ! git remote get-url $GIT_REMOTE &>/dev/null; then
    echo "🔧 Remote '$GIT_REMOTE' not found, adding it..."
    if git remote add $GIT_REMOTE $GIT_REPO_URL 2>/dev/null; then
        echo "✅ Remote added successfully"
        git pull $GIT_REMOTE $GIT_BRANCH || {
            echo "❌ Error: Failed to pull from git"
            exit 1
        }
    else
        echo "⚠️  Warning: Failed to add remote, trying with existing remotes..."
        # Try with origin if it exists, otherwise just pull
        if git remote get-url origin &>/dev/null; then
            echo "📥 Using 'origin' remote instead..."
            git pull origin $GIT_BRANCH || {
                echo "❌ Error: Failed to pull from git"
                exit 1
            }
        else
            echo "📥 Using default git pull..."
            git pull || {
                echo "❌ Error: Failed to pull from git"
                exit 1
            }
        fi
    fi
else
    echo "✅ Remote '$GIT_REMOTE' found, pulling..."
    git pull $GIT_REMOTE $GIT_BRANCH || {
        echo "❌ Error: Failed to pull from git"
        exit 1
    }
fi
echo "✅ Git pull completed successfully"

# Check and install Docker if needed
check_and_install_docker() {
    if ! command -v docker &> /dev/null; then
        echo "🐳 Docker not found, installing..."
        if command -v apt-get &> /dev/null; then
            apt-get update || true
            apt-get install -y docker.io || {
                echo "❌ Error: Failed to install Docker"
                exit 1
            }
        elif command -v yum &> /dev/null; then
            yum install -y docker || {
                echo "❌ Error: Failed to install Docker"
                exit 1
            }
        elif command -v dnf &> /dev/null; then
            dnf install -y docker || {
                echo "❌ Error: Failed to install Docker"
                exit 1
            }
        else
            echo "❌ Error: Could not detect package manager. Please install Docker manually."
            exit 1
        fi
        systemctl enable docker || true
        systemctl start docker || {
            echo "⚠️  Warning: Could not start Docker service (may need to run as root or user in docker group)"
        }
        echo "✅ Docker installed successfully"
    else
        echo "✅ Docker is already installed"
    fi
}

# Check and install docker-compose if needed
check_and_install_docker_compose() {
    # Check for docker-compose (standalone) or docker compose (plugin)
    if command -v docker-compose &> /dev/null; then
        echo "✅ docker-compose is already installed"
        DOCKER_COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        echo "✅ docker compose plugin is already installed"
        DOCKER_COMPOSE_CMD="docker compose"
    else
        echo "🐳 docker-compose not found, installing..."
        if command -v apt-get &> /dev/null; then
            apt-get update || true
            apt-get install -y docker-compose || {
                echo "⚠️  Package manager install failed, trying direct download..."
                curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose || {
                    echo "❌ Error: Failed to install docker-compose"
                    exit 1
                }
                chmod +x /usr/local/bin/docker-compose
            }
        elif command -v yum &> /dev/null; then
            yum install -y docker-compose || {
                echo "⚠️  Package manager install failed, trying direct download..."
                curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose || {
                    echo "❌ Error: Failed to install docker-compose"
                    exit 1
                }
                chmod +x /usr/local/bin/docker-compose
            }
        elif command -v dnf &> /dev/null; then
            dnf install -y docker-compose || {
                echo "⚠️  Package manager install failed, trying direct download..."
                curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose || {
                    echo "❌ Error: Failed to install docker-compose"
                    exit 1
                }
                chmod +x /usr/local/bin/docker-compose
            }
        else
            # Fallback: install docker-compose standalone
            curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose || {
                echo "❌ Error: Failed to download docker-compose"
                exit 1
            }
            chmod +x /usr/local/bin/docker-compose
        fi
        # Verify installation
        if command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker-compose"
            echo "✅ docker-compose installed successfully"
        elif docker compose version &> /dev/null 2>&1; then
            DOCKER_COMPOSE_CMD="docker compose"
            echo "✅ docker compose plugin installed successfully"
        else
            echo "❌ Error: Failed to install docker-compose"
            exit 1
        fi
    fi
}

# Install Docker and docker-compose if needed
check_and_install_docker
check_and_install_docker_compose

# Step 2: Stop and remove containers
echo "🛑 Stopping and removing containers..."
$DOCKER_COMPOSE_CMD down
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to stop containers"
    exit 1
fi
echo "✅ Containers stopped and removed"

# Step 3: Build containers
echo "🔨 Building containers..."
$DOCKER_COMPOSE_CMD build
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to build containers"
    exit 1
fi
echo "✅ Containers built successfully"

# Step 4: Start containers
echo "🚀 Starting containers..."
$DOCKER_COMPOSE_CMD up -d
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to start containers"
    exit 1
fi
echo "✅ Containers started successfully"

echo ""
echo "✨ Update process completed!"
echo "📊 View logs with: $DOCKER_COMPOSE_CMD logs -f"
echo "🔍 Check status with: $DOCKER_COMPOSE_CMD ps"

