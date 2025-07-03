# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
from semantic_kernel.agents import AzureAIAgent, AgentGroupChat
from semantic_kernel.agents.strategies import TerminationStrategy, SequentialSelectionStrategy
from agents.order_status_plugin import OrderStatusPlugin
from agents.order_refund_plugin import OrderRefundPlugin
from agents.order_cancel_plugin import OrderCancellationPlugin
from semantic_kernel.contents import AuthorRole, ChatMessageContent
from azure.ai.projects import AIProjectClient
from typing import Callable

# Define the confidence threshold for CLU intent recognition
confidence_threshold = float(os.environ.get("CLU_CONFIDENCE_THRESHOLD", "0.5"))

# Create custom selection strategy for the agent groupchat by sublcassing the SequentialSelection Strategy
class SelectionStrategy(SequentialSelectionStrategy):
    async def select_agent(self, agents, history):
        """
        Multi-agent orchestration method for Semantic Kernel Agent Group Chat
        This method decides how to select agent based on the current message and agent with custom logic
        The two possible routes with this multi-agent orchestration are:
            1) user query -> triage agent [CLU tool invoked] -> head support agent -> custom agent -> terminate chat and return custom agent answer.
            2) user query -> triage agent [CQA tool invoked] -> terminate chat and return CQA answer.
        """
        last = history[-1] if history else None

        # Process user messages
        if not last or last.role == AuthorRole.USER or last is None:
            print("[SYSTEM]: Last message is from the USER, routing to TriageAgent...")
            return next((a for a in agents if a.name == "TriageAgent"), None)
        
        # Process triage agent mnessages
        elif last.name == "TriageAgent":
            print("[SYSTEM]: Last message is from TriageAgent, checking if agent returned a CQA or CLU result...")
            try:
                parsed = json.loads(last.content)

                # Handle CQA results
                if parsed.get("type") == "cqa_result":
                    print("[SYSTEM]: CQA result received, determining final response...")
                    return None  # End early
                
                # Handle CLU results
                if parsed.get("type") == "clu_result":
                    print("[SYSTEM]: CLU result received, checking intent, entities, and confidence ...")
                    intent = parsed["response"]["result"]["prediction"]["topIntent"]
                    confidence = parsed["response"]["result"]["prediction"]["intents"][0]["confidenceScore"]

                    # Filter based on confidence threshold:
                    if confidence < confidence_threshold:
                        print("CLU confidence threshold not met")
                        raise ValueError("CLU confidence threshold not met")
                    else:
                        print("[TriageAgent]: Detected Intent:", intent)
                        print("[TriageAgent]: Identified Intent and Entities, routing to HeadSupportAgent for custom agent selection... \n")
                        # Route to HeadSupportAgent for custom agent selection
                        return next((agent for agent in agents if agent.name == "HeadSupportAgent"), None)
            except Exception:
                return None

        # Process head support agent messages
        elif last.name == "HeadSupportAgent":
            print("[SYSTEM] Last message is from HeadSupportAgent, choosing custom agent...")
            try:
                parsed = json.loads(last.content)

                # Grab the target agent from the parsed content
                route = parsed.get("target_agent")
                print("[HeadSupportAgent] Routing to target custom agent:", route, "\n")
                return next((a for a in agents if a.name == route), None)
            except Exception:
                return None

        return None

# Create the custom termination strategy for the agent groupchat by subclassing the TerminationStrategy
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

        # If history is empty, return False
        if not last:
            return False
        
        # If the last message contains True for terminated or need_more_info, terminate
        try:
            parsed = json.loads(last.content)
            return parsed.get("terminated") == "True" or parsed.get("need_more_info") == "True"
        except Exception:
            return False
        
