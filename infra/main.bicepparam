using 'main.bicep'

param router_type = readEnvironmentVariable('AZD_PARAM_ROUTER_TYPE', 'TRIAGE_AGENT')

param gpt_model_name = readEnvironmentVariable('AZD_PARAM_GPT_MODEL_NAME', 'gpt-4o-mini')
param gpt_deployment_type = readEnvironmentVariable('AZD_PARAM_GPT_MODEL_DEPLOYMENT_TYPE', 'GlobalStandard')
param gpt_deployment_capacity = int(readEnvironmentVariable('AZD_PARAM_GPT_MODEL_CAPACITY', '100'))

param embedding_model_name = readEnvironmentVariable('AZD_PARAM_EMBEDDING_MODEL_NAME', 'text-embedding-ada-002')
param embedding_deployment_type = readEnvironmentVariable('AZD_PARAM_EMBEDDING_MODEL_DEPLOYMENT_TYPE', 'GlobalStandard')
param embedding_deployment_capacity = int(readEnvironmentVariable('AZD_PARAM_EMBEDDING_MODEL_CAPACITY', '100'))
