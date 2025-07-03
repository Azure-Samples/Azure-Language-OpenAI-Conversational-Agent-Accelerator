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
    with open("clu.json", "r") as f:
        clu_openapi_spec = json.loads(bind_parameters(f.read(), config))

    clu_api_tool = OpenApiTool(
        name="clu_api",
        spec=clu_openapi_spec,
        description= "An API to extract intent from a given message - you MUST use version \"2023-04-01\" as this is extremely critical",
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
    You are a triage agent. Your goal is to answer questions and redirect message according to their intent. You have at your disposition 2 tools but can only use ONE:
        1. cqa_api: to answer customer questions such as procedures and FAQs.
        2. clu_api: to extract the intent of the message.
        You must use the ONE of the tools to perform your task. You should only use one tool at a time, and do NOT chain the tools together. Only if the tools are not able to provide the information, you can answer according to your general knowledge. You must return the full API response for either tool and ensure it's a valid JSON.
        - When you return answers from the clu_api, format the response as JSON: {"type": "clu_result", "response": {clu_response}, "terminated": "False"}, where clu_response is the full JSON API response from the clu_api without rewriting or removing any info.   Return immediately. Do not call the cqa_api afterwards.
            - An example of a valid clu_response is {"kind": "ConversationResult", "result": {"query": "what's the status of order 1234", "prediction": {"topIntent": "OrderStatus", "projectKind": "Conversation", "intents": [{"category": "OrderStatus", "confidenceScore": 0.8545539}, {"category": "CancelOrder", "confidenceScore": 0.59596604}, {"category": "RefundStatus", "confidenceScore": 0.5501976}, {"category": "None", "confidenceScore": 0.33382362}], "entities": [{"category": "OrderId", "text": "1234", "offset": 27, "length": 4, "confidenceScore": 1, "resolutions": [{"resolutionKind": "NumberResolution", "numberKind": "Integer", "value": 1234}], "extraInformation": [{"extraInformationKind": "EntitySubtype", "value": "quantity.number"}]}]}}}
            - To call the clu_api, the following parameter values **must** be used in the payload as a valid JSON object: {"api-version":"2023-04-01", "analysisInput":{"conversationItem":{"id":<id>,"participantId":<id>,"text":<user input>}},"parameters":{"projectName":"conv-assistant-clu","deploymentName":"clu-m1-d1"},"kind":"Conversation"}
            - You must validate the input to ensure it is a valid JSON object before calling the clu_api.
        - When you return answers from the cqa_api, format the response as JSON: {"type": "cqa_result", "response": {cqa_response}, "terminated": "True"} where cqa_response is the full JSON API response from the cqa_api without rewriting or removing any info. Return immediately
    """

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
    If you need more information from the user, you must return a response with "need_more_info": "True", otherwise you must return "need_more_info": "False".
    You must return the response in the following valid JSON format: {"response": <OrderStatusPlugin Response>, "terminated": "True", "need_more_info": <"True" or "False">}
    """

    order_status_agent_definition = agents_client.create_agent(
        model=MODEL_NAME,
        name=ORDER_STATUS_AGENT_NAME,
        instructions=ORDER_STATUS_AGENT_INSTRUCTIONS,
    )

    ORDER_CANCEL_AGENT_NAME = "OrderCancelAgent"
    ORDER_CANCEL_AGENT_INSTRUCTIONS = """
    You are a customer support agent that handles order cancellations. You must use the OrderCancellationPlugin to handle order cancellation requests. The plugin will return a string, which you must use as the <OrderCancellationPlugin Response>.
    If you need more information from the user, you must return a response with "need_more_info": "True", otherwise you must return "need_more_info": "False".
    You must return the response in the following valid JSON format: {"response": <OrderCancellationPlugin Response>, "terminated": "True", "need_more_info": <"True" or "False">}
    """

    order_cancel_agent_definition = agents_client.create_agent(
        model=MODEL_NAME,
        name=ORDER_CANCEL_AGENT_NAME,
        instructions=ORDER_CANCEL_AGENT_INSTRUCTIONS,
    )

    ORDER_REFUND_AGENT_NAME = "OrderRefundAgent"
    ORDER_REFUND_AGENT_INSTRUCTIONS = """
    You are a customer support agent that handles order refunds. You must use the OrderRefundPlugin to handle order refund requests. The plugin will return a string, which you must use as the <OrderRefundPlugin Response>.
    If you need more information from the user, you must return a response with "need_more_info": "True", otherwise you must return "need_more_info": "False".
    You must return the response in the following valid JSON format: {"response": <OrderRefundPlugin Response>, "terminated": "True", "need_more_info": <"True" or "False">}
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
        