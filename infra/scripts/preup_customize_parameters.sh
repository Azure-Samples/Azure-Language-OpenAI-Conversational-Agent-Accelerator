#!/bin/bash
# `az login` should have been run before executing this script:

declare -a regions=(
    "australiaeast"
    "centralindia"
    "eastus"
    "eastus2"
    "northeurope"
    "southcentralus"
    "switzerlandnorth"
    "uksouth"
    "westeurope"
    "westus2"
    "westus3"
)

declare -a models=(
    "OpenAI.GlobalStandard.gpt-4o"
    "OpenAI.GlobalStandard.gpt-4o-mini"
    "OpenAI.GlobalStandard.text-embedding-3-small"
    "OpenAI.GlobalStandard.text-embedding-ada-002"
    "OpenAI.Standard.gpt-4o"
    "OpenAI.Standard.gpt-4o-mini"
    "OpenAI.Standard.text-embedding-3-small"
    "OpenAI.Standard.text-embedding-ada-002"
)

declare -A valid_regions

selected_subscription=${az account show --query name --output tsv}

# Fetch quota information per region per model:
for region in "${regions[@]}"; do
    echo "----------------------------------------"
    echo "Checking region: $region"

    quota_info="$(az cognitiveservices usage list --location "$region" --output json)"

    if [ -z "$quota_info" ]; then
        echo "WARNING: failed to retrieve quota information for region $region. Skipping."
        continue
    fi

    gpt_available="false"
    embedding_available="false"
    region_quota_info=""

    for model in "${models[@]}"; do
        model_info="$(echo "$quota_info" | awk -v model="\"value\": \"$model\"" '
            BEGIN { RS="},"; FS="," }
            $0 ~ model { print $0 }
        ')"

        if [ -z "$model_info" ]; then
            echo "WARNING: no quota information found for model $model in region $region. Skipping."
            continue
        fi

        current_value="$(echo "$model_info" | awk -F': ' '/"currentValue"/ {print $2}'  | tr -d ',' | tr -d ' ')"
        limit="$(echo "$model_info" | awk -F': ' '/"limit"/ {print $2}' | tr -d ',' | tr -d ' ')"

        current_value="$(echo "${current_value:-0}" | cut -d'.' -f1)"
        limit="$(echo "${limit:-0}" | cut -d'.' -f1)"
        available=$(($limit - $current_value))

        if [ "$available" -gt 0 ]; then
            region_quota_info+="$model=$available "
            if grep -q "gpt" <<< "$model"; then
                gpt_available="true"
            elif grep -q "embedding" <<< "$model"; then
                embedding_available="true"
            fi
        fi

        echo "Model: $model | Used: $current_value | Limit: $limit | Available: $available"
    done

    if [ "$gpt_available" = "true" ] && [ "$embedding_available" = "true" ]; then
        valid_regions[$region]="$region_quota_info"
    fi
done

# Select region:
while true; do
    echo -e "\nAvailable regions: "
    for region_option in "${!valid_regions[@]}"; do
        echo "-> $region_option"
    done

    read -p "Select a region: " selected_region
    if [[ -v valid_regions[$selected_region] ]]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Get model information from selected region:
declare -A valid_gpt_models
declare -A valid_embedding_models
region_quota_info="${valid_regions[$selected_region]}"

for model_info in $region_quota_info; do
    model_name="$(echo "$model_info" | cut -d "=" -f1)"
    available="$(echo "$model_info" | cut -d "=" -f2)"

    if grep -q "gpt" <<< "$model_name"; then
        valid_gpt_models[$model_name]="$available"
    elif grep -q "embedding" <<< "$model_name"; then
        valid_embedding_models[$model_name]="$available"
    fi
 done

# Select GPT model:
while true; do
    echo -e "\nAvailable GPT models in $selected_region:"
    for model_option in "${!valid_gpt_models[@]}"; do
        echo "-> $model_option (${valid_gpt_models[$model_option]} quota available)"
    done

    read -p "Select a GPT model: " selected_gpt_model
    if [[ -v valid_gpt_models[$selected_gpt_model] ]]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Select GPT model quota:
while true; do
    available=${valid_gpt_models[$selected_gpt_model]}
    echo -e "\nAvailable quota for $selected_gpt_model in $selected_region: $available"

    read -p "Select capacity for $selected_gpt_model deployment: " selected_gpt_quota

    if [ 0 -lt $selected_gpt_quota ] && [ $selected_gpt_quota -le $available ]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Select embedding model:
while true; do
    echo -e "\nAvailable embedding models in $selected_region:"
    for model_option in "${!valid_embedding_models[@]}"; do
        echo "-> $model_option (${valid_embedding_models[$model_option]} quota available)"
    done

    read -p "Select an embedding model: " selected_embedding_model
    if [[ -v valid_embedding_models[$selected_embedding_model] ]]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Select embedding model quota:
while true; do
    available=${valid_embedding_models[$selected_embedding_model]}
    echo -e "\nAvailable quota for $selected_embedding_model in $selected_region: $available"

    read -p "Select capacity for $selected_embedding_model deployment: " selected_embedding_quota

    if [ 0 -lt $selected_embedding_quota ] && [ $selected_embedding_quota -le $available ]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Fetch summary:
gpt_model_name=$(echo "$selected_gpt_model" | cut -d "." -f3)
gpt_deployment_type=$(echo "$selected_gpt_model" | cut -d "." -f2)

embedding_model_name=$(echo "$selected_embedding_model" | cut -d "." -f3)
embedding_deployment_type=$(echo "$selected_embedding_model" | cut -d "." -f2)

echo -e "\n--------------------------\nSummary:"
echo "Subscription: $selected_subscription"
echo "Region: $selected_region"
echo "GPT model name: $gpt_model_name"
echo "GPT model deployment type: $gpt_deployment_type"
echo "GPT model capacity: $selected_gpt_quota"
echo "Embedding model name: $embedding_model_name"
echo "Embedding model deployment type: $embedding_deployment_type"
echo "Embedding model capacity: $selected_embedding_quota"

# Set AZD env variables:
export AZURE_ENV_GPT_MODEL_NAME=$gpt_model_name
export AZURE_ENV_GPT_MODEL_CAPACITY=$selected_gpt_quota
export AZURE_ENV_GPT_MODEL_DEPLOYMENT_TYPE=$gpt_deployment_type

export AZURE_ENV_EMBEDDING_MODEL_NAME=$embedding_model_name
export AZURE_ENV_EMBEDDING_MODEL_CAPACITY=$selected_embedding_quota
export AZURE_ENV_EMBEDDING_MODEL_DEPLOYMENT_TYPE=$embedding_deployment_type

echo -e "\nazd parameters set"

echo "Ensure that you select the following subscription: ${selected_subscription}"
echo "Ensure that you select the following region: ${selected_region}"
