@description('Resource name suffix.')
param suffix string

@description('Name of Container Registry resource.')
param name string = 'acr${suffix}'

@description('Location for all resources.')
param location string = resourceGroup().location

//----------- Container Registry Resource -----------//
resource container_registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: name
  location: location 
  sku: {
    name: 'Standard'
  }
}

//----------- Outputs -----------//
output name string = container_registry.name
