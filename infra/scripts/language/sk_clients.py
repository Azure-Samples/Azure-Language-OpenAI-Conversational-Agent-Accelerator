import os
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from dotenv import load_dotenv
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings, AgentGroupChat, GroupChatOrchestration
from semantic_kernel.agents.strategies import TerminationStrategy, SequentialSelectionStrategy
from agents.order_status_plugin import OrderStatusPlugin
from agents.order_refund_plugin import OrderRefundPlugin
from agents.order_cancel_plugin import OrderCancellationPlugin
from agents.discount_plugin import OrderDiscountPlugin
from semantic_kernel.agents.runtime import InProcessRuntime
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.contents import AuthorRole, ChatMessageContent
from semantic_kernel.agents.orchestration.group_chat import BooleanResult, GroupChatManager, MessageResult, StringResult
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.contents import AuthorRole, ChatHistory, ChatMessageContent
from utils import bind_parameters
import json
from azure.ai.agents.models import OpenApiTool, OpenApiManagedAuthDetails,OpenApiManagedSecurityScheme
import asyncio

# load environment variables
load_dotenv()

PROJECT_ENDPOINT = os.environ.get("AGENTS_PROJECT_ENDPOINT")
MODEL_NAME = os.environ.get("AOAI_DEPLOYMENT")
AOAI_ENDPOINT=os.environ.get("AOAI_ENDPOINT")
TRIAGE_AGENT_ID = os.environ.get("TRIAGE_AGENT_ID")


config = {}
config['language_resource_url'] = os.environ.get("LANGUAGE_ENDPOINT")
config['clu_project_name'] = os.environ.get("CLU_PROJECT_NAME")
config['clu_deployment_name'] = os.environ.get("CLU_DEPLOYMENT_NAME")
config['cqa_project_name'] = os.environ.get("CQA_PROJECT_NAME")
config['cqa_deployment_name'] = os.environ.get("CQA_DEPLOYMENT_NAME")

# Create chat completion service using Azure OpenAI - not using right now but good to have as reference
# chat_completion_service = AzureChatCompletion(
#     endpoint=AOAI_ENDPOINT,
#     deployment_name=MODEL_NAME,
# )
# print('successfully created chat completion service')

def create_tools(config):
    # Set up the auth details for the OpenAPI connection
    auth = OpenApiManagedAuthDetails(security_scheme=OpenApiManagedSecurityScheme(audience="https://cognitiveservices.azure.com/"))

    # Read in the OpenAPI spec from a file
    with open("../../openapi_specs/clu.json", "r") as f:
        clu_openapi_spec = json.loads(bind_parameters(f.read(), config))

    clu_api_tool = OpenApiTool(
        name="clu_api",
        spec=clu_openapi_spec,
        description= "An API to extract intent from a given message - you MUST use version \"2023-04-01\" as this is extremely critical",
        auth=auth
    )

    # Read in the OpenAPI spec from a file
    with open("../../openapi_specs/cqa.json", "r") as f:
        cqa_openapi_spec = json.loads(bind_parameters(f.read(), config))

    # Initialize an Agent OpenApi tool using the read in OpenAPI spec
    cqa_api_tool = OpenApiTool(
        name="cqa_api",
        spec=cqa_openapi_spec,
        description= "An API to get answer to questions related to business operation",
        auth=auth
    )

    return clu_api_tool, cqa_api_tool

