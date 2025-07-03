#!/bin/bash

set -e

cwd=$(pwd)

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    # Script is being sourced
    script_dir=$(dirname $(realpath "${BASH_SOURCE[0]}"))
else
    # Script is being executed
    script_dir=$(dirname $(realpath "$0"))
fi

cd ${script_dir}

# Fetch data:
cp ../../data/*.json .
cp ../../openapi_specs/*.json .

# Run agent setup:
echo "Running agent setup..."
python3 agent_setup.py
echo "Agent setup complete"
