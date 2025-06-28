# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import json
from semantic_kernel.agents import AzureAIAgent, AgentGroupChat
from semantic_kernel.agents.strategies import TerminationStrategy, SequentialSelectionStrategy
from agents.order_status_plugin import OrderStatusPlugin
from agents.order_refund_plugin import OrderRefundPlugin
from agents.order_cancel_plugin import OrderCancellationPlugin
from semantic_kernel.contents import AuthorRole, ChatMessageContent

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
    
# Create the custom termination strategy for the agent groupchat by sublcassing the TerminationStrategy
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
        
# Custom multi-agent semantic kernel orchestrator
class SemanticKernelOrchestrator:
    def __init__(self, client, model_name, project_endpoint, agent_ids, max_retries=3):
        self.model_name = model_name
        self.project_endpoint = project_endpoint
        self.agent_ids = agent_ids
        self.client = client
        self.max_retries = max_retries

        # Initialize plugins for custom agents
        self.order_status_plugin = OrderStatusPlugin()
        self.order_refund_plugin = OrderRefundPlugin()
        self.order_cancel_plugin = OrderCancellationPlugin()

    # Initialize Semantic Kernel Azure AI Agents
    async def initialize_agents(self) -> list:
        """
        Initialize the agents for the semantic kernel orchestrator.
        This method retrieves the agent definitions from AI Foundry and creates AzureAIAgent instances.
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
        description="An agent that checks order status",
        plugins=[OrderStatusPlugin()],
        )

        order_cancel_agent_definition = await self.client.agents.get_agent(self.agent_ids["ORDER_CANCEL_AGENT_ID"])
        order_cancel_agent = AzureAIAgent(
        client=self.client,
        definition=order_cancel_agent_definition,
        description="An agent that checks on cancellations",
        plugins=[OrderCancellationPlugin()],
        )

        order_refund_agent_definition = await self.client.agents.get_agent(self.agent_ids["ORDER_REFUND_AGENT_ID"])
        order_refund_agent = AzureAIAgent(
        client=self.client,
        definition=order_refund_agent_definition,
        description="An agent that checks on refunds",
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

    # Create multi-agent orchestration
    async def create_agent_group_chat(self) -> None:
        """
        Create an agent group chat with the specified chat ID.
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
    
    async def initialize(self) -> None:
        """
        Initialize the semantic kernel orchestrator.
        This method creates the agent group chat and initializes the agents.
        """
        await self.create_agent_group_chat()
        print("Agent group chat created successfully.")
        print("Agents initialized:", [agent.name for agent in self.agent_group_chat.agents])

    # Process user messages and invoke the agent group chat
    async def process_message(self, message_content: str) -> str:
        """
        Process a message in the agent group chat.
        This method creates a new agent group chat and processes the message.
        """

        retry_count = 0
        last_exception = None

        while retry_count < self.max_retries:
            try:
                # Create a user message content
                user_message = ChatMessageContent(
                    role=AuthorRole.USER,
                    content=message_content,
                )

                # Append the current log file to the chat
                await self.agent_group_chat.add_chat_message(user_message)
            
                print("User message added to chat:", user_message.content)
                # Invoke a response from the agents
                async for response in self.agent_group_chat.invoke():
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
                    return final_response
                # if CLU
                else:
                    print("CLU result received, printing custom agent response.")
                    print("final response is ", final_response['response'])
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
        