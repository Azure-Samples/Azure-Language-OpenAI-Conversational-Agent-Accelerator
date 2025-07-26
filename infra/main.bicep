// ========== main.bicep ========== //
targetScope = 'resourceGroup'

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
    ai_foundry_name: ai_foundry.outputs.name
    search_service_name: search_service.outputs.name
    storage_account_name: storage_account.outputs.name
  }
}

//----------- Deploy App -----------//
module container_instance 'resources/container_instance.bicep' = {
  name: 'deploy_container_group'
  params: {
    suffix: suffix
    agents_project_endpoint: ai_foundry.outputs.agents_project_endpoint
    aoai_deployment: ai_foundry.outputs.gpt_deployment_name
    aoai_endpoint: ai_foundry.outputs.openai_endpoint
    language_endpoint: ai_foundry.outputs.language_endpoint
    translator_resource_id: ai_foundry.outputs.translator_resource_id
    managed_identity_name: managed_identity.outputs.name
    search_endpoint: search_service.outputs.endpoint
    blob_container_name: storage_account.outputs.blob_container_name
    embedding_deployment_name: ai_foundry.outputs.embedding_deployment_name
    embedding_model_dimensions: ai_foundry.outputs.embedding_model_dimensions
    embedding_model_name: ai_foundry.outputs.embedding_model_name
    storage_account_connection_string: storage_account.outputs.connection_string
    storage_account_name: storage_account.outputs.name
  }
}

output WEB_APP_URL string = container_instance.outputs.fqdn
