#!/bin/bash
# `az login` should have been run before executing this script:

set -e

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

selected_subscription=$(az account show --query name --output tsv)
model_region=""

if [ "$IS_GITHUB_WORKFLOW_RUN" = "true" ]; then
    # Skip parameter customization during GitHub workflow run:
    echo "Pre-up: using configured workflow variables..."
    generate_parameters
    cd ${cwd}
    exit 0
fi

function print_summary {
    echo -e "--------------------------\nSUMMARY:"
    echo "Subscription: $selected_subscription"
    echo "Region: $MODEL_LOCATION"
    echo "Parameters:"
    cat ${script_dir}/../parameters.json

    echo "ENSURE THAT YOU SELECT THE FOLLOWING SUBSCRIPTION: ${selected_subscription}"
    echo "ENSURE THAT YOU SELECT THE FOLLOWING REGION: ${model_region}"
}

function generate_parameters {
    cat << EOF > ${script_dir}/../parameters.json
{
    "router_type": "$AZD_PARAM_ROUTER_TYPE",
    "gpt_model_name": "$AZD_PARAM_GPT_MODEL_NAME",
    "gpt_model_deployment_type": "$AZD_PARAM_GPT_MODEL_DEPLOYMENT_TYPE",
    "gpt_model_capacity": "$AZD_PARAM_GPT_MODEL_CAPACITY",
    "embedding_model_name": "$AZD_PARAM_EMBEDDING_MODEL_NAME",
    "embedding_model_deployment_type": "$AZD_PARAM_EMBEDDING_MODEL_DEPLOYMENT_TYPE",
    "embedding_model_capacity": "$AZD_PARAM_EMBEDDING_MODEL_CAPACITY",
    "model_region": "$model_region"
}
EOF
}

read -p "Pre-up: would you like to skip parameter customization and use the values found in parameters.json? (y/n): " user_response
if [ "$user_response" = "y" ]; then
    echo "Pre-up: skipping parameter customization..."
    print_summary
    cd ${cwd}
    exit 0
fi

echo "Pre-up: customizing parameters..."

declare -a routers=(
    "BYPASS"
    "CLU"
    "CQA"
    "ORCHESTRATION"
    "FUNCTION_CALLING"
    "TRIAGE_AGENT"
)

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

declare -A available_regions

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
    region_model_info=""

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
            region_model_info+="$model=$available "
            if grep -q "gpt" <<< "$model"; then
                gpt_available="true"
            elif grep -q "embedding" <<< "$model"; then
                embedding_available="true"
            fi
        fi

        echo "Model: $model | Used: $current_value | Limit: $limit | Available: $available"
    done

    if [ "$gpt_available" = "true" ] && [ "$embedding_available" = "true" ]; then
        available_regions[$region]="$region_model_info"
    fi
done

# Select region:
while true; do
    echo -e "\nAvailable regions: "
    for region_option in "${!available_regions[@]}"; do
        echo "-> $region_option"
    done

    read -p "Select a region: " selected_region
    if [[ -v available_regions[$selected_region] ]]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Get model information from selected region:
declare -A available_gpt_models
declare -A available_embedding_models
region_model_info="${available_regions[$selected_region]}"

for model_info in $region_model_info; do
    model_name="$(echo "$model_info" | cut -d "=" -f1)"
    available_quota="$(echo "$model_info" | cut -d "=" -f2)"

    if grep -q "gpt" <<< "$model_name"; then
        available_gpt_models[$model_name]="$available_quota"
    elif grep -q "embedding" <<< "$model_name"; then
        available_embedding_models[$model_name]="$available_quota"
    fi
 done

# Select GPT model:
while true; do
    echo -e "\nAvailable GPT models in $selected_region:"
    for model_option in "${!available_gpt_models[@]}"; do
        available_quota=${available_gpt_models[$model_option]}
        echo "-> $model_option ($available_quota quota available)"
    done

    read -p "Select a GPT model: " selected_gpt_model
    if [[ -v available_gpt_models[$selected_gpt_model] ]]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Select GPT model quota:
while true; do
    available_quota=${available_gpt_models[$selected_gpt_model]}
    echo -e "\nAvailable quota for $selected_gpt_model in $selected_region: $available_quota"

    read -p "Select capacity for $selected_gpt_model deployment: " selected_gpt_quota

    if [ 0 -lt $selected_gpt_quota ] && [ $selected_gpt_quota -le $available_quota ]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Select embedding model:
while true; do
    echo -e "\nAvailable embedding models in $selected_region:"
    for model_option in "${!available_embedding_models[@]}"; do
        available_quota=${available_embedding_models[$model_option]}
        echo "-> $model_option ($available_quota quota available)"
    done

    read -p "Select an embedding model: " selected_embedding_model
    if [[ -v available_embedding_models[$selected_embedding_model] ]]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Select embedding model quota:
while true; do
    available_quota=${available_embedding_models[$selected_embedding_model]}
    echo -e "\nAvailable quota for $selected_embedding_model in $selected_region: $available_quota"

    read -p "Select capacity for $selected_embedding_model deployment: " selected_embedding_quota

    if [ 0 -lt $selected_embedding_quota ] && [ $selected_embedding_quota -le $available_quota ]; then
        break
    else
        echo "Invalid selection"
    fi
done

echo "----------------------------------------"

# Select router type:
while true; do
    echo -e "\nAvailable router types:"
    for router in "${routers[@]}"; do
        echo "-> $router"
    done

    read -p "Select a router type: " selected_router_type
    if [[ ${routers[@]} =~ $selected_router_type ]]; then
        break
    else
        echo "Invalid selection"
    fi
done

# Set variables:
gpt_model_name=$(echo "$selected_gpt_model" | cut -d "." -f3)
gpt_model_deployment_type=$(echo "$selected_gpt_model" | cut -d "." -f2)

embedding_model_name=$(echo "$selected_embedding_model" | cut -d "." -f3)
embedding_model_deployment_type=$(echo "$selected_embedding_model" | cut -d "." -f2)

AZD_PARAM_ROUTER_TYPE="$selected_router_type"
AZD_PARAM_GPT_MODEL_NAME="$gpt_model_name"
AZD_PARAM_GPT_MODEL_DEPLOYMENT_TYPE="$gpt_model_deployment_type"
AZD_PARAM_GPT_MODEL_CAPACITY="$selected_gpt_quota"
AZD_PARAM_EMBEDDING_MODEL_NAME="$embedding_model_name"
AZD_PARAM_EMBEDDING_MODEL_DEPLOYMENT_TYPE="$embedding_model_deployment_type"
AZD_PARAM_EMBEDDING_MODEL_CAPACITY="$selected_embedding_quota"

model_region="$selected_region"

generate_parameters
print_summary

cd ${cwd}
