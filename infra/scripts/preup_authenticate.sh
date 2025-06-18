#!/bin/bash

set -e

if [ "$IS_GITHUB_WORKFLOW_RUN" = "true" ]; then
    # Skip authentication during GitHub workflow run:
    echo "Skipping authentication..."
    exit 0
fi

echo "Pre-up: authenticating to Azure..."
echo "ENSURE YOU SELECT THE SUBSCRIPTION YOU ARE DEPLOYING RESOURCES TO:"

az login
azd auth login

echo "Pre-up: authentication complete"
