# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
import yaml
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    OpenApiTool, OpenApiManagedAuthDetails, OpenApiManagedSecurityScheme
)
from utils import bind_parameters, get_clu_intents, get_cqa_questions

ENV_FILE = os.environ.get('ENV_FILE')
DELETE_OLD_AGENTS = os.environ.get('DELETE_OLD_AGENTS', 'false').lower() == 'true'
AGENTS_PROJECT_ENDPOINT = os.environ.get('AGENTS_PROJECT_ENDPOINT')
AGENTS_API_VERSION = '2025-05-15-preview'
AGENTS_MODEL_NAME = os.environ.get('AOAI_DEPLOYMENT')
AGENTS_CONFIG_FILE = 'agents_config.yaml'

# Create agents client:
AGENTS_CLIENT = AgentsClient(
    endpoint=AGENTS_PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
    api_version=AGENTS_API_VERSION
)


def create_agent(agent_config: dict, parameters: dict):
    # Authentication details for OpenAPI connection:
    auth = OpenApiManagedAuthDetails(
        security_scheme=OpenApiManagedSecurityScheme(
            audience="https://cognitiveservices.azure.com/"
        )
    )

    # Create OpenAPI tools:
    tools = []
    for tool in agent_config.openapi_tools:
        with open(f'openapi_specs/{tool.spec}', 'r') as fp:
            spec = json.loads(bind_parameters(fp.read(), parameters))
        tool = OpenApiTool(
            name=tool.name,
            spec=spec,
            description=tool.description,
            auth=auth
        )
        tools.append(tool)

    # Generate instructions:
    instructions = bind_parameters(agent_config['instructions'], parameters)

    if DELETE_OLD_AGENTS:
        # Delete all existing agents with the same target name:
        to_delete = [
            agent for agent in AGENTS_CLIENT.list_agents() if agent.name == agent_config.name
        ]
        for agent in to_delete:
            print(f"Deleting existing agent: {agent.id}")
            AGENTS_CLIENT.delete_agent(agent.id)

    # Create agent:
    agent = AGENTS_CLIENT.create_agent(
        model=AGENTS_MODEL_NAME,
        name=agent_config.name,
        instructions=instructions,
        tools=[tool_def for tool in tools for tool_def in tool.definitions]
    )

    print(f'Agent created: {agent_config.name}, {agent.id}')

    # Update env file:
    with open(ENV_FILE, 'a') as fp:
        fp.write(f'export {agent_config.env_var}="{agent.id}"\n')


# Fetch agents config:
with open(AGENTS_CONFIG_FILE, 'r') as fp:
    agents_config = yaml.safe_load(fp)

# Create Triage Agent:
print('Creating Triage Agent...')
triage_agent_parameters = {
    'clu_example_intents': ', '.join(get_clu_intents()),
    'cqa_example_questions': ', '.join(get_cqa_questions())
}
create_agent(agents_config.triage_agent, triage_agent_parameters)

# Cleanup:
AGENTS_CLIENT.close()
