@description('Name of Managed Identity resource.')
param managed_identity_name string

@description('Name of Container Registry resource.')
param container_registry_name string

@description('Name of Storage Account resource.')
param storage_account_name string

@description('Name of AI Foundry resource.')
param ai_foundry_name string

@description('Name of Search Service resource.')
param search_service_name string

//----------- Managed Identity Resource -----------//
resource managed_identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: managed_identity_name
}

//----------- SCOPE: Container Registry Role Assignments -----------//
resource container_registry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: container_registry_name
}

// PRINCIPAL: Managed Identity
// Allow container instance to pull docker image from ACR using MI.
resource mi_acr_pull_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(container_registry.id, managed_identity.id, acr_pull_role.id)
  scope: container_registry
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: acr_pull_role.id
    principalType: 'ServicePrincipal'
  }
}

//----------- SCOPE: Storage Account Role Assignments -----------//
resource storage_account 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storage_account_name
}

// PRINCIPAL: Search service
// Allow search service to access blob container data to run indexing pipeline.
resource search_storage_blob_data_reader_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage_account.id, search_service.id, storage_blob_data_reader_role.id)
  scope: storage_account
  properties: {
    principalId: search_service.identity.principalId
    roleDefinitionId: storage_blob_data_reader_role.id
    principalType: 'ServicePrincipal'
  }
}

//----------- SCOPE: Search Service Role Assignments -----------//
resource search_service 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: search_service_name
}

// PRINCIPAL: Managed Identity
// Allow container instance to fetch RAG grounding data from search index using MI.
resource mi_search_index_data_reader_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search_service.id, managed_identity.id, search_index_data_reader_role.id)
  scope: search_service
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: search_index_data_reader_role.id
    principalType: 'ServicePrincipal'
  }
}

//----------- SCOPE: AI Foundry Role Assignments -----------//
resource ai_foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: ai_foundry_name
}

// PRINCIPAL: Managed Identity
// Allow container instance to call AOAI chat completions using MI.
resource mi_cognitive_services_openai_user_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, managed_identity.id, cognitive_services_openai_user_role.id)
  scope: ai_foundry
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: cognitive_services_openai_user_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: Managed Identity
// Allow container instance to call language APIs using MI.
resource mi_cognitive_services_language_reader_role_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, managed_identity.id, cognitive_services_language_reader_role.id)
  scope: ai_foundry
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: cognitive_services_language_reader_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: Managed Identity
// Allow container instance to call agents API using MI.
resource mi_azure_ai_account_user_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, managed_identity.id, azure_ai_account_user_role.id)
  scope: ai_foundry
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: azure_ai_account_user_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: Search Service
// Allow search service to run AOAI embedding model in indexing pipeline.
resource search_cognitive_services_openai_user_role_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, search_service.id, cognitive_services_openai_user_role.id)
  scope: ai_foundry
  properties: {
    principalId: search_service.identity.principalId
    roleDefinitionId: cognitive_services_openai_user_role.id
    principalType: 'ServicePrincipal'
  }
}

//----------- Built-in Roles -----------//
@description('Built-in Acr Pull role (https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/containers#acrpull).')
resource acr_pull_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
    name: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
}

@description('Built-in Storage Blob Data Reader role (https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/storage#storage-blob-data-reader).')
resource storage_blob_data_reader_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
    name: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
}

@description('Built-in Search Index Data Reader role (https://docs.azure.cn/en-us/role-based-access-control/built-in-roles/ai-machine-learning#search-index-data-reader).')
resource search_index_data_reader_role 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  name: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
}

@description('Built-in Cognitive Services OpenAI User role (https://docs.azure.cn/en-us/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-openai-user).')
resource cognitive_services_openai_user_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
}

@description('Built-in Cognitive Services Language Reader role (https://docs.azure.cn/en-us/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-language-reader).')
resource cognitive_services_language_reader_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '7628b7b8-a8b2-4cdc-b46f-e9b35248918e'
}

@description('Built-in Azure AI Account User role (https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry?pivots=fdp-project#azure-ai-user).')
resource azure_ai_account_user_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '53ca6127-db72-4b80-b1b0-d745d6d5456d'
}

//----------- Outputs -----------//
output name string = managed_identity.name
