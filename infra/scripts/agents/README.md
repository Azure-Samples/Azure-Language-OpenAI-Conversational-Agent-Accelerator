# Conversational-Agent: Agents Setup

## Environment Variables
Expected environment variables:
```
ENV_FILE=<path-to-env-file>
DELETE_OLD_AGENTS=<should-old-agents-be-deleted>
AGENTS_PROJECT_ENDPOINT=<foundry-agents-project-endpoint>
AOAI_DEPLOYMENT=<aoai-gpt-deployment-name>

LANGUAGE_ENDPOINT=<language-service-endpoint>
CLU_PROJECT_NAME=<clu-project-name>
CLU_DEPLOYMENT_NAME=<clu-deployment-name>
CQA_PROJECT_NAME=<cqa-project-name>
CQA_DEPLOYMENT_NAME=production
```

## Running Setup (local)
```
az login
bash run_agents_setup.sh
```