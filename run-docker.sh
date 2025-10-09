#!/bin/bash
# Simple script to run YouTube Study Buddy in Docker
# No docker-compose needed!

set -e

# Configuration
IMAGE_NAME="youtube-study-buddy"
CONTAINER_NAME="youtube-study-buddy"
PORT="8501"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Create a .env file with:"
    echo "CLAUDE_API_KEY=your_api_key_here"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Stop and remove existing container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping existing container..."
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
fi

# Check if image exists
if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
    echo "Image not found. Building..."
    docker build -t ${IMAGE_NAME} .
fi

# Run the container
echo "Starting YouTube Study Buddy with Tor..."
docker run -d \
  --name ${CONTAINER_NAME} \
  -p ${PORT}:8501 \
  --env-file .env \
  -v "$(pwd)/notes:/app/notes" \
  ${IMAGE_NAME}

# Wait a moment for startup
echo "Waiting for container to start..."
sleep 5

# Show logs
echo ""
echo "=========================================="
echo "Container Logs:"
echo "=========================================="
docker logs ${CONTAINER_NAME} 2>&1 | tail -20

# Check if it's running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo ""
    echo "=========================================="
    echo "✅ YouTube Study Buddy is running!"
    echo "=========================================="
    echo ""
    echo "🌐 Access at: http://localhost:${PORT}"
    echo ""
    echo "📋 Useful commands:"
    echo "  View logs:    docker logs -f ${CONTAINER_NAME}"
    echo "  Stop:         docker stop ${CONTAINER_NAME}"
    echo "  Restart:      docker restart ${CONTAINER_NAME}"
    echo "  Remove:       docker rm -f ${CONTAINER_NAME}"
    echo ""
else
    echo ""
    echo "❌ Container failed to start. Check logs above."
    exit 1
fi
