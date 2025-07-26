@description('Name of Managed Identity resource.')
param managed_identity_name string

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

//----------- SCOPE: Storage Account Role Assignments -----------//
resource storage_account 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storage_account_name
}

// PRINCIPAL: Managed Identity
resource mi_storage_blob_data_contributor_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage_account.id, managed_identity.id, storage_blob_data_contributor_role.id)
  scope: storage_account
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: storage_blob_data_contributor_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: Search service
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
resource mi_search_index_data_contributor_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search_service.id, managed_identity.id, search_index_data_contributor_role.id)
  scope: search_service
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: search_index_data_contributor_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: Managed Identity
resource mi_search_service_contributor_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search_service.id, managed_identity.id, search_service_contributor_role.id)
  scope: search_service
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: search_service_contributor_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: AI Foundry (OpenAI)
resource foundry_search_index_data_contributor_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search_service.id, ai_foundry.id, search_index_data_contributor_role.id)
  scope: search_service
  properties: {
    principalId: ai_foundry.identity.principalId
    roleDefinitionId: search_index_data_contributor_role.id
    principalType: 'ServicePrincipal'
  }
}

//----------- SCOPE: AI Foundry Role Assignments -----------//
resource ai_foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: ai_foundry_name
}

// PRINCIPAL: Managed Identity
resource mi_cognitive_services_openai_contributor_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, managed_identity.id, cognitive_services_openai_contributor_role.id)
  scope: ai_foundry
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: cognitive_services_openai_contributor_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: Managed Identity
resource mi_cognitive_services_language_owner_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, managed_identity.id, cognitive_services_language_owner_role.id)
  scope: ai_foundry
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: cognitive_services_language_owner_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: AI Foundry (OpenAI)
resource foundry_cognitive_services_language_owner_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, ai_foundry.id, cognitive_services_language_owner_role.id)
  scope: ai_foundry
  properties: {
    principalId: ai_foundry.identity.principalId
    roleDefinitionId: cognitive_services_language_owner_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: Managed Identity
resource mi_azure_ai_account_owner_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, managed_identity.id, azure_ai_account_owner_role.id)
  scope: ai_foundry
  properties: {
    principalId: managed_identity.properties.principalId
    roleDefinitionId: azure_ai_account_owner_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: Managed Identity
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
resource search_cognitive_services_openai_contributor_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, search_service.id, cognitive_services_openai_contributor_role.id)
  scope: ai_foundry
  properties: {
    principalId: search_service.identity.principalId
    roleDefinitionId: cognitive_services_openai_contributor_role.id
    principalType: 'ServicePrincipal'
  }
}

// PRINCIPAL: AI Foundry (Cognitive Services User)
resource foundry_cognitive_services_user_role_assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai_foundry.id, ai_foundry.id, cognitive_services_user_role.id)
  scope: ai_foundry
  properties: {
    principalId: ai_foundry.identity.principalId
    roleDefinitionId: cognitive_services_user_role.id
    principalType: 'ServicePrincipal'
  }
}

//----------- Built-in Roles -----------//
@description('Built-in Storage Blob Data Contributor role (https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/storage#storage-blob-data-contributor).')
resource storage_blob_data_contributor_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
    name: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
}

@description('Built-in Storage Blob Data Reader role (https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/storage#storage-blob-data-reader).')
resource storage_blob_data_reader_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
    name: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
}

@description('Built-in Search Service Contributor role (https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/ai-machine-learning#search-service-contributor).')
resource search_service_contributor_role 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  name: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
}

@description('Built-in Search Index Data Contributor role (https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/ai-machine-learning#search-index-data-contributor).')
resource search_index_data_contributor_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
}

@description('Built-in Cognitive Services OpenAI Contributor role (https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-openai-contributor).')
resource cognitive_services_openai_contributor_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: 'a001fd3d-188f-4b5d-821b-7da978bf7442'
}

@description('Built-in Cognitive Services Language Owner role (https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-language-owner).')
resource cognitive_services_language_owner_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: 'f07febfe-79bc-46b1-8b37-790e26e6e498'
}

@description('Built-in Azure AI Account Owner role (https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry?pivots=fdp-project#azure-ai-account-owner).')
resource azure_ai_account_owner_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: 'e47c6f54-e4a2-4754-9501-8e0985b135e1'
}

@description('Built-in Azure AI Account User role (https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry?pivots=fdp-project#azure-ai-user).')
resource azure_ai_account_user_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '53ca6127-db72-4b80-b1b0-d745d6d5456d'
}

@description('Built-in Cognitive Services User role (https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/cognitive-services-user).')
resource cognitive_services_user_role 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: 'a97b65f3-24c7-4388-baec-2e87135dc908'
}

//----------- Outputs -----------//
output name string = managed_identity.name
