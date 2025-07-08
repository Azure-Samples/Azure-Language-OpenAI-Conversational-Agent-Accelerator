# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
import yaml
from azure.identity import AzureCliCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    OpenApiTool, OpenApiManagedAuthDetails, OpenApiManagedSecurityScheme
)
from utils import camel_to_snake, bind_parameters, get_clu_intents, get_cqa_questions

ENV_FILE = os.environ.get('ENV_FILE')
DELETE_OLD_AGENTS = os.environ.get('DELETE_OLD_AGENTS', 'false').lower() == 'true'
AGENTS_PROJECT_ENDPOINT = os.environ.get('AGENTS_PROJECT_ENDPOINT')
AGENTS_API_VERSION = '2025-05-15-preview'
AGENTS_MODEL_NAME = os.environ.get('AOAI_DEPLOYMENT')
AGENTS_CONFIG_FILE = 'agents_config.yaml'

# Create agents client:
AGENTS_CLIENT = AgentsClient(
    endpoint=AGENTS_PROJECT_ENDPOINT,
    credential=AzureCliCredential(),
    api_version=AGENTS_API_VERSION
)


def create_agent(agent_config: dict, parameters: dict = {}):
    # Authentication details for OpenAPI connection:
    auth = OpenApiManagedAuthDetails(
        security_scheme=OpenApiManagedSecurityScheme(
            audience="https://cognitiveservices.azure.com/"
        )
    )

    # Create OpenAPI tools:
    tools = []
    for tool in agent_config['openapi_tools']:
        with open(f'openapi_specs/{tool['spec']}', 'r') as fp:
            spec = json.loads(bind_parameters(fp.read(), parameters))
        tools.append(OpenApiTool(
            name=tool['name'],
            spec=spec,
            description=tool['description'],
            auth=auth
        ))
    tool_defs = None if not tools else [
        tool_def for tool in tools for tool_def in tool.definitions
    ]

    # Generate instructions:
    instructions = bind_parameters(agent_config['instructions'], parameters)

    # Create agent:
    agent = AGENTS_CLIENT.create_agent(
        model=AGENTS_MODEL_NAME,
        name=agent_config['name'],
        instructions=instructions,
        tools=tool_defs,
        temperature=0.2
    )

    print(f'Agent created: {agent_config['name']}, {agent.id}')

    # Update env file:
    with open(ENV_FILE, 'a') as fp:
        fp.write(f'export {agent_config['env_var']}="{agent.id}"\n')


if DELETE_OLD_AGENTS:
    print("Deleting all existing agents in project...")
    to_delete = [agent for agent in AGENTS_CLIENT.list_agents()]
    for agent in to_delete:
        print(f"Deleting agent {agent.name}: {agent.id}")
        AGENTS_CLIENT.delete_agent(agent.id)

# Fetch agents config:
with open(AGENTS_CONFIG_FILE, 'r') as fp:
    agents_config = yaml.safe_load(fp)

# Query language projects for context:
clu_intents = get_clu_intents()
cqa_questions = get_cqa_questions()

# Create TriageAgent:
print('Creating Triage Agent...')
triage_agent_parameters = {
    'clu_example_intents': ', '.join(clu_intents),
    'cqa_example_questions': ', '.join(cqa_questions)
}
create_agent(agents_config['triage'], triage_agent_parameters)

# Create HeadSupportAgent (CLU custom intent routing):
head_support_agent_parameters = {
    'custom_intent_agent_names': ', '.join(
            [f'{intent}Agent' for intent in clu_intents]
        )
}
create_agent(agents_config['head_support'], head_support_agent_parameters)

# Create custom intent agents:
for agent_key in [camel_to_snake(intent) for intent in clu_intents]:
    create_agent(agents_config[agent_key])

# Cleanup:
AGENTS_CLIENT.close()
