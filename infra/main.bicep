// ========== main.bicep ========== //
targetScope = 'resourceGroup'

// Conv-Agent:
@allowed([
  'BYPASS'
  'CLU'
  'CQA'
  'ORCHESTRATION'
  'FUNCTION_CALLING'
  'TRIAGE_AGENT'
])
param router_type string = 'TRIAGE_AGENT'

// GPT model:
@description('Name of GPT model to deploy.')
@allowed([
  'gpt-4o-mini'
  'gpt-4o'
])
param gpt_model_name string

@description('Capacity of GPT model deployment.')
@minValue(1)
param gpt_deployment_capacity int

@description('GPT model deployment type.')
@allowed([
  'Standard'
  'GlobalStandard'
])
param gpt_deployment_type string

// Embedding model:
@description('Name of Embedding model to deploy.')
@allowed([
  'text-embedding-ada-002'
  'text-embedding-3-small'
])
param embedding_model_name string

@description('Capacity of embedding model deployment.')
@minValue(1)
param embedding_deployment_capacity int

@description('Embedding model deployment type.')
@allowed([
  'Standard'
  'GlobalStandard'
])
param embedding_deployment_type string

// Variables:
var suffix = uniqueString(subscription().id, resourceGroup().id, resourceGroup().location)

//----------- Deploy App Dependencies -----------//
module managed_identity 'resources/managed_identity.bicep' = {
  name: 'deploy_managed_identity'
  params: {
    suffix: suffix
  }
}

module container_registry 'resources/container_registry.bicep' = {
  name: 'deploy_container_registry'
  params: {
    suffix: suffix
  }
}

module storage_account 'resources/storage_account.bicep' = {
  name: 'deploy_storage_account'
  params: {
    suffix: suffix
  }
}

module search_service 'resources/search_service.bicep' = {
  name: 'deploy_search_service'
  params: {
    suffix: suffix
  }
}

module ai_foundry 'resources/ai_foundry.bicep' = {
  name: 'deploy_ai_foundry'
  params: {
    suffix: suffix
    managed_identity_name: managed_identity.outputs.name
    search_service_name: search_service.outputs.name
    gpt_model_name: gpt_model_name
    gpt_deployment_capacity: gpt_deployment_capacity
    gpt_deployment_type: gpt_deployment_type
    embedding_model_name: embedding_model_name
    embedding_deployment_capacity: embedding_deployment_capacity
    embedding_deployment_type: embedding_deployment_type
  }
}

module role_assignments 'resources/role_assignments.bicep' = {
  name: 'create_role_assignments'
  params: {
    managed_identity_name: managed_identity.outputs.name
    container_registry_name: container_registry.outputs.name
    ai_foundry_name: ai_foundry.outputs.name
    search_service_name: search_service.outputs.name
    storage_account_name: storage_account.outputs.name
  }
}

//----------- Outputs -----------//

// Resource Group:
output LOCATION string = resourceGroup().location
output RG_NAME string = resourceGroup().name
output RG_SUFFIX string = suffix

// Managed Identity:
output MI_ID string = managed_identity.outputs.id
output MI_CLIENT_ID string = managed_identity.outputs.client_id

// Language:
output LANGUAGE_ENDPOINT string = ai_foundry.outputs.language_endpoint
output CLU_PROJECT_NAME string = 'conv-agent-clu'
output CLU_MODEL_NAME string = 'clu-m1'
output CLU_DEPLOYMENT_NAME string = 'clu-m1-d1'
output CLU_CONFIDENCE_THRESHOLD string = '0.5'
output CQA_PROJECT_NAME string = 'conv-agent-cqa'
output CQA_DEPLOYMENT_NAME string = 'production'
output CQA_CONFIDENCE_THRESHOLD string = '0.5'
output ORCHESTRATION_PROJECT_NAME string = 'conv-agent-orch'
output ORCHESTRATION_MODEL_NAME string = 'orch-m1'
output ORCHESTRATION_DEPLOYMENT_NAME string = 'orch-m1-d1'
output ORCHESTRATION_CONFIDENCE_THRESHOLD string = '0.5'
output PII_ENABLED string = 'true'
output PII_CATEGORIES string = 'organization,person'
output PII_CONFIDENCE_THRESHOLD string = '0.5'

// AOAI:
output AOAI_ENDPOINT string = ai_foundry.outputs.openai_endpoint
output AOAI_DEPLOYMENT string = ai_foundry.outputs.gpt_deployment_name
output EMBEDDING_DEPLOYMENT_NAME string = ai_foundry.outputs.embedding_deployment_name
output EMBEDDING_MODEL_NAME string = ai_foundry.outputs.embedding_model_name
output EMBEDDING_MODEL_DIMENSIONS string = string(ai_foundry.outputs.embedding_model_dimensions)

// Agents:
output AGENTS_PROJECT_ENDPOINT string = ai_foundry.outputs.agents_project_endpoint
output MAX_AGENT_RETRY string = '5'
output DELETE_OLD_AGENTS string = 'true'

// Search:
output SEARCH_ENDPOINT string = search_service.outputs.endpoint
output SEARCH_INDEX_NAME string = 'conv-agent-manuals-idx'

// Storage:
output STORAGE_ACCOUNT_NAME string = storage_account.outputs.name
output STORAGE_ACCOUNT_CONNECTION_STRING string = storage_account.outputs.connection_string
output BLOB_CONTAINER_NAME string = storage_account.outputs.blob_container_name

// ACR:
output ACR_NAME string = container_registry.outputs.name

// Conv-Agent:
output ROUTER_TYPE string = router_type
