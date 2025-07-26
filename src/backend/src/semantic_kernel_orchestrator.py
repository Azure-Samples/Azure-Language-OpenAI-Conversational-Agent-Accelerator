# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
import asyncio
from typing import Callable
from semantic_kernel.agents import AzureAIAgent, GroupChatOrchestration, GroupChatManager, BooleanResult, StringResult, MessageResult
from semantic_kernel.contents import ChatMessageContent, ChatHistory, AuthorRole
from semantic_kernel.agents.runtime import InProcessRuntime
from agents.order_status_plugin import OrderStatusPlugin
from agents.order_refund_plugin import OrderRefundPlugin
from agents.order_cancel_plugin import OrderCancellationPlugin
from azure.ai.projects import AIProjectClient
from pydantic import BaseModel

# Define the confidence threshold for CLU intent recognition
confidence_threshold = float(os.environ.get("CLU_CONFIDENCE_THRESHOLD", "0.5"))
cqa_confidence = float(os.environ.get("CQA_CONFIDENCE", "0.5"))


class ChatMessage(BaseModel):
    role: str
    content: str


# Custom functions to route messages from specific roles / agents
def route_user_message(participant_descriptions: dict) -> StringResult:
    try:
        return StringResult(
            result=next((agent for agent in participant_descriptions.keys() if agent == "TranslationAgent"), None),
            reason="Routing to TranslationAgent for initial translation."
        )
    except Exception as e:
        return StringResult(
            result=None,
            reason=f"Error routing to TranslationAgent: {e}"
        )


def route_translation_message(last_message: ChatMessageContent, participant_descriptions: dict) -> StringResult:
    try:
        parsed = json.loads(last_message.content)
        response = parsed['response']
        print("[TranslationAgent] Translated message:", response)

        return StringResult(
            result=next((agent for agent in participant_descriptions.keys() if agent == "TriageAgent"), None),
            reason="Routing to TriageAgent for message translation."
        )
    except Exception as e:
        return StringResult(
            result=None,
            reason=f"Error routing to TriageAgent: {e}"
        )


def route_triage_message(last_message: ChatMessageContent, participant_descriptions: dict) -> StringResult:
    try:
        parsed = json.loads(last_message.content)
        # Handle CQA results
        if parsed.get("type") == "cqa_result":
            print("[SYSTEM]: CQA result received, checking confidence...")
            confidence = parsed["response"]["answers"][0]["confidenceScore"]

            if confidence >= cqa_confidence:
                return StringResult(
                    result=next((agent for agent in participant_descriptions.keys() if agent == "TranslationAgent"), None),
                    reason="Routing to TranslationAgent for final translation."
                )
            else:
                raise ValueError(f"[TriageAgent] CQA result returned low confidence score: {confidence}. Expected at least {cqa_confidence}.")

        # Handle CLU results
        if parsed.get("type") == "clu_result":
            print("[SYSTEM]: CLU result received, checking intent and entities...")
            intent = parsed["response"]["result"]["conversations"][0]["intents"][0]["name"]
            print("[TriageAgent]: detected intent ", intent, ", routing to HeadSupportAgent for custom agent selection...")
            return StringResult(
                result=next((agent for agent in participant_descriptions.keys() if agent == "HeadSupportAgent"), None),
                reason="Routing to HeadSupportAgent for custom agent selection."
            )

    # Handle errors in triage agent response
    except Exception as e:
        print(f"[SYSTEM]: Error processing TriageAgent message: {e}")
        return StringResult(
            result=None,
            reason="Error processing TriageAgent message."
        )


