#!/bin/bash
# `az login` should have been run before executing this script:

set -e

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

echo "Running agents setup..."

echo "inject val: ${TRIAGE_AGENT_INJECT_EXAMPLES}"
echo "wf val: ${IS_GITHUB_WORKFLOW_RUN}"

export ENV_FILE="${script_dir}/../.env"
python3 -m pip install -r requirements.txt
python3 agents_setup.py

cd ${cwd}

echo "Agents setup complete"
