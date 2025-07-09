#!/bin/bash
# `az login` should have been run before executing this script:

set -e

if [ "$IS_GITHUB_WORKFLOW_RUN" = "true" ]; then
    # Skip parameter validation during GitHub workflow run:
    echo "Pre-provision: skipping parameter validation..."
    az account set --subscription "$AZURE_SUBSCRIPTION_ID"
    exit 0
fi

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

echo "Pre-provision: validating parameters..."

selected_subscription_id=$(az account show --query id --output tsv)
if [ "$selected_subscription_id" != "$AZURE_SUBSCRIPTION_ID" ]; then
    echo "Subscription selected during authentication does NOT match subscription selected in azd"
    echo "$selected_subscription_id != $AZURE_SUBSCRIPTION_ID"
    echo "Aborting..."
    exit 1
fi

# model_region=$(grep -m1 'model_region' ${script_dir}/../parameters.json | awk '{ print $2 }' | tr -d '"')
# if [ -n "$model_region" ] && [ "$model_region" != "$AZURE_LOCATION" ]; then
#     echo "Region selected during parameter customization does NOT match region selected in azd"
#     echo "$model_region != $AZURE_LOCATION"
#     echo "Aborting..."
#     exit 1
# fi

cd ${cwd}

echo "Pre-provision: parameters validated"
