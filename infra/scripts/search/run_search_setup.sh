#!/bin/bash

set -e

product_info_file="product_info.tar.gz"
cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

echo "Running search setup..."

# Fetch data:
cp ../data/${product_info_file} .

# Unzip data:
mkdir product_info && mv ${product_info_file} product_info/
cd product_info && tar -xvzf ${product_info_file} && cd ..

# Upload data to storage account blob container:
echo "Uploading files to blob container..."
az storage blob upload-batch \
    --auth-mode login \
    --destination ${BLOB_CONTAINER_NAME} \
    --account-name ${STORAGE_ACCOUNT_NAME} \
    --source "product_info" \
    --pattern "*.md" \
    --overwrite

python3 -m pip install -r requirements.txt
python3 index_setup.py

# Cleanup:
rm -rf product_info/
cd ${cwd}

echo "Search setup complete"
