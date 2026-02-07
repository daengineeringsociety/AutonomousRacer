#!/bin/bash
# Move to the .devcontainer folder where the yaml lives
cd .devcontainer

echo "Starting AutonomousRacer environment..."
docker compose up -d

echo "Done. You can now use your enter script or open VS Code."