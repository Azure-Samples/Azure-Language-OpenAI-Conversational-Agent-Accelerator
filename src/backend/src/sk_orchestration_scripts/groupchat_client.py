# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
This script is a local script to interact with the GroupChatOrchestration class within the Semantic Kernel framework.
It initializes agents, sets up a custom group chat manager, and runs an orchestration task.
"""

import os
import json
import asyncio
from semantic_kernel.agents import AzureAIAgent, GroupChatOrchestration, GroupChatManager, BooleanResult, StringResult, MessageResult
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.functions import kernel_function
from semantic_kernel.contents import AuthorRole, ChatMessageContent, ChatHistory
from azure.identity.aio import DefaultAzureCredential

from dotenv import load_dotenv
load_dotenv()


# Environment variables
PROJECT_ENDPOINT = os.environ.get("AGENTS_PROJECT_ENDPOINT")
MODEL_NAME = os.environ.get("AOAI_DEPLOYMENT")


# Comment out for local testing:
AGENT_IDS = {
    "TRIAGE_AGENT_ID": os.environ.get("TRIAGE_AGENT_ID"),
    "HEAD_SUPPORT_AGENT_ID": os.environ.get("HEAD_SUPPORT_AGENT_ID"),
    "ORDER_STATUS_AGENT_ID": os.environ.get("ORDER_STATUS_AGENT_ID"),
    "ORDER_CANCEL_AGENT_ID": os.environ.get("ORDER_CANCEL_AGENT_ID"),
    "ORDER_REFUND_AGENT_ID": os.environ.get("ORDER_REFUND_AGENT_ID"),
    "TRANSLATION_AGENT_ID": os.environ.get("TRANSLATION_AGENT_ID"),
    "CUSTOMER_TRANSLATE_AGENT_ID": os.environ.get("CUSTOMER_TRANSLATE_AGENT_ID"),
    "SINGLE_TRANSLATE_AGENT_ID": os.environ.get("SINGLE_TRANSLATE_AGENT_ID"),
}

# Define the confidence threshold for CLU intent recognition
confidence_threshold = float(os.environ.get("CLU_CONFIDENCE_THRESHOLD", "0.5"))


# Agent plugins
class OrderCancellationPlugin:
    @kernel_function
    def process_cancellation(self, order_id: str) -> str:
        """Process a cancellation for an order."""
        # Simulate processing a cancellation
        print(f"[CancellationPlugin] Processing cancellation for order {order_id}")
        return f"Cancellation for order {order_id} has been processed successfully."


class OrderRefundPlugin:
    @kernel_function
    def process_refund(self, order_id: str) -> str:
        """Process a refund for an order."""
        # Simulate processing a refund
        print(f"[RefundPlugin] Processing refund for order {order_id}")
        return f"Refund for order {order_id} has been processed successfully."


class OrderStatusPlugin:
    @kernel_function
    def check_order_status(self, order_id: str) -> str:
        """Check the status of an order."""
        print(f"[OrderStatusPlugin] Checking status for order {order_id}")
        return f"Order {order_id} is shipped and will arrive in 2-3 days."


class CustomGroupChatManager(GroupChatManager):
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

    async def should_request_user_input(self, chat_history: ChatHistory) -> BooleanResult:
        # Custom logic to decide if user input is needed
        return BooleanResult(
            result=False,
            reason="No user input needed based on the last message."
        )

    # Function to create custom agent selection methods
    async def select_next_agent(self, chat_history, participant_descriptions):
        """
        Multi-agent orchestration method for Semantic Kernel Agent Group Chat.
        This method decides how to select the next agent based on the current message and agent with custom logic.
        """
        last_message = chat_history[-1] if chat_history else None
        format_agent_response(last_message)

        # Process user messages
        if not last_message or last_message.role == AuthorRole.USER:

            if len(chat_history) == 1:
                print("[SYSTEM]: Last message is from the USER, routing to translator for initial translation...")

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

        elif last_message.name == "TranslationAgent":
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

        # Process triage agent messages
        elif last_message.name == "TriageAgent":
            print("[SYSTEM]: Last message is from TriageAgent, checking if agent returned a CQA or CLU result...")
            try:
                parsed = json.loads(last_message.content)

                # Handle CQA results
                if parsed.get("type") == "cqa_result":
                    print("[SYSTEM]: CQA result received, determining final response...")
                    return StringResult(
                        result=None,
                        reason="CQA result received, terminating chat."
                    )

                # Handle CLU results
                if parsed.get("type") == "clu_result":
                    print("[SYSTEM]: CLU result received, checking intent, entities, and confidence...")
                    intent = parsed["response"]["result"]["conversations"][0]["intents"][0]["name"]
                    print("[TriageAgent]: Detected Intent:", intent)
                    print("[TriageAgent]: Identified Intent and Entities, routing to HeadSupportAgent for custom agent selection...")
                    return StringResult(
                        result=next((agent for agent in participant_descriptions.keys() if agent == "HeadSupportAgent"), None),
                        reason="Routing to HeadSupportAgent for custom agent selection."
                    )

            except Exception as e:
                print(f"[SYSTEM]: Error processing TriageAgent message: {e}")
                return StringResult(
                    result=None,
                    reason="Error processing TriageAgent message."
                )

        # Process head support agent messages
        elif last_message.name == "HeadSupportAgent":
            print("[SYSTEM]: Last message is from HeadSupportAgent, choosing custom agent...")
            try:
                parsed = json.loads(last_message.content)

                # Grab the target agent from the parsed content
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

        elif last_message.name in ["OrderStatusAgent", "OrderCancelAgent", "OrderRefundAgent"]:
            print(f"[SYSTEM]: Last message is from {last_message.name}, returning to TranslationAgent for final routing.")
            try:
                parsed = json.loads(last_message.content)

                return StringResult(
                    result=next((agent for agent in participant_descriptions.keys() if agent == "TranslationAgent"), None),
                    reason="Handle final message formatting"
                )
            except Exception as e:
                print(f"[SYSTEM]: Error preparing TranslationAgent follow-up: {e}")
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

        if last_message.name == "TranslationAgent" and len(chat_history) > 3:
            print(last_message.name)
            return BooleanResult(
                result=True,
                reason="Chat terminated due to TranslationAgent response."
            )

        return BooleanResult(
            result=False,
            reason="No termination flags found in last message."
        )


def agent_response_callback(message: ChatMessageContent) -> None:
    """Observer function to print the messages from the agents."""
    print(f"**{message.name}**\n{message.content}")


# sample reference for creating an Azure AI agent
async def main():
    async with DefaultAzureCredential(exclude_interactive_browser_credential=False) as creds:
        async with AzureAIAgent.create_client(credential=creds, endpoint=PROJECT_ENDPOINT) as client:
            # Grab the agent definition from AI Foundry
            triage_agent_definition = await client.agents.get_agent(AGENT_IDS["TRIAGE_AGENT_ID"])
            triage_agent = AzureAIAgent(
                client=client,
                definition=triage_agent_definition,
                description="A triage agent that routes inquiries to the proper custom agent",
            )

            order_status_agent_definition = await client.agents.get_agent(AGENT_IDS["ORDER_STATUS_AGENT_ID"])
            order_status_agent = AzureAIAgent(
                client=client,
                definition=order_status_agent_definition,
                description="An agent that checks order status",
                plugins=[OrderStatusPlugin()],
            )

            order_cancel_agent_definition = await client.agents.get_agent(AGENT_IDS["ORDER_CANCEL_AGENT_ID"])
            order_cancel_agent = AzureAIAgent(
                client=client,
                definition=order_cancel_agent_definition,
                description="An agent that checks on cancellations",
                plugins=[OrderCancellationPlugin()],
            )

            order_refund_agent_definition = await client.agents.get_agent(AGENT_IDS["ORDER_REFUND_AGENT_ID"])
            order_refund_agent = AzureAIAgent(
                client=client,
                definition=order_refund_agent_definition,
                description="An agent that checks on refunds",
                plugins=[OrderRefundPlugin()],
            )

            head_support_agent_definition = await client.agents.get_agent(AGENT_IDS["HEAD_SUPPORT_AGENT_ID"])
            head_support_agent = AzureAIAgent(
                client=client,
                definition=head_support_agent_definition,
                description="A head support agent that routes inquiries to the proper custom agent.",
            )

            translation_agent_definition = await client.agents.get_agent(AGENT_IDS["TRANSLATION_AGENT_ID"])
            translation_agent = AzureAIAgent(
                client=client,
                definition=translation_agent_definition,
                description="Translates into English",
            )

            print("Agents initialized successfully.")
            print(f"Triage Agent ID: {triage_agent.id}")
            print(f"Head Support Agent ID: {head_support_agent.id}")
            print(f"Order Status Agent ID: {order_status_agent.id}")
            print(f"Order Cancel Agent ID: {order_cancel_agent.id}")
            print(f"Order Refund Agent ID: {order_refund_agent.id}")
            print(f"Translation Agent ID: {translation_agent.id}")

            created_agents = [translation_agent, triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent]

            orchestration = GroupChatOrchestration(
                members=created_agents,
                manager=CustomGroupChatManager(),
            )

            for attempt in range(1, 3):
                print(f"\n[RETRY ATTEMPT {attempt}] Starting new runtime...")
                runtime = InProcessRuntime(ignore_unhandled_exceptions=False)
                runtime.start()

                try:
                    task_json = {
                        "query": "quiero cancelar mi pedido 12345",
                        "to": "english"
                    }
                    task_string = json.dumps(task_json)
                    print(task_string)

                    orchestration_result = await orchestration.invoke(
                        task=task_string,
                        runtime=runtime,
                    )

                    try:
                        # Timeout to avoid indefinite hangs
                        value = await orchestration_result.get(timeout=60)
                        print(f"\n***** Result *****\n{value}")
                        break  # Success

                    except Exception as e:
                        print(f"[EXCEPTION]: Orchestration failed with exception: {e}")

                finally:
                    try:
                        await runtime.stop_when_idle()
                    except Exception as e:
                        print(f"[SHUTDOWN ERROR]: Runtime failed to shut down cleanly: {e}")

                await asyncio.sleep(2)
            else:
                print(f"[FAILURE]: Max retries ({3}) reached. No successful response.")


def format_agent_response(response):
    try:
        # Pretty print the JSON response
        formatted_content = json.dumps(json.loads(response.content), indent=2)
        print(f"[{response.name}]: \n{formatted_content}\n")
    except json.JSONDecodeError:
        # Fallback to regular print if content is not JSON
        print(f"[{response.name if response.name else 'USER'}]: {response.content}\n")
    return response.content


if __name__ == "__main__":
    asyncio.run(main())
    print("Agent orchestration completed successfully.")
