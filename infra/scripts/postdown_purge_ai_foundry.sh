#!/bin/bash
# `az login` should have been run before executing this script:

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

source ${script_dir}/.env

echo "Post-down: purging AI Foundry resource..."

az resource delete --ids /subscriptions/${RG_SUBSCRIPTION_ID}/providers/Microsoft.CognitiveServices/locations/${RG_LOCATION}/resourceGroups/${RG_NAME}/deletedAccounts/${AI_FOUNDRY_NAME}

cd ${cwd}

echo "Post-down: AI Foundry resource purged"
