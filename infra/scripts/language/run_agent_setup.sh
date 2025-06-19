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
agent_ids=$(python3 agent_setup.py | )
echo "$agent_ids"

# Parse the JSON and export the environment variables
export TRIAGE_AGENT_ID=$(echo "$agent_ids" | jq -r '.TRIAGE_AGENT_ID')
export HEAD_SUPPORT_AGENT_ID=$(echo "$agent_ids" | jq -r '.HEAD_SUPPORT_AGENT_ID')
export ORDER_STATUS_AGENT_ID=$(echo "$agent_ids" | jq -r '.ORDER_STATUS_AGENT_ID')
export ORDER_CANCEL_AGENT_ID=$(echo "$agent_ids" | jq -r '.ORDER_CANCEL_AGENT_ID')
export ORDER_REFUND_AGENT_ID=$(echo "$agent_ids" | jq -r '.ORDER_REFUND_AGENT_ID')

# Verify the environment variables
echo "TRIAGE_AGENT_ID=$TRIAGE_AGENT_ID"
echo "HEAD_SUPPORT_AGENT_ID=$HEAD_SUPPORT_AGENT_ID"
echo "ORDER_STATUS_AGENT_ID=$ORDER_STATUS_AGENT_ID"
echo "ORDER_CANCEL_AGENT_ID=$ORDER_CANCEL_AGENT_ID"
echo "ORDER_REFUND_AGENT_ID=$ORDER_REFUND_AGENT_ID"