# Create custom selection strategy for the agent groupchat by sublcassing the SequentialSelection Strategy
class SelectionStrategy(SequentialSelectionStrategy):
    async def select_agent(self, agents, history):
        """
        Select agent based on the current message and agent.
        This method overrides the default selection strategy to use a custom logic.
            - The triage agent is always selected after the user message.
            - If the triage agent returns a CQA result, the chat is terminated and the CQA result is returned.
            - If the triage agent returns a CLU result, the head support agent is selected.
            - Based on the intent and entities passed to the head support agent, the appropriate custom agent (return, refund, order status) is selected
            - The custom agent returns the result and the chat is terminated.
            - If any agents fail, the chat falls back to a default response.
        """
        last = history[-1] if history else None

        print("last message:", last)
        print("last message name:", last.name if last else None)
                
        if not last or last.role == AuthorRole.USER or last is None:
            # If the last message is from the user, select the triage agent
            print("Passing to TriageAgent")
            return next((a for a in agents if a.name == "TriageAgent"), None)
        
        elif last.name == "TriageAgent":
            print("Last message is from TriageAgent, checking content...")
            try:
                parsed = json.loads(last.content)
                print("Parsed content:", parsed)
                if parsed.get("type") == "cqa_result":
                    return None  # End early
                if parsed.get("type") == "clu_result":
                    print("Realizing intent from CLU result")
                    intent = parsed["response"]["result"]["prediction"]["topIntent"]
                    print("intent:", intent)
                    print("Passing to head agent")
                    return next((agent for agent in agents if agent.name == "HeadSupportAgent"), None)
            except Exception:
                return None

        elif last.name == "HeadSupportAgent":
            print("Last message is from HeadSupportAgent, checking content...")
            try:
                parsed = json.loads(last.content)
                print("Parsed content:", parsed)
                route = parsed.get("target_agent")
                print("Route to custom agent:", route)
                return next((a for a in agents if a.name == route), None)
            except Exception:
                return None

        return None
    

class ApprovalStrategy(TerminationStrategy):
    """
    Custom termination strategy that ends the chat if it's from the custom action agent 
    or if the triage agent returns a CQA result.
    """
    async def should_agent_terminate(self, agent, history):
        """
        Check if the agent should terminate based on the last message.
        If the last message is from the custom action agent or if the triage agent returns a CQA result, terminate.
        """
        last = history[-1] if history else None

        if not last:
            return False
        
        try:
            parsed = json.loads(last.content)
            return parsed.get("terminated") == "True" or parsed.get("need_more_info") == "True"
        except Exception:
            return False

async def get_azure_ai_agents(client, agent_ids):
    triage_agent_definition = await client.agents.get_agent(agent_ids["TRIAGE_AGENT_ID"])
    triage_agent = AzureAIAgent(
    client=client,
    definition=triage_agent_definition,
    description="A customer support agent that chooses between CLU and CQA APIs tools. The CLU API version query parameter must be '2023-04-10' - this is extremely critical",
    )

    order_status_agent_definition = await client.agents.get_agent(agent_ids["ORDER_STATUS_AGENT_ID"])
    order_status_agent = AzureAIAgent(
    client=client,
    definition=order_status_agent_definition,
    description="An agent that checks order status",
    plugins=[OrderStatusPlugin()],
    )

    order_cancel_agent_definition = await client.agents.get_agent(agent_ids["ORDER_CANCEL_AGENT_ID"])
    order_cancel_agent = AzureAIAgent(
    client=client,
    definition=order_cancel_agent_definition,
    description="An agent that checks on cancellations",
    plugins=[OrderCancellationPlugin()],
    )

    order_refund_agent_definition = await client.agents.get_agent(agent_ids["ORDER_REFUND_AGENT_ID"])
    order_refund_agent = AzureAIAgent(
    client=client,
    definition=order_refund_agent_definition,
    description="An agent that checks on refunds",
    plugins=[OrderRefundPlugin()],
    )

    head_support_agent_definition = await client.agents.get_agent(agent_ids["HEAD_SUPPORT_AGENT_ID"])
    head_support_agent = AzureAIAgent(
    client=client,
    definition=head_support_agent_definition,
    description="A head support agent that routes inquiries to the proper custom agent. Ensure you do not use any special characters in the JSON response, as this will cause the agent to fail. The response must be a valid JSON object.",
    )

    return triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent

