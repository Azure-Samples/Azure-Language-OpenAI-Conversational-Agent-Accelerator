# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
from azure.identity import DefaultAzureCredential
from azure.ai.language.conversations.authoring import ConversationAuthoringClient


project_name = os.environ['ORCHESTRATION_PROJECT_NAME']
model_name = os.environ['ORCHESTRATION_MODEL_NAME']
deployment_name = os.environ['ORCHESTRATION_DEPLOYMENT_NAME']

clu_project_name = os.environ['CLU_PROJECT_NAME']
clu_deployment_name = os.environ['CLU_DEPLOYMENT_NAME']
cqa_project_name = os.environ['CQA_PROJECT_NAME']

endpoint = os.environ['LANGUAGE_ENDPOINT']
credential = DefaultAzureCredential()

client = ConversationAuthoringClient(endpoint, credential)

# Import project data:
print('Importing Orchestration project...')

import_file = 'orchestration_import.json'
with open(import_file, 'r') as fp:
    project_json = json.load(fp)

project_json['metadata']['projectName'] = project_name

# Link CLU/CQA projects:
clu_intent = project_json["assets"]["intents"][0]
cqa_intent = project_json["assets"]["intents"][1]
clu_intent["orchestration"]["conversationOrchestration"]["projectName"] = clu_project_name
clu_intent["orchestration"]["conversationOrchestration"]["deploymentName"] = clu_deployment_name
cqa_intent["orchestration"]["questionAnsweringOrchestration"]["projectName"] = cqa_project_name

poller = client.begin_import_project(
    project_name=project_name,
    project=project_json
)

response = poller.result()
print(response)

# Check trained models:
print('Checking trained Orchestration models...')

models = client.list_trained_models(
    project_name=project_name
)

model_names = [model['label'] for model in models]

if model_name not in model_names:
    # Train model:
    print('Training Orchestration model...')

    poller = client.begin_train(
        project_name=project_name,
        configuration={
            'modelLabel': model_name,
            'trainingMode': 'standard'
        }
    )

    response = poller.result()
    print(response)
else:
    print(f"Model {model_name} already trained.")

# Check deployments:
print('Checking Orchestration deployments...')

deployments = client.list_deployments(
    project_name=project_name
)

deployment_names = [dep['deploymentName'] for dep in deployments]

if deployment_name not in deployment_names:
    # Deploy model:
    print('Deploying Orchestration model...')

    poller = client.begin_deploy_project(
        project_name=project_name,
        deployment_name=deployment_name,
        deployment={
            'trainedModelLabel': model_name
        }
    )

    response = poller.result()
    print(response)
else:
    print(f"Deployment {model_name} already deployed.")
