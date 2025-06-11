using 'main.bicep'

param router_type = readEnvironmentVariable('AZURE_ENV_ROUTER_TYPE', 'TRIAGE_AGENT')

param gpt_model_name = readEnvironmentVariable('AZURE_ENV_GPT_MODEL_NAME', 'gpt-4o-mini')
param gpt_deployment_capacity = int(readEnvironmentVariable('AZURE_ENV_GPT_MODEL_CAPACITY', '100'))
param gpt_deployment_type = readEnvironmentVariable('AZURE_ENV_GPT_MODEL_DEPLOYMENT_TYPE', 'GlobalStandard')

param embedding_model_name = readEnvironmentVariable('AZURE_ENV_EMBEDDING_MODEL_NAME', 'text-embedding-ada-002')
param embedding_deployment_capacity = int(readEnvironmentVariable('AZURE_ENV_EMBEDDING_MODEL_CAPACITY', '100'))
param embedding_deployment_type = readEnvironmentVariable('AZURE_ENV_EMBEDDING_MODEL_DEPLOYMENT_TYPE', 'GlobalStandard')
