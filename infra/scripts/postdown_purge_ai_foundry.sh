#!/bin/bash
# `az login` should have been run before executing this script:

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

source ${script_dir}/.env

echo "Purging AI Foundry resource..."

az resource delete --ids /subscriptions/${SUBSCRIPTION}/providers/Microsoft.CognitiveServices/locations/${LOCATION}/resourceGroups/${RG_NAME}/deletedAccounts/${AI_FOUNDRY_NAME}

cd ${cwd}

echo "Post-down AI Foundry resource purged"