# Custom multi-agent semantic kernel orchestrator
class SemanticKernelOrchestrator:
    def __init__(
        self,
        client: AIProjectClient,
        model_name: str,
        project_endpoint: str,
        agent_ids: dict,
        fallback_function: Callable[[str, str, str], dict],
        max_retries: int = 3
    ):
        """
        Initialize the semantic kernel orchestrator with the AI Project client, model name, project endpoint,
        agent IDs, fallback function, and maximum retries.
        """
        self.client = client
        self.model_name = model_name
        self.project_endpoint = project_endpoint
        self.agent_ids = agent_ids
        self.fallback_function = fallback_function
        self.max_retries = max_retries

        # Initialize plugins for custom agents
        self.order_status_plugin = OrderStatusPlugin()
        self.order_refund_plugin = OrderRefundPlugin()
        self.order_cancel_plugin = OrderCancellationPlugin()

    async def initialize_agents(self) -> list:
        """
        Initialize the Semantic Kernel Azure AI agents for the semantic kernel orchestrator.
        This method retrieves the agent definitions from AI Foundry and creates AzureAIAgent instances for each foundry agent.
        """
        # Grab the agent definition from AI Foundry
        triage_agent_definition = await self.client.agents.get_agent(self.agent_ids["TRIAGE_AGENT_ID"])
        triage_agent = AzureAIAgent(
            client=self.client,
            definition=triage_agent_definition,
        )

        order_status_agent_definition = await self.client.agents.get_agent(self.agent_ids["ORDER_STATUS_AGENT_ID"])
        order_status_agent = AzureAIAgent(
            client=self.client,
            definition=order_status_agent_definition,
            description="An agent that checks order status and it must use the OrderStatusPlugin to check the status of an order. If you need more information from the user, you must return a response with 'need_more_info': 'True', otherwise you must return 'need_more_info': 'False'. You must return the response in the following valid JSON format: {'response': <OrderStatusResponse>, 'terminated': 'True', 'need_more_info': <'True' or 'False'>}",
            plugins=[OrderStatusPlugin()],
        )

        order_cancel_agent_definition = await self.client.agents.get_agent(self.agent_ids["ORDER_CANCEL_AGENT_ID"])
        order_cancel_agent = AzureAIAgent(
            client=self.client,
            definition=order_cancel_agent_definition,
            description="An agent that checks on cancellations and it must use the OrderCancellationPlugin to handle order cancellation requests. If you need more information from the user, you must return a response with 'need_more_info': 'True', otherwise you must return 'need_more_info': 'False'. You must return the response in the following valid JSON format: {'response': <OrderCancellationResponse>, 'terminated': 'True', 'need_more_info': <'True' or 'False'>}",
            plugins=[OrderCancellationPlugin()],
        )

        order_refund_agent_definition = await self.client.agents.get_agent(self.agent_ids["ORDER_REFUND_AGENT_ID"])
        order_refund_agent = AzureAIAgent(
            client=self.client,
            definition=order_refund_agent_definition,
            description="An agent that checks on refunds and it must use the OrderRefundPlugin to handle order refund requests. If you need more information from the user, you must return a response with 'need_more_info': 'True', otherwise you must return 'need_more_info': 'False'. You must return the response in the following valid JSON format: {'response': <OrderRefundResponse>, 'terminated': 'True', 'need_more_info': <'True' or 'False'>}",
            plugins=[OrderRefundPlugin()],
        )

        head_support_agent_definition = await self.client.agents.get_agent(self.agent_ids["HEAD_SUPPORT_AGENT_ID"])
        head_support_agent = AzureAIAgent(
            client=self.client,
            definition=head_support_agent_definition,
            description="A head support agent that routes inquiries to the proper custom agent. Ensure you do not use any special characters in the JSON response, as this will cause the agent to fail. The response must be a valid JSON object.",
        )

        print("Agents initialized successfully.")
        print(f"Triage Agent ID: {triage_agent.id}")
        print(f"Head Support Agent ID: {head_support_agent.id}")
        print(f"Order Status Agent ID: {order_status_agent.id}")
        print(f"Order Cancel Agent ID: {order_cancel_agent.id}")
        print(f"Order Refund Agent ID: {order_refund_agent.id}")

        return [triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent]

    async def create_agent_group_chat(self) -> None:
        """
        Create an agent group chat with the specified chat ID after all agents have been initialized.
        This method initializes the agents and sets up the agent group chat with custom selection and termination strategies
        """
        created_agents = await self.initialize_agents()
        print("Agents initialized:", [agent.name for agent in created_agents])

        # Create the agent group chat with the custom selection and termination strategies
        self.agent_group_chat = AgentGroupChat(
            agents=created_agents,
            selection_strategy=SelectionStrategy(
                agents=created_agents
            ),
            termination_strategy=ApprovalStrategy(
                agents=created_agents,
                maximum_iterations=10,
                automatic_reset=True,
            ),
        )

        print("Agent group chat created successfully.")
        print("Agents initialized:", [agent.name for agent in self.agent_group_chat.agents])

    async def process_message(self, message_content: str) -> str:
        """
        Process a message in the agent group chat.
        This method creates a new agent group chat and processes the message.
        """
        retry_count = 0
        last_exception = None

        # Use retry logic to handle potential errors during chat invocation
        while retry_count < self.max_retries:
            try:
                # Create a user message content
                user_message = ChatMessageContent(
                    role=AuthorRole.USER,
                    content=message_content,
                )

                # Append the current log file to the chat
                await self.agent_group_chat.add_chat_message(user_message)
            
                #print("User message added to chat:", user_message.content)
                print(f'[USER]: Message added to chat: "{user_message.content}"\n')
                # Invoke a response from the agents
                async for response in self.agent_group_chat.invoke():
                    if response is None or not response.name:
                        continue
                    final_response = format_agent_response(response)
                
                final_response = json.loads(final_response)

                # if CQA
                if final_response.get("type") == "cqa_result":
                    print("[SYSTEM]: Final CQA result received, terminating chat.")
                    final_response = final_response['response']['answers'][0]['answer']
                    print("[SYSTEM]: Final response is ", final_response)
                    return final_response
                
                # if CLU
                else:
                    print("[SYSTEM]: Final CLU result received, printing custom agent response...")
                    print("[SYSTEM]: Final response is ", final_response['response'])
                    return final_response['response']

            except Exception as e:
                retry_count += 1
                last_exception = e
                print(f"Error during chat invocation, retrying {retry_count}/{self.max_retries} times: {e}")

                # reset chat state
                self.agent_group_chat.clear_activity_signal()
                await self.agent_group_chat.reset()
                print("Chat reset due to error.")

                continue
            
        print("Max retries reached, returning last exception.")

        if last_exception:
            return {"error": last_exception}
        
def format_agent_response(response):
    try:
        # Pretty print the JSON response
        formatted_content = json.dumps(json.loads(response.content), indent=2)
        print(f"[{response.name}]: \n{formatted_content}\n")
    except json.JSONDecodeError:
        # Fallback to regular print if content is not JSON
        print(f"[{response.name}]: {response.content}\n")
    return response.content
        