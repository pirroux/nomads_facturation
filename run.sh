#!/bin/bash

# Stop any running containers
echo "Stopping any running containers..."
docker stop $(docker ps -q) 2>/dev/null || true

# Check if service_account_keys directory exists
if [ ! -d "service_account_keys" ]; then
  echo "Error: service_account_keys directory not found!"
  exit 1
fi

# Get the name of the first JSON file in service_account_keys directory
KEY_FILE=$(ls service_account_keys/*.json 2>/dev/null | head -1)

if [ -z "$KEY_FILE" ]; then
  echo "Error: No service account key file found in service_account_keys directory!"
  exit 1
fi

KEY_FILENAME=$(basename "$KEY_FILE")
echo "Using service account key: $KEY_FILENAME"

# Remove old image if it exists
echo "Removing old Docker image if it exists..."
docker rmi nomads-app:latest 2>/dev/null || true

# Build and run with Docker
echo "Building Docker image..."
docker build -t nomads-app:latest .

echo "Running container..."
docker run -p 8080:8080 -p 8501:8501 \
  -v $(pwd)/service_account_keys:/app/service_account_keys:ro \
  -v $(pwd)/factures.json:/app/factures.json \
  -e PROJECT_ID=nomadsfacturation \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/service_account_keys/$KEY_FILENAME \
  -e API_URL=http://localhost:8080 \
  nomads-app:latest
