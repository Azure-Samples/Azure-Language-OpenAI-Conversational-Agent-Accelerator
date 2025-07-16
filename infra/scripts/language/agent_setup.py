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
CONFIG_DIR = os.environ.get("CONFIG_DIR", ".")
config_file = os.path.join(CONFIG_DIR, "config.json")

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

def create_tools(config):
    # Set up the auth details for the OpenAPI connection
    auth = OpenApiManagedAuthDetails(security_scheme=OpenApiManagedSecurityScheme(audience="https://cognitiveservices.azure.com/"))

    # Read in the OpenAPI spec from a file
    with open("clu_convai.json", "r") as f:
        clu_openapi_spec = json.loads(bind_parameters(f.read(), config))

    clu_api_tool = OpenApiTool(
        name="clu_convai_api",
        spec=clu_openapi_spec,
        description= "An API to extract intent from a given message with multi-turn conversation history",
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

    return clu_api_tool, cqa_api_tool

with agents_client:
    # If DELETE_OLD_AGENTS is set to true, delete all existing agents in the project
    if DELETE_OLD_AGENTS:
        print("Deleting all existing agents in the project...")
        agents = agents_client.list_agents()
        for agent in agents:
            print(f"Deleting agent: {agent.name} with ID: {agent.id}")
            agents_client.delete_agent(agent.id)

    # 1) Create the triage agent which can use CLU or CQA tools to answer questions or extract intent
    clu_api_tool, cqa_api_tool = create_tools(config)
    TRIAGE_AGENT_NAME = "TriageAgent"
    TRIAGE_AGENT_INSTRUCTIONS = """
    You are a triage agent. Your goal is to understand customer intent and redirect messages accordingly. You are required to use ONE of the OpenAPI tools provided. You have at your disposition 2 tools but can only use ONE:
        1. **cqa_api**: to answer general FAQs and procedural questions that do NOT depend on a customer-specific context (e.g. “What's the return policy?”, “What are your store hours?”).
        2. **clu_api**: to extract customer-specific intent or order-specific intent ("What is the status of order 1234" or "I want to cancel order 12345")

    ---

    Input Format:

    You will receive input as a comma-delimited string representing a multi-turn conversation, formatted like this:

    "current question: <current message>, history: user - <msg1>, bot - <msg2>, user - <msg3>"

    If the <current message> is related to an FAQ, call the CQA API. Otherwise, this structured input allows you to analyze intent in multi-turn conversations using the CLU API.

    ---
    Available Tools:
    ---
    To use the CLU API: 
    You must convert the input JSON into the following clu_api request format. You MUST keep the parameters field in the payload - this is extremely critical. Do NOT put analysisInput inside the parameters field. You must not add any additional fields. You must use the api version of 2025-05-15-preview - this is EXTREMELY CRITICAL as a query parameter (?api-version=2025-05-15-preview)

    example payload = {
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
                        {"participantId": "user", "id": "1", "text": "Hi!"},
                        {"participantId": "bot", "id": "2", "text": "Hello, how can I help you?"},
                        {"participantId": "user", "id": "3", "text": "I want to cancel an order"},
                        {"participantId": "bot", "id": "4", "text": "Please provide your order number."},
                        {"participantId": "user", "id": "5", "text": "Order id 1234"}
                    ]
                }
            ]
        }
    }
    Use all history messages followed by the current question in the conversationItems array, with unique increasing IDs. 

    Return the raw API response in this format:

    {
    "type": "clu_result",
    "response": { <FULL CLU RESPONSE> },
    "terminated": "False"
    }
    """

    TRIAGE_AGENT_INSTRUCTIONS = bind_parameters(TRIAGE_AGENT_INSTRUCTIONS, config)

    triage_agent_definition = agents_client.create_agent(
        model=MODEL_NAME,
        name=TRIAGE_AGENT_NAME,
        instructions= TRIAGE_AGENT_INSTRUCTIONS,
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

    # Output the agent IDs in a JSON format to be captured as env variables
    agent_ids = {
        "TRIAGE_AGENT_ID": triage_agent_definition.id,
        "HEAD_SUPPORT_AGENT_ID": head_support_agent_definition.id,
        "ORDER_STATUS_AGENT_ID": order_status_agent_definition.id,
        "ORDER_CANCEL_AGENT_ID": order_cancel_agent_definition.id,
        "ORDER_REFUND_AGENT_ID": order_refund_agent_definition.id,
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
        