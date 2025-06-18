#!/bin/bash

set -e

if [ "$IS_GITHUB_WORKFLOW_RUN" = "true" ]; then
    # Skip parameter validation during GitHub workflow run:
    echo "Skipping parameter validation..."
    exit 0
fi

echo "Pre-provision: validating parameters..."

if [ "$AZURE_ENV_SUBSCRIPTION_ID" != "$AZURE_SUBSCRIPTION_ID" ]; then
    echo "Subscription selected during authentication does NOT match subscription selected in azd"
    echo "$AZURE_ENV_SUBSCRIPTION_ID != $AZURE_SUBSCRIPTION_ID"
    echo "Aborting..."
    exit 1
fi

if [ "$AZURE_ENV_LOCATION" != "$AZURE_LOCATION" ]; then
    echo "Region selected during parameter customization does NOT match region selected in azd"
    echo "$AZURE_ENV_LOCATION != $AZURE_LOCATION"
    echo "Aborting..."
    exit 1
fi

echo "Pre-provision: parameters validated"
