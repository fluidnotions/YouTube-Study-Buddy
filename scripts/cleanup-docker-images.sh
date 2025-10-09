#!/bin/bash
# Cleanup old YouTube Study Buddy Docker images

# Change to project root directory
cd "$(dirname "$0")/.."

echo "YouTube Study Buddy - Docker Image Cleanup"
echo "=========================================="
echo ""

# List current images
echo "Current YouTube Study Buddy images:"
docker images | grep -E "(youtube|study|buddy|ytstudybuddy|tor-debugging)" || echo "No images found"
echo ""

# Confirm cleanup
read -p "Do you want to remove all old images and keep only fluidnotions/youtube-study-buddy:latest? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Removing old images..."

# Remove old images (not the new one)
docker images | grep -E "(tor-debugging-youtube-study-buddy|ytstudybuddy-youtube-study-buddy|youtube-study-buddy)" | \
    grep -v "fluidnotions/youtube-study-buddy" | \
    awk '{print $3}' | \
    xargs -r docker rmi -f

echo ""
echo "Cleanup complete!"
echo ""
echo "Remaining images:"
docker images | grep -E "(youtube|study|buddy)" || echo "No YouTube Study Buddy images found"
echo ""
echo "To build the new image, run:"
echo "  docker-compose -f docker-compose.dev.yml build"
echo "  docker tag <image-id> fluidnotions/youtube-study-buddy:latest"
