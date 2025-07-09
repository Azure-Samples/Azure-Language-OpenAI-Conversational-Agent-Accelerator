#!/bin/bash
# `az login` should have been run before executing this script:

set -e

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

source ${script_dir}/.env

echo "Post-provision: running setup scripts..."

bash language/run_language_setup.sh
bash search/run_search_setup.sh
bash agents/run_agents_setup.sh

cd ${cwd}

echo "Post-provision: setup scripts complete"