def route_head_support_message(last_message: ChatMessageContent, participant_descriptions: dict) -> StringResult:
    try:
        # Grab the target agent from the parsed content
        parsed = json.loads(last_message.content)
        route = parsed.get("target_agent")

        print("[HeadSupportAgent] Routing to target custom agent:", route)
        return StringResult(
            result=next((agent for agent in participant_descriptions.keys() if agent == route), None),
            reason=f"Routing to target custom agent: {route}."
        )
    except Exception as e:
        print(f"[SYSTEM]: Error processing HeadSupportAgent message: {e}")
        return StringResult(
            result=None,
            reason="Error processing HeadSupportAgent message."
        )


def route_custom_agent_message(last_message: ChatMessageContent, participant_descriptions: dict) -> StringResult:
    try:
        response = json.loads(last_message.content)["response"]
        print(f"[{last_message.name}]: Response content: {response}")
        print(f"[TranslationAgent]: Translating {response}")
        return StringResult(
            result=next((agent for agent in participant_descriptions.keys() if agent == "TranslationAgent"), None),
            reason="Handle final message translation back to original language."
        )
    except Exception as e:
        print(f"[SYSTEM]: Error processing custom agent message: {e}")
        return StringResult(
            result=None,
            reason="Error processing custom agent message."
        )


