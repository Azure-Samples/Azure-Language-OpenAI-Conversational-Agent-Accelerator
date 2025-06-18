import json
from azure.ai.agents.models import OpenApiTool
from utils import bind_parameters

def get_openapi_tool(filename, name, description, config, auth):
    with open(filename, "r") as f:
        spec = json.loads(bind_parameters(f.read(), config))
    return OpenApiTool(
        name=name,
        spec=spec,
        description=description,
        auth=auth
    )

def get_triage_instructions(config):
    triage_instructions = """
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
    return bind_parameters(triage_instructions, config)

async def create_triage_agent(agents_client, model_name, triage_instructions, cqa_api_tool, clu_api_tool):
    TRIAGE_AGENT_NAME = "Intent Routing Agent"
    return await agents_client.agents.create_agent(
        model=model_name,
        name=TRIAGE_AGENT_NAME,
        instructions=triage_instructions,
        tools=cqa_api_tool.definitions + clu_api_tool.definitions
    )
