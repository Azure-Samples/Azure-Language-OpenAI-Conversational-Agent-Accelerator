#!/bin/bash

# `az login` should have been run before executing this script:

set -ex

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

echo "Running post-provision setup scripts..."

bash language/run_language_setup.sh
bash search/run_search_setup.sh
bash agents/run_agents_setup.sh

cd ${cwd}

echo "Post-provision setup scripts complete"
