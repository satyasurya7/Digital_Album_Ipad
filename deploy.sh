#!/bin/bash

IMAGE_NAME=fastapi-album
CONTAINER_NAME=fastapi-album-app

# Build the image
docker build -t $IMAGE_NAME .

# Stop and remove old container if it exists
docker rm -f $CONTAINER_NAME 2>/dev/null || true

# Remove old image (except latest build)
docker rmi $IMAGE_NAME:old 2>/dev/null || true

# Run the new container, mapping image directory
docker run -d \
  --name $CONTAINER_NAME \
  -p 8000:80 \
  -v /media/crazy7/immich_pics:/media/crazy7/immich_pics \
  $IMAGE_NAME
