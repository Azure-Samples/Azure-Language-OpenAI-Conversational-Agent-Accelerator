# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
from azure.identity import DefaultAzureCredential
from azure.ai.language.conversations.authoring import ConversationAuthoringClient


project_name = os.environ['CLU_PROJECT_NAME']
model_name = os.environ['CLU_MODEL_NAME']
deployment_name = os.environ['CLU_DEPLOYMENT_NAME']

endpoint = os.environ['LANGUAGE_ENDPOINT']
credential = DefaultAzureCredential()

client = ConversationAuthoringClient(endpoint, credential)

# Import project data:
print('Importing CLU project...')

import_file = 'clu_import.json'
with open(import_file, 'r') as fp:
    project_json = json.load(fp)

project_json['metadata']['projectName'] = project_name

poller = client.begin_import_project(
    project_name=project_name,
    project=project_json
)

response = poller.result()
print(response)

# Check trained models:
print('Checking trained CLU models...')

models = client.list_trained_models(
    project_name=project_name
)

model_names = [model['label'] for model in models]

if model_name not in model_names:
    # Train model:
    print('Training CLU model...')

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
print('Checking CLU deployments...')

deployments = client.list_deployments(
    project_name=project_name
)

deployment_names = [dep['deploymentName'] for dep in deployments]

if deployment_name not in deployment_names:
    # Deploy model:
    print('Deploying CLU model...')

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
