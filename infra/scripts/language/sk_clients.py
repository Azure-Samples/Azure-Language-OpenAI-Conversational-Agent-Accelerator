import os
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from dotenv import load_dotenv
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings, AgentGroupChat
from semantic_kernel.agents.strategies import TerminationStrategy, SequentialSelectionStrategy
from agents.order_status_plugin import OrderStatusPlugin
from agents.order_refund_plugin import OrderRefundPlugin
from agents.order_return_plugin import OrderReturnPlugin
from agents.discount_plugin import OrderDiscountPlugin
from semantic_kernel.agents.runtime import InProcessRuntime
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.contents import AuthorRole, ChatMessageContent
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

# Create chat completion service using Azure OpenAI
chat_completion_service = AzureChatCompletion(
    endpoint=AOAI_ENDPOINT,
    deployment_name=MODEL_NAME,
)
print('successfully created chat completion service')

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
            return parsed.get("terminated") is True
        except Exception:
            return False

# sample reference for creating an Azure AI agent
async def main():
    ai_agent_settings = AzureAIAgentSettings(model_deployment_name=MODEL_NAME)
    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds, endpoint=PROJECT_ENDPOINT) as client,
    ):
        # order status agent
        # order_status_agent_definition = await client.agents.create_agent(
        #     model=ai_agent_settings.model_deployment_name,
        #     name="OrderStatusAgent",
        #     instructions="""You are a customer support agent that checks order status. You must use the OrderStatusPlugin to check the status of an order.
        #     You must return the response in the following format:
        #     {
        #         "response": "<OrderStatusResponse>",
        #         "terminated": true
        #     }""",
        # )

        # order_status_agent = AzureAIAgent(
        #     client=client,
        #     definition=order_status_agent_definition,
        #     description="An agent that checks order status",
        #     plugins=[OrderStatusPlugin()],
        # )

        # # order return agent
        # order_return_agent_definition = await client.agents.create_agent(
        #     model=ai_agent_settings.model_deployment_name,
        #     name="OrderReturnAgent",
        #     instructions="""You are a customer support agent that handles order returns. You must use the OrderReturnPlugin to handle order return requests.
        #     You must return the response in the following format:
        #     {
        #         "response": "<OrderReturnResponse>",
        #         "terminated": true
        #     }""",
        # )

        # order_return_agent = AzureAIAgent(
        #     client=client,
        #     definition=order_return_agent_definition,
        #     description="An agent that checks on returns",
        #     plugins=[OrderReturnPlugin()],
        # )

        # # order refund agent
        # order_refund_agent_definition = await client.agents.create_agent(
        #     model=ai_agent_settings.model_deployment_name,
        #     name="OrderRefundAgent",
        #     instructions="""You are a customer support agent that handles order refunds. You must use the OrderRefundPlugin to handle order refund requests.
        #     You must return the response in the following format:
        #     {
        #         "response": "<OrderRefundResponse>",
        #         "terminated": True
        #     }""",
        # )

        # order_refund_agent = AzureAIAgent(
        #     client=client,
        #     definition=order_refund_agent_definition,
        #     description="An agent that checks on refunds",
        #     plugins=[OrderRefundPlugin()],
        # )

        # print("Order status agent id: ", order_status_agent.id)
        # print("Order refund agent id: ", order_refund_agent.id)
        # print("Order return agent id: ", order_return_agent.id)

        # # triage agent tools
        # clu_api_tool, cqa_api_tool = create_tools(config)

        # triage_agent_definition = await client.agents.create_agent(
        #     model=ai_agent_settings.model_deployment_name,
        #     name="TriageAgent",
        #     instructions="""
        #     You are a triage agent. Your goal is to answer questions and redirect message according to their intent. You have at your disposition 2 tools but can only use ONE:
        #     1. cqa_api: to answer customer questions such as procedures and FAQs.
        #     2. clu_api: to extract the intent of the message.
        #     - The API version must be "2023-04-01"
        #     You must use the ONE of the tools to perform your task. You should only use one tool at a time, and do NOT chain the tools together. Only if the tools are not able to provide the information, you can answer according to your general knowledge. You must return the full API response for either tool and ensure it's a valid JSON.
        #     - When you return answers from the clu_api, format the response as JSON: {"type": "clu_result", "response": {clu_response}, "terminated": False}, where clu_response is the full JSON API response from the clu_api without rewriting or removing any info.   Return immediately. Do not call the cqa_api afterwards.
        #     This is extremeley critical - to call the clu_api, the following parameters values MUST be used in the payload:
        #         - 'api-version': must be "2023-04-01"
        #         - 'projectName': value must be 'conv-assistant-clu'
        #         - 'deploymentName': value must be 'clu-m1-d1'
        #         - 'text': must be the input from the user.
        #     - When you return answers from the cqa_api, format the response as JSON: {"type": "cqa_result", "response": {cqa_response}, "terminated": True} where cqa_response is the full JSON API response from the cqa_api without rewriting or removing any info. Return immediately
        #     """,
        #     tools=clu_api_tool.definitions + cqa_api_tool.definitions,
        # )

        # triage_agent = AzureAIAgent(
        #     client=client,
        #     definition=triage_agent_definition,
        #     description="A customer support agent that chooses between CLU and CQA APIs to answer customer questions and returns API response",
        # )

        # # print("Triage agent id: ", triage_agent.id)

        # # # Create Head Support Agent in AI Foundry
        # head_support_agent_definition = await client.agents.create_agent(
        #     model=ai_agent_settings.model_deployment_name,
        #     name="HeadSupportAgent",
        #     instructions="""
        #         You are a head support agent that routes inquiries to the proper custom agent based on the provided intent and entities from the triage agent.
        #         You must choose between the following agents:
        #         - OrderStatusAgent: for order status inquiries
        #         - OrderReturnAgent: for order return inquiries
        #         - OrderRefundAgent: for order refund inquiries

        #         You must return the response in the following format:
        #         {
        #           "target_agent": "<AgentName>",
        #           "intent": "<IntentName>",
        #           "entities": [<List of extracted entities>]
        #         }

        #         Where:
        #         - "target_agent" is the name of the agent you are routing to (must match one of the agent names above).
        #         - "intent" is the top-level intent extracted from the CLU result.
        #         - "entities" is a list of all entities extracted from the CLU result, including their category and value.
        #         """,
        # )

        # head_support_agent = AzureAIAgent(
        #     client=client,
        #     definition=head_support_agent_definition,
        #     description="A head support agent that routes inquiries to the proper custom agent",
        # )

        # # Collect agent IDs in a dictionary
        # agent_ids = {
        #     "TRIAGE_AGENT_ID": triage_agent_definition.id,
        #     "ORDER_STATUS_AGENT_ID": order_status_agent_definition.id,
        #     "ORDER_RETURN_AGENT_ID": order_return_agent_definition.id,
        #     "ORDER_REFUND_AGENT_ID": order_refund_agent_definition.id,
        #     "HEAD_SUPPORT_AGENT_ID": head_support_agent_definition.id,
        # }

        # # Output the agent IDs as JSON
        # print(json.dumps(agent_ids, indent=4))

        # Get the agents from these agent IDs
        agent_ids = {
            "TRIAGE_AGENT_ID": "asst_VnmEjOwWbiPjhvnMBwgznppW",
            "ORDER_STATUS_AGENT_ID": "asst_aEWmybkdV624MhurTxTeKfYn",
            "ORDER_RETURN_AGENT_ID": "asst_P9QyAickP7zkw4xW7b95eWdf",
            "ORDER_REFUND_AGENT_ID": "asst_7xBrY9qa6Gl2udmuw7x0zDlm",
            "HEAD_SUPPORT_AGENT_ID": "asst_c3WOZzwVVElkbcFk3hfnr5ml"
        }

        # grab the agents from the agent IDs
        triage_agent_definition = await client.agents.get_agent(agent_ids["TRIAGE_AGENT_ID"])
        triage_agent = AzureAIAgent(
            client=client,
            definition=triage_agent_definition,
            description="A customer support agent that chooses between CLU and CQA APIs to answer customer questions and returns API response. The CLU API version must be '2023-04-10'",
        )

        order_status_agent_definition = await client.agents.get_agent(agent_ids["ORDER_STATUS_AGENT_ID"])
        order_status_agent = AzureAIAgent(
            client=client,
            definition=order_status_agent_definition,
            description="An agent that checks order status",
            plugins=[OrderStatusPlugin()],
        )
        order_return_agent_definition = await client.agents.get_agent(agent_ids["ORDER_RETURN_AGENT_ID"])
        order_return_agent = AzureAIAgent(
            client=client,
            definition=order_return_agent_definition,
            description="An agent that checks on returns",
            plugins=[OrderReturnPlugin()],
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
            description="A head support agent that routes inquiries to the proper custom agent",
        )

        # create the agent group chat with all of the agents
        agent_group_chat = AgentGroupChat(
            agents=[
                triage_agent,
                head_support_agent,
                order_status_agent,
                order_return_agent,
                order_refund_agent,
            ],
            selection_strategy=SelectionStrategy(
                agents=[triage_agent, head_support_agent, order_status_agent, order_return_agent, order_refund_agent]
            ),
            termination_strategy=ApprovalStrategy(
                agents=[triage_agent, head_support_agent, order_status_agent, order_return_agent, order_refund_agent],
                maximum_iterations=10,
                automatic_reset=True,
            ),
        )

        print("Agent group chat created successfully.")

        # Process message
        user_msg = ChatMessageContent(role=AuthorRole.USER, content="I want to refund order 12387 because it was too small")
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

            
        except Exception as e:
            print(f"Error during chat invocation: {e}")


        # runtime = InProcessRuntime()
        # runtime.start()

        # # 3. Invoke the orchestration with a task and the runtime
        # orchestration_result = await handoff_orchestration.invoke(
        #     task="A customer is on the line.",
        #     runtime=runtime,
        # )

        # # 4. Wait for the results
        # value = await orchestration_result.get()
        # print(value)

        # # 5. Stop the runtime after the invocation is complete
        # await runtime.stop_when_idle()


if __name__ == "__main__":
    asyncio.run(main())
    print("Agent groupchat completed successfully.")