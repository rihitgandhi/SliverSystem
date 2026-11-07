param location string
@secure()
param flaskSecret string

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'sliversystemdg395e'
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'SliverSystem-Plan'
  location: location
  kind: 'linux'
  sku: { name: 'B1', tier: 'Basic', capacity: 1 }
  properties: { reserved: true }
}

resource web 'Microsoft.Web/sites@2023-12-01' = {
  name: 'sliversystem-dg395e'
  location: location
  kind: 'app,linux,container'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${registry.properties.loginServer}/sliversystem:initial'
      acrUseManagedIdentityCreds: true
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      healthCheckPath: '/api/health'
      appSettings: [
        { name: 'WEBSITES_PORT', value: '10000' }
        { name: 'PORT', value: '10000' }
        { name: 'APP_ENV', value: 'production' }
        { name: 'FLASK_DEBUG', value: 'false' }
        { name: 'FLASK_SECRET_KEY', value: flaskSecret }
        { name: 'WEBSITES_CONTAINER_START_TIME_LIMIT', value: '600' }
      ]
    }
  }
}

resource pull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, web.id, 'AcrPull')
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: web.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Existing StockResearch deployment identity; grant access only to the NEW group.
resource deployer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, 'bd15c91e-8451-487c-89b7-13992d5e240c', 'Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
    principalId: 'bd15c91e-8451-487c-89b7-13992d5e240c'
    principalType: 'ServicePrincipal'
  }
}

output hostname string = web.properties.defaultHostName
