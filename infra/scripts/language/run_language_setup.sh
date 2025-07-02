#!/bin/bash
# `az login` should have been run before executing this script:

set -e

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

echo "Running language setup..."

# Fetch data:
cp ../data/*.json .

python3 -m pip install -r requirements.txt
python3 clu_setup.py
if [ "$SKIP_CQA_SETUP" != "true" ]; then
    python3 cqa_setup.py
fi
python3 orchestration_setup.py

# Cleanup:
rm *.json
cd ${cwd}

echo "Language setup complete"