async def create_agents(client, ai_agent_settings, config):
    # order status agent
    order_status_agent_definition = await client.agents.create_agent(
    model=ai_agent_settings.model_deployment_name,
    name="OrderStatusAgent",
    instructions="""You are a customer support agent that checks order status. You must use the OrderStatusPlugin to check the status of an order.
    If you need more information from the user, you must return a response with "need_more_info": "True", otherwise you must return "need_more_info": "False".
    You must return the response in the following valid JSON format: {"response": <OrderStatusResponse>, "terminated": "True", "need_more_info": <"True" or "False">}""",

    )

    order_status_agent = AzureAIAgent(
    client=client,
    definition=order_status_agent_definition,
    description="An agent that checks order status",
    plugins=[OrderStatusPlugin()],
    )

    # order cancel agent
    order_cancel_agent_definition = await client.agents.create_agent(
    model=ai_agent_settings.model_deployment_name,
    name="OrderCancelAgent",
    instructions="""You are a customer support agent that handles order cancellations. You must use the OrderCancellationPlugin to handle order cancellation requests.
    If you need more information from the user, you must return a response with "need_more_info": "True", otherwise you must return "need_more_info": "False".
    You must return the response in the following valid JSON format: {"response": <OrderCancellationResponse>, "terminated": "True", "need_more_info": <"True" or "False">}""",
    )

    order_cancel_agent = AzureAIAgent(
    client=client,
    definition=order_cancel_agent_definition,
    description="An agent that handles order cancellations",
    plugins=[OrderCancellationPlugin()],
    )

    # order refund agent
    order_refund_agent_definition = await client.agents.create_agent(
    model=ai_agent_settings.model_deployment_name,
    name="OrderRefundAgent",
    instructions="""You are a customer support agent that handles order refunds. You must use the OrderRefundPlugin to handle order refund requests.
    If you need more information from the user, you must return a response with "need_more_info": "True", otherwise you must return "need_more_info": "False".
    You must return the response in the following valid JSON format: {"response": <OrderRefundResponse>, "terminated": "True", "need_more_info": <"True" or "False">}""",
    )

    order_refund_agent = AzureAIAgent(
    client=client,
    definition=order_refund_agent_definition,
    description="An agent that checks on refunds",
    plugins=[OrderRefundPlugin()],
    )

    # triage agent tools
    clu_api_tool, cqa_api_tool = create_tools(config)

    triage_agent_definition = await client.agents.create_agent(
    model=ai_agent_settings.model_deployment_name,
    name="TriageAgent",
    instructions="""
    You are a triage agent. Your goal is to answer questions and redirect message according to their intent. You have at your disposition 2 tools but can only use ONE:
    1. cqa_api: to answer customer questions such as procedures and FAQs.
    2. clu_api: to extract the intent of the message.
    You must use the ONE of the tools to perform your task. You should only use one tool at a time, and do NOT chain the tools together. Only if the tools are not able to provide the information, you can answer according to your general knowledge. You must return the full API response for either tool and ensure it's a valid JSON.
    - When you return answers from the clu_api, format the response as JSON: {"type": "clu_result", "response": {clu_response}, "terminated": "False"}, where clu_response is the full JSON API response from the clu_api without rewriting or removing any info.   Return immediately. Do not call the cqa_api afterwards.
        - To call the clu_api, the following parameter values **must** be used in the payload as a valid JSON object: {"api-version":"2023-04-01", "analysisInput":{"conversationItem":{"id":<id>,"participantId":<id>,"text":<user input>}},"parameters":{"projectName":"conv-assistant-clu","deploymentName":"clu-m1-d1"},"kind":"Conversation"}
        - You must validate the input to ensure it is a valid JSON object before calling the clu_api.
    - When you return answers from the cqa_api, format the response as JSON: {"type": "cqa_result", "response": {cqa_response}, "terminated": "True"} where cqa_response is the full JSON API response from the cqa_api without rewriting or removing any info. Return immediately
    """,
    tools=clu_api_tool.definitions + cqa_api_tool.definitions,
    temperature=0.1,
    )

    triage_agent = AzureAIAgent(
    client=client,
    definition=triage_agent_definition,
    )

    # Create Head Support Agent in AI Foundry
    head_support_agent_definition = await client.agents.create_agent(
    model=ai_agent_settings.model_deployment_name,
    name="HeadSupportAgent",
    instructions="""
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
        """,
    )

    head_support_agent = AzureAIAgent(
    client=client,
    definition=head_support_agent_definition,
    )

    agent_ids = {
            "TRIAGE_AGENT_ID": triage_agent_definition.id,
            "ORDER_STATUS_AGENT_ID": order_status_agent_definition.id,
            "ORDER_CANCEL_AGENT_ID": order_cancel_agent_definition.id,
            "ORDER_REFUND_AGENT_ID": order_refund_agent_definition.id,
            "HEAD_SUPPORT_AGENT_ID": head_support_agent_definition.id,
        }

    # Output the agent IDs as JSON
    print(json.dumps(agent_ids, indent=4))

    return triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent

