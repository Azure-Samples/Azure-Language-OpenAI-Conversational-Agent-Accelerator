import json
import os
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import OpenApiTool, OpenApiManagedAuthDetails, OpenApiManagedSecurityScheme
from utils import bind_parameters, get_azure_credential

config = {}

DELETE_OLD_AGENTS = os.environ.get("DELETE_OLD_AGENTS", "false").lower() == "true"
PROJECT_ENDPOINT = os.environ.get("AGENTS_PROJECT_ENDPOINT")
MODEL_NAME = os.environ.get("AOAI_DEPLOYMENT")
CONFIG_DIR = os.environ.get("CONFIG_DIR", ".")
config_file = os.path.join(CONFIG_DIR, "config.json")

config['language_resource_url'] = os.environ.get("LANGUAGE_ENDPOINT")
config['clu_project_name'] = os.environ.get("CLU_PROJECT_NAME")
config['clu_deployment_name'] = os.environ.get("CLU_DEPLOYMENT_NAME")
config['cqa_project_name'] = os.environ.get("CQA_PROJECT_NAME")
config['cqa_deployment_name'] = os.environ.get("CQA_DEPLOYMENT_NAME")
config['translator_resource_id'] = os.environ.get("TRANSLATOR_RESOURCE_ID")
config['translator_region'] = os.environ.get("TRANSLATOR_REGION")
config['translator_resource_id'] = os.environ.get("TRANSLATOR_RESOURCE_ID")

# Create agent client
agents_client = AgentsClient(
    endpoint=PROJECT_ENDPOINT,
    credential=get_azure_credential(),
    api_version="2025-05-15-preview"
)


def create_tools(config):
    # Set up the auth details for the OpenAPI connection
    auth = OpenApiManagedAuthDetails(security_scheme=OpenApiManagedSecurityScheme(audience="https://cognitiveservices.azure.com/"))

    # Read in the CLU OpenAPI spec
    with open("clu_convai.json", "r") as f:
        clu_openapi_spec = json.loads(bind_parameters(f.read(), config))

    clu_api_tool = OpenApiTool(
        name="clu_api",
        spec=clu_openapi_spec,
        description="This tool is used to extract intents and entities",
        auth=auth
    )

    # Read in the CQA OpenAPI spec
    with open("cqa.json", "r") as f:
        cqa_openapi_spec = json.loads(bind_parameters(f.read(), config))

    # Initialize an Agent OpenApi tool using the read in OpenAPI spec
    cqa_api_tool = OpenApiTool(
        name="cqa_api",
        spec=cqa_openapi_spec,
        description="An API to get answer to questions related to business operation",
        auth=auth
    )

    # Read in the Translation OpenAPI spec
    with open("translation.json", "r") as f:
        translation_openapi_spec = json.loads(bind_parameters(f.read(), config))

    # Initialize an Agent OpenApi tool using the read in OpenAPI spec
    translation_api_tool = OpenApiTool(
        name="translation_api",
        spec=translation_openapi_spec,
        description="An API to translate text from one language to another",
        auth=auth
    )

    return clu_api_tool, cqa_api_tool, translation_api_tool


