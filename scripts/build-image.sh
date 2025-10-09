#!/bin/bash
# Build and tag YouTube Study Buddy Docker image

set -e

# Change to project root directory
cd "$(dirname "$0")/.."

IMAGE_NAME="fluidnotions/youtube-study-buddy"
VERSION="${1:-latest}"

echo "=========================================="
echo "YouTube Study Buddy - Image Builder"
echo "=========================================="
echo ""
echo "Building: ${IMAGE_NAME}:${VERSION}"
echo ""

# Build the image using docker-compose.dev.yml
echo "Step 1: Building image from Dockerfile..."
docker-compose -f docker-compose.dev.yml build

# Get the image ID that was just built
IMAGE_ID=$(docker images -q youtube-study-buddy-dev 2>/dev/null | head -1)

if [ -z "$IMAGE_ID" ]; then
    echo "Error: Could not find built image"
    exit 1
fi

echo "Built image ID: $IMAGE_ID"
echo ""

# Tag the image
echo "Step 2: Tagging image..."
docker tag $IMAGE_ID ${IMAGE_NAME}:${VERSION}

if [ "$VERSION" != "latest" ]; then
    docker tag $IMAGE_ID ${IMAGE_NAME}:latest
    echo "Tagged as: ${IMAGE_NAME}:${VERSION} and ${IMAGE_NAME}:latest"
else
    echo "Tagged as: ${IMAGE_NAME}:latest"
fi

echo ""
echo "✓ Build complete!"
echo ""
echo "Image details:"
docker images ${IMAGE_NAME}
echo ""
echo "To push to Docker Hub:"
echo "  docker login"
echo "  docker push ${IMAGE_NAME}:${VERSION}"
if [ "$VERSION" != "latest" ]; then
    echo "  docker push ${IMAGE_NAME}:latest"
fi
echo ""
echo "To use in production:"
echo "  docker-compose pull"
echo "  docker-compose up -d"
