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
echo "📥 Pulling latest changes from git (remote: $GIT_REMOTE, branch: $GIT_BRANCH)..."
git pull $GIT_REMOTE $GIT_BRANCH
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to pull from git"
    exit 1
fi
echo "✅ Git pull completed successfully"

# Step 2: Stop and remove containers
echo "🛑 Stopping and removing containers..."
docker-compose down
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to stop containers"
    exit 1
fi
echo "✅ Containers stopped and removed"

# Step 3: Build containers
echo "🔨 Building containers..."
docker-compose build
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to build containers"
    exit 1
fi
echo "✅ Containers built successfully"

# Step 4: Start containers
echo "🚀 Starting containers..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to start containers"
    exit 1
fi
echo "✅ Containers started successfully"

echo ""
echo "✨ Update process completed!"
echo "📊 View logs with: docker-compose logs -f"
echo "🔍 Check status with: docker-compose ps"

