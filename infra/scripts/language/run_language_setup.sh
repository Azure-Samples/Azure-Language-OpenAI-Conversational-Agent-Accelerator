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

# Install requirements:
echo "Installing requirements..."
python3 -m pip install -r requirements.txt

# Run setup:
echo "Running CLU setup..."
python3 clu_setup.py
echo "Running CQA setup..."
python3 cqa_setup.py
echo "Running Orchestration setup..."
python3 orchestration_setup.py

# Cleanup:
rm *.json
cd ${cwd}

echo "Language setup complete"
