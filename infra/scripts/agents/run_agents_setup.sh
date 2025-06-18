#!/bin/bash
# `az login` should have been run before executing this script:

set -e

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

echo "Running agents setup..."

export ENV_FILE="${script_dir}/../.env"
python3 -m pip install -r requirements.txt
python3 agents_setup.py

cd ${cwd}

echo "Agents setup complete"