# sample reference for creating an Azure AI agent
async def main():
    ai_agent_settings = AzureAIAgentSettings(model_deployment_name=MODEL_NAME)
    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds, endpoint=PROJECT_ENDPOINT) as client,
    ):
        CREATE_NEW_AGENTS = False

        if CREATE_NEW_AGENTS:
            print("Creating new agents...")
            # Create the agents from scratch
            triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent = await create_agents(client, ai_agent_settings, config)
        else:
            print("Using existing agents...")
            # Get the agents from these agent IDs
            agent_ids = {
                "TRIAGE_AGENT_ID": "asst_ysqsCOGt2wjq2pdIiyUhnpr0",
                "ORDER_STATUS_AGENT_ID": "asst_OBncddlN55Dq8G13Rv5VwxQN",
                "ORDER_CANCEL_AGENT_ID": "asst_jQOhkFOs3Wh6nXJvtoJtggAq",
                "ORDER_REFUND_AGENT_ID": "asst_7KnkjOkZnZOCm5wcQW2gdPEl",
                "HEAD_SUPPORT_AGENT_ID": "asst_teR3MCcQzSOr6zQnTDsqUkOz"
            }
            triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent = await get_azure_ai_agents(client, agent_ids)


        # # create the agent group chat with all of the agents
        agent_group_chat = AgentGroupChat(
            agents=[
                triage_agent,
                head_support_agent,
                order_status_agent,
                order_cancel_agent,
                order_refund_agent,
            ],
            selection_strategy=SelectionStrategy(
                agents=[triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent]
            ),
            termination_strategy=ApprovalStrategy(
                agents=[triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent],
                maximum_iterations=10,
                automatic_reset=True,
            ),
        )
        print("Agent group chat created successfully.")

        # Process message
        user_msg = ChatMessageContent(role=AuthorRole.USER, content="I want to refund order 12389")
        await asyncio.sleep(5) # Wait to reduce TPM
        print(f"\nReady to process user message: {user_msg.content}\n")

        # Append the current log file to the chat
        await agent_group_chat.add_chat_message(user_msg)
        print()

        try:
            print()
            # Invoke a response from the agents
            async for response in agent_group_chat.invoke():
                if response is None or not response.name:
                    continue
                print(f"{response.content}")
                final_response = response.content
            
            final_response = json.loads(final_response)

            # if CQA
            if final_response.get("type") == "cqa_result":
                print("CQA result received, terminating chat.")
                final_response = final_response['response']['answers'][0]['answer']
                print("final response is ", final_response)
                return
            # if CLU
            else:
                print("CLU result received, printing custom agent response.")
                print("final response is ", final_response['response'])


            # Come back to this later for human in the loop
            # while True:
            #     async for response in agent_group_chat.invoke():
            #         if response is None or not response.name:
            #             continue
            #         print(f"{response.name}: {response.content}")

            #         # Check if the agent needs more input
            #         try:
            #             cleaned_content = response.content.replace('\n', '').strip()
                        
            #             parsed_response = json.loads(cleaned_content)
            #             if parsed_response.get("need_more_info") == "True":
            #                 # Prompt the user for additional input
            #                 user_input = input("Agent needs more information. Please provide additional input: ")
            #                 user_msg = ChatMessageContent(role=AuthorRole.USER, content=user_input)
            #                 await agent_group_chat.add_chat_message(user_msg)
            #                 break  # Break the loop to process the new user input
            #         except json.JSONDecodeError:
            #             print("Error parsing agent response. Continuing...")
            #             continue

            #     else:
            #         # If no more responses, exit the loop
            #         break

        except Exception as e:
            print(f"Error during chat invocation: {e}")

if __name__ == "__main__":
    asyncio.run(main())
    print("Agent groupchat completed successfully.")