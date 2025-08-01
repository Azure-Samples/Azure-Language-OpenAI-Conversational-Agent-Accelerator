#!/bin/bash

set -e

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
src_dir="${script_dir}/../../src"
frontend_dir="${src_dir}/frontend"
backend_dir="${src_dir}/backend"

cd ${script_dir}

# Authenticate:
az login --identity

# Ensure pip:
python3 -m ensurepip --upgrade

# Install deps:
tdnf install -y tar
tdnf install -y awk

# Install nodejs:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash
\. "$HOME/.nvm/nvm.sh"
nvm install 22
node -v
nvm current
npm -v

# Run setup:
export CONFIG_DIR="$(pwd)/config_dir"
mkdir -p $CONFIG_DIR
echo "Running setup..."
source language/run_language_setup.sh
bash search/run_search_setup.sh ${STORAGE_ACCOUNT_NAME} ${BLOB_CONTAINER_NAME}
source language/run_agent_setup.sh

# Build UI:
echo "Building UI..."
cd ${frontend_dir}
npm install
npm run build

# Run app:
echo "Running uvicorn app..."
cd ${backend_dir}
python3 -m pip install -r requirements.txt
cd src
cp -r ${frontend_dir}/dist .

# Check if APP_MODE is set, default to semantic_kernel
APP_MODE=${APP_MODE:-semantic_kernel}

# Launch the app:
echo "Launching the app based on the environment variable APP_MODE..."
if [ "$APP_MODE" == "SEMANTIC_KERNEL" ]; then
    echo "Launching app with agents (semantic_kernel_app.py)..."
    python3 -m uvicorn semantic_kernel_app:app --host 0.0.0.0 --port 8000
elif [ "$APP_MODE" == "CLASSIC" ]; then
    echo "Launching non-agent classic app (classic_app.py)..."
    python3 -m uvicorn classic_app:app --host 0.0.0.0 --port 8000
else
    echo "Unknown APP_MODE: $APP_MODE"
    exit 1
fi
