#!/bin/bash

set -e

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

echo "Running language setup..."

# Fetch data:
cp ../data/*.json .

python3 -m pip install -r requirements.txt
python3 clu_setup.py
python3 cqa_setup.py
python3 orchestration_setup.py

# Cleanup:
rm *.json
cd ${cwd}

echo "Language setup complete"
