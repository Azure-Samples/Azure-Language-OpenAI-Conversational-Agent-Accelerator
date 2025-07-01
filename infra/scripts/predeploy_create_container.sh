#!/bin/bash
# `az login` should have been run before executing this script:

set -e

cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
src_dir="${script_dir}/../../src"
cd $src_dir

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

source ${script_dir}/.env

# Build docker image:
echo "Pre-deploy: building app image..."

repo="conv-agent"
image="app"
tag=$(date '+%Y%m%d-%H%M')

# No Docker dependency:
# az acr build \
#     -r ${ACR_NAME} \
#     -t ${repo}/${image}:${tag} \
#     .

docker build . -t ${ACR_NAME}.azurecr.io/${repo}/${image}:${tag}

# Push image to ACR:
echo "Pre-deploy: pushing image to acr..."

az acr login --name ${ACR_NAME}
docker push ${ACR_NAME}.azurecr.io/${repo}/${image}:${tag}

# Create container instance:
echo "Pre-deploy: creating container instance..."

result=$(az container create \
    --resource-group ${RG_NAME} \
    --name "ci-${RG_SUFFIX}" \
    --location ${RG_LOCATION} \
    --image ${ACR_NAME}.azurecr.io/${repo}/${image}:${tag} \
    --assign-identity ${MI_ID} \
    --acr-identity ${MI_ID} \
    --restart-policy "Never" \
    --ports 80 \
    --protocol "TCP" \
    --cpu 1 \
    --memory 1 \
    --dns-name-label "conv-agent-app-${RG_SUFFIX}" \
    --os-type "Linux" \
    --ip-address "Public" \
    --environment-variables \
        AGENTS_PROJECT_ENDPOINT=$AGENTS_PROJECT_ENDPOINT \
        USE_MI_AUTH=true \
        MI_CLIENT_ID=$MI_CLIENT_ID \
        AOAI_ENDPOINT=$AOAI_ENDPOINT \
        AOAI_DEPLOYMENT=$AOAI_DEPLOYMENT \
        SEARCH_ENDPOINT=$SEARCH_ENDPOINT \
        SEARCH_INDEX_NAME=$SEARCH_INDEX_NAME \
        EMBEDDING_DEPLOYMENT_NAME=$EMBEDDING_DEPLOYMENT_NAME \
        EMBEDDING_MODEL_NAME=$EMBEDDING_MODEL_NAME \
        EMBEDDING_MODEL_DIMENSIONS=$EMBEDDING_MODEL_DIMENSIONS \
        STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT_NAME \
        STORAGE_ACCOUNT_CONNECTION_STRING=$STORAGE_ACCOUNT_CONNECTION_STRING \
        BLOB_CONTAINER_NAME=$BLOB_CONTAINER_NAME \
        LANGUAGE_ENDPOINT=$LANGUAGE_ENDPOINT \
        CLU_PROJECT_NAME=$CLU_PROJECT_NAME \
        CLU_MODEL_NAME=$CLU_MODEL_NAME \
        CLU_DEPLOYMENT_NAME=$CLU_DEPLOYMENT_NAME \
        CLU_CONFIDENCE_THRESHOLD=$CLU_CONFIDENCE_THRESHOLD \
        CQA_PROJECT_NAME=$CQA_PROJECT_NAME \
        CQA_DEPLOYMENT_NAME=$CQA_DEPLOYMENT_NAME \
        CQA_CONFIDENCE_THRESHOLD=$CQA_CONFIDENCE_THRESHOLD \
        ORCHESTRATION_PROJECT_NAME=$ORCHESTRATION_PROJECT_NAME \
        ORCHESTRATION_MODEL_NAME=$ORCHESTRATION_MODEL_NAME \
        ORCHESTRATION_DEPLOYMENT_NAME=$ORCHESTRATION_DEPLOYMENT_NAME \
        ORCHESTRATION_CONFIDENCE_THRESHOLD=$ORCHESTRATION_CONFIDENCE_THRESHOLD \
        PII_ENABLED=$PII_ENABLED \
        PII_CATEGORIES=$PII_CATEGORIES \
        PII_CONFIDENCE_THRESHOLD=$PII_CONFIDENCE_THRESHOLD \
        ROUTER_TYPE=$ROUTER_TYPE \
        MAX_AGENT_RETRY=$MAX_AGENT_RETRY \
        TRIAGE_AGENT_ID=$TRIAGE_AGENT_ID)

fqdn=$(echo "$result" | grep -m1 '"fqdn": ' "-" | awk '{print $2 }' | tr -d ',"')

echo -e "\nWeb-App URL: ${fqdn}"

echo "Pre-deploy: container instance spawned"

cd ${cwd}