with agents_client:
    # If DELETE_OLD_AGENTS is set to true, delete all existing agents in the project
    if DELETE_OLD_AGENTS:
        print("Deleting all existing agents in the project...")
        agents = agents_client.list_agents()
        for agent in agents:
            print(f"Deleting agent: {agent.name} with ID: {agent.id}")
            agents_client.delete_agent(agent.id)

    # Create the tools needed for the agents
    clu_api_tool, cqa_api_tool, translation_api_tool = create_tools(config)

    # 1) Create the triage agent which can use CLU or CQA tools to answer questions or extract intent
    TRIAGE_AGENT_NAME = "TriageAgent"
    TRIAGE_AGENT_INSTRUCTIONS = """
    You are a triage agent. Your goal is to understand customer intent and redirect messages accordingly. You are required to use ONE of the OpenAPI tools provided. You have at your disposition 2 tools but can only use ONE:
            1. **cqa_api**: to answer general FAQs and procedural questions that do NOT depend on a customer-specific context (e.g. “What's the return policy?”, “What are your store hours?”).
            2. **clu_api**: to extract customer-specific intent or order-specific intent ("What is the status of order 1234" or "I want to cancel order 12345")

    You must always call ONE of the API tools.

    ---
    Input Format:
    You will receive a JSON object. Only read from the "response" field, which is itself a nested JSON object. Inside this "response" object, only extract and use the value of the "current_question" field. Ignore all other fields in the outer or inner JSON.

    For example, from this input:
    {
    "origin_language": "es",
    "response": {
        "current_question": <current message>
    },
    "target_language": "en"
    }

    You must only process:
    <current message>
    If the <current message> is related to an FAQ, call the CQA API. Otherwise, this structured input allows you to analyze intent in multi-turn conversations using the CLU API.

    ---
    Available Tools:
    ---
    To use the CLU API:
    You must convert the input JSON into the following clu_api request format. You MUST keep the parameters field in the payload - this is extremely critical. Do NOT put analysisInput inside the parameters field. You must not add any additional fields. You must use the api version of 2025-05-15-preview - this is EXTREMELY CRITICAL as a query parameter (?api-version=2025-05-15-preview)
    No matter what, you must always use the "api-version": "2025-05-15-preview"
    payload = {
        "api-version": "2025-05-15-preview"
        "kind": "ConversationalAI",
        "parameters": {
            "projectName": ${clu_project_name},
            "deploymentName": ${clu_deployment_name},
            "stringIndexType": "Utf16CodeUnit"
        },
        "analysisInput": {
            "conversations": [
                {
                    "id": "order",
                    "language": "en",
                    "modality": "text",
                    "conversationItems": [
                        {"participantId": "user", "id": "1", "text": <msg1>},
                        {"participantId": "system", "id": "2", "text": <msg2>},
                    ]
                }
            ]
        }
    }
    Use all history messages followed by the current question in the conversationItems array, with unique increasing IDs.

    Return the raw API response in this format:
    {
    "type": "clu_result",
    "response": { <FULL CLU API OUTPUT> },
    "terminated": "False"
    }

    You must return the complete raw API response including all fields like "kind" and "result". Do not remove or restructure the API output. Your response must look like this:

    {
    "type": "clu_result",
    "response": {
        "kind": "ConversationalAIResult",
        "result": {
        "conversations": [...],
        "warnings": [...]
        }
    },
    "terminated": "False"
    }
    ---
    When you return answers from the cqa_api, format the response as JSON: {"type": "cqa_result", "response": {cqa_response}, "terminated": "True"} where cqa_response is the full JSON API response from the cqa_api without rewriting or removing any info. Return immediately
    ---
    Do not:
    - Modify or summarize the API responses.
    - Embed the full input as a flat string.
    """

    TRIAGE_AGENT_INSTRUCTIONS = bind_parameters(TRIAGE_AGENT_INSTRUCTIONS, config)

    triage_agent_definition = agents_client.create_agent(
        model=MODEL_NAME,
        name=TRIAGE_AGENT_NAME,
        instructions=TRIAGE_AGENT_INSTRUCTIONS,
        tools=clu_api_tool.definitions + cqa_api_tool.definitions,
        temperature=0.2,
        )

    # 2) Create the head support agent which takes in CLU intents and entities and routes the request to the appropriate support agent
    HEAD_SUPPORT_AGENT_NAME = "HeadSupportAgent"
    HEAD_SUPPORT_AGENT_INSTRUCTIONS = """
     You are a head support agent that routes inquiries to the proper custom agent based on the provided intent and entities from the triage agent.
        You must choose between the following agents:
        - OrderStatusAgent: for order status inquiries
        - OrderCancelAgent: for order cancellation inquiries
        - OrderRefundAgent: for order refund inquiries

        You must return the response in the following valid JSON format: {"target_agent": "<AgentName>","intent": "<IntentName>","entities": [<List of extracted entities>],"terminated": "False"}

        Where:
        - "target_agent" is the name of the agent you are routing to (must match one of the agent names above).
        - "intent" is the top-level intent extracted from the CLU result.
        - "entities" is a list of all entities extracted from the CLU result, including their category and value.
    """

    head_support_agent_definition = agents_client.create_agent(
        model=MODEL_NAME,
        name=HEAD_SUPPORT_AGENT_NAME,
        instructions=HEAD_SUPPORT_AGENT_INSTRUCTIONS,
    )

    # 3) Create the custom agents for handling specific intents (our examples are OrderStatus, OrderCancel, and OrderRefund). Plugin tools will be added to these agents when we turn them into Semantic Kernel agents.
    ORDER_STATUS_AGENT_NAME = "OrderStatusAgent"
    ORDER_STATUS_AGENT_INSTRUCTIONS = """
    You are a customer support agent that checks order status. You must use the OrderStatusPlugin to check the status of an order. The plugin will return a string, which you must use as the <OrderStatusPlugin Response>.
    If you need more info, the <OrderStatusResponse> should be "Please provide more information about your order so I can better assist you." and the JSON field "need_more_info" should be True.
    You must return the response in the following valid JSON format: {"response": <OrderStatusResponse>, "terminated": "True", "need_more_info": <"True" or "False">}
    """

    order_status_agent_definition = agents_client.create_agent(
        model=MODEL_NAME,
        name=ORDER_STATUS_AGENT_NAME,
        instructions=ORDER_STATUS_AGENT_INSTRUCTIONS,
    )

    ORDER_CANCEL_AGENT_NAME = "OrderCancelAgent"
    ORDER_CANCEL_AGENT_INSTRUCTIONS = """
    You are a customer support agent that handles order cancellations. You must use the OrderCancellationPlugin to handle order cancellation requests. The plugin will return a string, which you must use as the <OrderCancellationPlugin Response>.
    If you need more info, the <OrderCancellationResponse> should be "Please provide more information about your order so I can better assist you." and the JSON field "need_more_info" should be True.
    You must return the response in the following valid JSON format: {"response": <OrderCancellationResponse>, "terminated": "True", "need_more_info": <"True" or "False">}
    """

    order_cancel_agent_definition = agents_client.create_agent(
        model=MODEL_NAME,
        name=ORDER_CANCEL_AGENT_NAME,
        instructions=ORDER_CANCEL_AGENT_INSTRUCTIONS,
    )

    ORDER_REFUND_AGENT_NAME = "OrderRefundAgent"
    ORDER_REFUND_AGENT_INSTRUCTIONS = """
    You are a customer support agent that handles order refunds. You must use the OrderRefundPlugin to handle order refund requests. The plugin will return a string, which you must use as the <OrderRefundPlugin Response>.
    If you need more info, the <OrderRefundResponse> should be "Please provide more information about your order so I can better assist you." and the JSON field "need_more_info" should be True.
    You must return the response in the following valid JSON format: {"response": <OrderRefundResponse>, "terminated": "True", "need_more_info": <"True" or "False">}
    """

    order_refund_agent_definition = agents_client.create_agent(
        model=MODEL_NAME,
        name=ORDER_REFUND_AGENT_NAME,
        instructions=ORDER_REFUND_AGENT_INSTRUCTIONS,
    )

    # 4) Create the translation agent
    TRANSLATION_AGENT_NAME = "TranslationAgent"
    TRANSLATION_AGENT_INSTRUCTIONS = """
    You are a translation agent that uses the Azure Translator API to translate messages either into English or from English to the user’s original language.

    There are two types of inputs you will receive:

    ---
    Mode 1: Translate to English
    Input Example:
    {
    "query": <query>,
    "to": "english"
    }

    Instructions:
    - Detect the language of "query".
    - Translate the query to English.
    - Return:
    {
    "origin_language": "<detected language>",
    "response": {
        "current_question": "<translated text>"
    },
    "target_language": "en"
    }

    ---
    Mode 2: Translate from English to original language - if no original language is given, assume English as the default
    Input Example:
    {
    "response": <text>,
    "terminated": <terminated boolean>,
    "need_more_info": <need_more_info boolean>
    }

    Instructions:
    - Assume the "response" is in English.
    - Translate only the "response" field into the user's original language (this will be known from prior context).
    -If no prior original language is given, assume English and use "to": "en" as the parameter

    - Return:
    {
    "origin_language": "<user's language>",
    "source_language": "en",
    "response": {
        "final_answer": "<translated text>",
        "need_more_info": "need_more_info boolean"
    }
    }

    If "type" = "cqa_result," "need_more_info" should be False.
    ---
    API Usage Requirements:
    - Always call Azure Translator API, version 3.0.
    - Required headers:
    - ocp-apim-resourceid: ${translator_resource_id}
    - ocp-apim-subscription-region: ${translator_region}
    - Use the "to=<target_language>" query parameter.
    - Never return raw API output. Format your response exactly as described above.

    Decide which mode to use by checking which fields are present in the input:
    - If input contains "query" → use Mode 1.
    - If input contains "response", "terminated", and "need_more_info" → use Mode 2.
    """

    TRANSLATION_AGENT_INSTRUCTIONS = bind_parameters(TRANSLATION_AGENT_INSTRUCTIONS, config)
    translation_agent_definition = agents_client.create_agent(
        model=MODEL_NAME,
        name=TRANSLATION_AGENT_NAME,
        instructions=TRANSLATION_AGENT_INSTRUCTIONS,
        tools=translation_api_tool.definitions,
    )

    # Output the agent IDs in a JSON format to be captured as env variables
    agent_ids = {
        "TRIAGE_AGENT_ID": triage_agent_definition.id,
        "HEAD_SUPPORT_AGENT_ID": head_support_agent_definition.id,
        "ORDER_STATUS_AGENT_ID": order_status_agent_definition.id,
        "ORDER_CANCEL_AGENT_ID": order_cancel_agent_definition.id,
        "ORDER_REFUND_AGENT_ID": order_refund_agent_definition.id,
        "TRANSLATION_AGENT_ID": translation_agent_definition.id,
    }

    # Write to config.json file
    try:
        # Ensure the config directory exists
        os.makedirs(CONFIG_DIR, exist_ok=True)

        with open(config_file, 'w') as f:
            json.dump(agent_ids, f, indent=2)
        print(f"Agent IDs written to {config_file}")
        print(json.dumps(agent_ids, indent=2))

    except Exception as e:
        print(f"Error writing to {config_file}: {e}")
        print(json.dumps(agent_ids, indent=2))