class CustomGroupChatManager(GroupChatManager):
    """
    Custom group chat manager for Semantic Kernel Group Chat Orchestration.
    You must override the methods to implement custom logic for agent selection, termination, and message filtering.
    """
    # Filtering results in the group chat
    async def filter_results(self, chat_history: ChatHistory) -> MessageResult:
        if not chat_history:
            return MessageResult(
                result=ChatMessageContent(role="assistant", content="No messages in chat history."),
                reason="Chat history is empty."
            )

        # Get the last message from the chat history
        last_message = chat_history[-1]

        return MessageResult(
            result=ChatMessageContent(role="assistant", content=last_message.content),
            reason="Returning the last agent's response."
        )

    # Custom logic to decide if user input is needed
    async def should_request_user_input(self, chat_history: ChatHistory) -> BooleanResult:
        return BooleanResult(result=False, reason="No user input required.")

    # Function to create custom agent selection methods
    async def select_next_agent(self, chat_history: ChatHistory, participant_descriptions: dict) -> StringResult:
        """
        Multi-agent orchestration method for Semantic Kernel Agent Group Chat.
        This method decides how to select the next agent based on the current message and agent with custom logic based on agent responses.
        """
        last_message = chat_history[-1] if chat_history else None
        format_agent_response(last_message)

        # Process user messages
        if not last_message or last_message.role == AuthorRole.USER:
            print("[SYSTEM]: Last message is from the USER, routing to TranslationAgent for initial translation...")
            return route_user_message(participant_descriptions)

        elif last_message.name == "TranslationAgent":
            print("[SYSTEM]: Last message is from TranslationAgent, routing to TriageAgent for message translation...")
            return route_translation_message(last_message, participant_descriptions)

        # Process triage agent messages
        elif last_message.name == "TriageAgent":
            print("[SYSTEM]: Last message is from TriageAgent, checking if agent returned a CQA or CLU result...")
            return route_triage_message(last_message, participant_descriptions)

        # Process head support agent messages
        elif last_message.name == "HeadSupportAgent":
            print("[SYSTEM]: Last message is from HeadSupportAgent, choosing custom agent...")
            return route_head_support_message(last_message, participant_descriptions)

        # Process custom agent messages - customize as needed
        elif last_message.name in ["OrderStatusAgent", "OrderRefundAgent", "OrderCancelAgent"]:
            print(f"[SYSTEM]: Last message is from {last_message.name}, translate back to original language if needed.")
            return route_custom_agent_message(last_message, participant_descriptions)

        # Default case
        print("[SYSTEM]: No valid routing logic found, returning None.")
        return StringResult(
            result=None,
            reason="No valid routing logic found."
        )

    # Function to check for termination
    async def should_terminate(self, chat_history):
        """
        Custom termination logic for the agent group chat.
        Ends the chat if the last message indicates termination or requires more information.
        """
        last_message = chat_history[-1] if chat_history else None
        # If history is empty, return False
        if not last_message:
            return BooleanResult(
                result=False,
                reason="No messages in chat history."
            )

        # Check if message is from the translation agent and is not the initial translation
        if last_message.name == "TranslationAgent" and len(chat_history) > 3:
            print(last_message.name)
            print(last_message.content)
            return BooleanResult(
                result=True,
                reason="Chat terminated due to TranslationAgent response."
            )

        return BooleanResult(
            result=False,
            reason="No termination flags found in last message."
        )


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
            description="A triage agent that routes inquiries to the proper custom agent."
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
            description="A head support agent that routes inquiries to the proper custom agent.",
        )

        translation_agent_definition = await self.client.agents.get_agent(self.agent_ids["TRANSLATION_AGENT_ID"])
        translation_agent = AzureAIAgent(
            client=self.client,
            definition=translation_agent_definition,
            description="A translation agent that translates to English",
        )
        # Set the translation agent for the orchestrator to handle fallback translations
        self.translation_agent = translation_agent

        print("Agents initialized successfully.")
        print(f"Triage Agent ID: {triage_agent.id}")
        print(f"Head Support Agent ID: {head_support_agent.id}")
        print(f"Order Status Agent ID: {order_status_agent.id}")
        print(f"Order Cancel Agent ID: {order_cancel_agent.id}")
        print(f"Order Refund Agent ID: {order_refund_agent.id}")
        print(f"Translation Agent ID: {translation_agent.id}")

        return [translation_agent, triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent]

    async def create_agent_group_chat(self) -> None:
        """
        Create an agent group chat with the specified chat ID after all agents have been initialized.
        This method initializes the agents and sets up the agent group chat with custom selection and termination strategies
        """
        created_agents = await self.initialize_agents()
        print("Agents initialized:", [agent.name for agent in created_agents])

        self.orchestration = GroupChatOrchestration(
            members=created_agents,
            manager=CustomGroupChatManager(),
        )

        print("Agent group chat created successfully.")

    async def process_message(self, task_content: str) -> str:
        """
        Process a message in the agent group chat.
        This method creates a new agent group chat and processes the message.
        """
        retry_count = 0
        last_exception = None
        need_more_info = False

        # Use retry logic to handle potential errors during chat invocation
        while retry_count < self.max_retries:
            print(f"\n[RETRY ATTEMPT {retry_count}] Starting new runtime...")
            runtime = InProcessRuntime()
            runtime.start()

            try:
                orchestration_result = await self.orchestration.invoke(
                    task=task_content,
                    runtime=runtime,
                )

                try:
                    # Timeout to avoid indefinite hangs
                    value = await orchestration_result.get(timeout=120)
                    print(f"\n***** Result *****\n{value.content}")

                    final_response = json.loads(value.content)

                    print("[SYSTEM]: Final response is ", final_response['response']['final_answer'])
                    need_more_info = final_response['response']['need_more_info']
                    return final_response['response']['final_answer'], need_more_info

                except Exception as e:
                    print(f"[EXCEPTION]: Orchestration failed with exception: {e}")
                    last_exception = {"type": "exception", "message": str(e)}
                    retry_count += 1

            finally:
                try:
                    await runtime.stop_when_idle()
                except Exception as e:
                    print(f"[SHUTDOWN ERROR]: Runtime failed to shut down cleanly: {e}")

            # Short delay before retry
            await asyncio.sleep(1)

        if last_exception:
            return {
                "error": f"An error occurred: {last_exception}"
            }, need_more_info


def format_agent_response(response):
    try:
        # Pretty print the JSON response
        formatted_content = json.dumps(json.loads(response.content), indent=2)
        print(f"[{response.name if response.name else 'USER'}]: \n{formatted_content}\n")
    except json.JSONDecodeError:
        # Fallback to regular print if content is not JSON
        print(f"[{response.name}]: {response.content}\n")
    return response.content
