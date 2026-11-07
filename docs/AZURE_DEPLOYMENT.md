# SliverSystem Azure deployment

This deploys to a separate Linux App Service in the same subscription and region as StockResearch. StockResearch source, app, hosting plan and existing identity trust are not changed.

## Resources

- Subscription: `395e1b4f-f9e3-447c-b4ac-36fe31e2229d`
- Region: `canadacentral`
- Resource group: `SliverSystem-RG`
- Dedicated B1 plan: `SliverSystem-Plan`
- App: `sliversystem-dg395e`
- Private Basic registry: `sliversystemdg395e`

B1 compute and Basic registry incur ongoing charges. Python 3.11, Gunicorn and Chromium are installed in the existing Dockerfile. Port 10000 is explicitly configured on both sides. No persistent application database is required.

## Authentication

StockResearch production uses `azure/login@v2` and OIDC with client ID `309959b6-4118-49b9-ad74-bbea01f6ced3`, tenant `a41dbdf5-254d-4350-970a-4f773b229683`. These IDs are not secrets. SliverSystem reuses that identity with an additional main-branch trust and Contributor on its own new resource group. The app pulls images with its own managed identity and AcrPull; registry passwords are disabled.

Reusing an identity means its existing StockResearch app permissions are also available to a trusted SliverSystem deployment job. The workflow fixes its target to SliverSystem and never modifies StockResearch. A separate deployment identity is required if identity-level isolation is desired.

## One-time provisioning (Azure CLI, from repository root)

```powershell
az login
az account set --subscription 395e1b4f-f9e3-447c-b4ac-36fe31e2229d
az provider register --namespace Microsoft.ContainerRegistry --wait
az bicep install
az deployment sub validate --location canadacentral --template-file infra/main.bicep --output none
az deployment sub what-if --location canadacentral --template-file infra/main.bicep
az deployment sub create --name sliversystem-initial --location canadacentral --template-file infra/main.bicep --output none
az ad app federated-credential create --id 309959b6-4118-49b9-ad74-bbea01f6ced3 --parameters infra/github-federation.json --output none
```

The template is for initial provisioning: rerunning it resets the image to `initial`, app settings and Flask session key. For application releases, run the workflow instead. It builds a commit-tagged image, deploys by digest, then checks `/api/health` for the exact revision and verifies `/`.

GitHub repositories using immutable OIDC subjects require `repo:rihitgandhi@170836026/SliverSystem@805940310:ref:refs/heads/main` instead. Check the repository's Actions OIDC settings or the login error's subject before updating only the SliverSystem federation. Do not alter StockResearch's federation.

## Deploy and verify

Push to `main`, or select **Actions > Deploy SliverSystem App Service > Run workflow** on `main`. The other legacy deployment workflows are manual-only. No repository secrets or variables are required for Azure login.

```powershell
gh workflow run deploy-sliversystem.yml --repo rihitgandhi/SliverSystem --ref main
gh run list --repo rihitgandhi/SliverSystem --workflow deploy-sliversystem.yml
Invoke-RestMethod https://sliversystem-dg395e.azurewebsites.net/api/health
```

Azure OpenAI features additionally require `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, and `AZURE_OPENAI_API_KEY` in the NEW app's environment settings. Set keys through Azure Portal without pasting them into logs, source or chat. Without these settings, the site and local accessibility checks work; AI features report unavailable. The infrastructure generates a separate secure Flask session key; no StockResearch secret is read or copied.

For rollback, configure this app to a previously verified image digest in its registry and restart it. Never retag or overwrite an existing release image.
