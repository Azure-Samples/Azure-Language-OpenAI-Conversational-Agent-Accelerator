import json
import os
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import OpenApiTool, OpenApiManagedAuthDetails,OpenApiManagedSecurityScheme
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from utils import bind_parameters

config = {}

DELETE_OLD_AGENTS = os.environ.get("DELETE_OLD_AGENTS", "false").lower() == "true"
PROJECT_ENDPOINT = os.environ.get("AGENTS_PROJECT_ENDPOINT")
MODEL_NAME = os.environ.get("AOAI_DEPLOYMENT")

config['language_resource_url'] = os.environ.get("LANGUAGE_ENDPOINT")
config['clu_project_name'] = os.environ.get("CLU_PROJECT_NAME")
config['clu_deployment_name'] = os.environ.get("CLU_DEPLOYMENT_NAME")
config['cqa_project_name'] = os.environ.get("CQA_PROJECT_NAME")
config['cqa_deployment_name'] = os.environ.get("CQA_DEPLOYMENT_NAME")


# Create agent client
agents_client = AgentsClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
    api_version="2025-05-15-preview"
)

# Set up the auth details for the OpenAPI connection
auth = OpenApiManagedAuthDetails(security_scheme=OpenApiManagedSecurityScheme(audience="https://cognitiveservices.azure.com/"))

# Read in the OpenAPI spec from a file
with open("clu.json", "r") as f:
    clu_openapi_spec = json.loads(bind_parameters(f.read(), config))

clu_api_tool = OpenApiTool(
    name="clu_api",
    spec=clu_openapi_spec,
    description= "An API to extract intent from a given message",
    auth=auth
)

# Read in the OpenAPI spec from a file
with open("cqa.json", "r") as f:
    cqa_openapi_spec = json.loads(bind_parameters(f.read(), config))

# Initialize an Agent OpenApi tool using the read in OpenAPI spec
cqa_api_tool = OpenApiTool(
    name="cqa_api",
    spec=cqa_openapi_spec,
    description= "An API to get answer to questions related to business operation",
    auth=auth
)

# Create an Agent with OpenApi tool and process Agent run
with agents_client:
    # Define agent name constant
    AGENT_NAME = "Intent Routing Agent"

    # Define the instructions for the agent
    instructions = """
        You are a triage agent. Your goal is to answer questions and redirect message according to their intent. You have at your disposition 2 tools but can only use ONE:
        1. cqa_api: to answer customer questions such as procedures and FAQs.
        2. clu_api: to extract the intent of the message.
        You must use the ONE of the tools to perform your task. You should only use one tool at a time, and do NOT chain the tools together. Only if the tools are not able to provide the information, you can answer according to your general knowledge. You must return the full API response for either tool and ensure it's a valid JSON.
        - When you return answers from the clu_api, format the response as JSON: {"type": "clu_result", "response": {clu_response}}, where clu_response is the full JSON API response from the clu_api without rewriting or removing any info.   Return immediately. Do not call the cqa_api afterwards.
          To call the clu_api, the following parameters values should be used in the payload:
            - 'projectName': value must be 'conv-assistant-clu'
            - 'deploymentName': value must be 'clu-m1-d1'
            - 'text': must be the input from the user.
            - 'api-version': must be "2023-04-01"
        - When you return answers from the cqa_api, format the response as JSON: {"type": "cqa_result", "response": {cqa_response}} where cqa_response is the full JSON API response from the cqa_api without rewriting or removing any info. Return immediately
        """

    instructions = bind_parameters(instructions, config)

    # Flag to determine if old agents should be deleted
    DELETE_OLD_AGENTS = os.environ.get("DELETE_OLD_AGENTS", "false").lower() == "true"

    if DELETE_OLD_AGENTS:
        # List all existing agents
        existing_agents = agents_client.list_agents()

        # Delete all old agents with the same target name to avoid inconsistencies
        for agent in existing_agents:
            if agent.name == AGENT_NAME:
                print(f"Deleting existing agent with ID: {agent.id}")
                agents_client.delete_agent(agent.id)
                print(f"Deleted agent with ID: {agent.id}")

    # Create the agent
    agent = agents_client.create_agent(
        model=MODEL_NAME,
        name=AGENT_NAME,
        instructions=instructions,
        tools=cqa_api_tool.definitions + clu_api_tool.definitions
    )

    print(f"Created agent, ID: {agent.id}")

    # Output the agent ID to be captured as env variable
    print(agent.id)
    