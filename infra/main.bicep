targetScope = 'subscription'

param location string = 'canadacentral'
@secure()
param flaskSecret string = newGuid()

resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'SliverSystem-RG'
  location: location
}

module app './resources.bicep' = {
  name: 'sliversystem-resources'
  scope: group
  params: {
    location: location
    flaskSecret: flaskSecret
  }
}

output hostname string = app.outputs.hostname
