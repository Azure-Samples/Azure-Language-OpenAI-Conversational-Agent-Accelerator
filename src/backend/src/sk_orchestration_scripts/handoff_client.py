# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
This script is a local script to interact with the HandoffOrchestration class within the Semantic Kernel framework.
It initializes agents, sets up handoffs, and runs an orchestration task.
"""

import os
import asyncio
from semantic_kernel.agents import AzureAIAgent, OrchestrationHandoffs, HandoffOrchestration
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.functions import kernel_function
from semantic_kernel.contents import AuthorRole, ChatMessageContent
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


def human_response_function() -> ChatMessageContent:
    """Observer function to print the messages from the agents."""
    user_input = input("User: ")
    return ChatMessageContent(role=AuthorRole.USER, content=user_input)


def agent_response_callback(message: ChatMessageContent) -> None:
    if message.content == "":
        return
    print(f"{message.name}: {message.content}")


# sample reference for creating an Azure AI agent
async def main():
    async with DefaultAzureCredential(exclude_interactive_browser_credential=False) as creds:
        async with AzureAIAgent.create_client(credential=creds, endpoint=PROJECT_ENDPOINT) as client:
            # Grab the agent definition from AI Foundry
            triage_agent_definition = await client.agents.get_agent(AGENT_IDS["TRIAGE_AGENT_ID"])
            triage_agent = AzureAIAgent(
                client=client,
                definition=triage_agent_definition,
                description="A triage agent that routes inquiries to the proper custom agent"
            )

            order_status_agent_definition = await client.agents.get_agent(AGENT_IDS["ORDER_STATUS_AGENT_ID"])
            order_status_agent = AzureAIAgent(
                client=client,
                definition=order_status_agent_definition,
                description="An agent that checks order status and it must use the OrderStatusPlugin to check the status of an order. If you need more information from the user, you must return a JSON response with 'need_more_info': 'True', otherwise you must return 'need_more_info': 'False'. You must return the response in the following valid JSON format: {'response': <OrderStatusResponse>, 'terminated': 'True', 'need_more_info': <'True' or 'False'>}",
                plugins=[OrderStatusPlugin()],
            )

            order_cancel_agent_definition = await client.agents.get_agent(AGENT_IDS["ORDER_CANCEL_AGENT_ID"])
            order_cancel_agent = AzureAIAgent(
                client=client,
                definition=order_cancel_agent_definition,
                description="An agent that checks on cancellations and it must use the OrderCancellationPlugin to handle order cancellation requests. If you need more information from the user, you must return a response with 'need_more_info': 'True', otherwise you must return 'need_more_info': 'False'. You must return the response in the following valid JSON format: {'response': <OrderCancellationResponse>, 'terminated': 'True', 'need_more_info': <'True' or 'False'>}",
                plugins=[OrderCancellationPlugin()],
            )

            order_refund_agent_definition = await client.agents.get_agent(AGENT_IDS["ORDER_REFUND_AGENT_ID"])
            order_refund_agent = AzureAIAgent(
                client=client,
                definition=order_refund_agent_definition,
                description="An agent that checks on refunds and it must use the OrderRefundPlugin to handle order refund requests. If you need more information from the user, you must return a JSON response with 'need_more_info': 'True', otherwise you must return 'need_more_info': 'False'. You must return the response in the following valid JSON format: {'response': <OrderRefundResponse>, 'terminated': 'True', 'need_more_info': <'True' or 'False'>}",
                plugins=[OrderRefundPlugin()],
            )

            print("Agents initialized successfully.")
            print(f"Triage Agent ID: {triage_agent.id}")
            print(f"Order Status Agent ID: {order_status_agent.id}")
            print(f"Order Cancel Agent ID: {order_cancel_agent.id}")
            print(f"Order Refund Agent ID: {order_refund_agent.id}")

            handoffs = (
                OrchestrationHandoffs()
                .add_many(    # Use add_many to add multiple handoffs to the same source agent at once
                    source_agent=triage_agent.name,
                    target_agents={
                        order_refund_agent.name: "Transfer to this agent if the issue is refund related. If the triage agent responds with a JSON, ensure you look at the 'topIntent' field and transfer to the appropriate agent based on the intent.",
                        order_status_agent.name: "Transfer to this agent if the issue is order status related. If the triage agent responds with a JSON, ensure you look at the 'topIntent' field and transfer to the appropriate agent based on the intent.",
                        order_cancel_agent.name: "Transfer to this agent if the issue is order cancellation related. If the triage agent responds with a JSON, ensure you look at the 'topIntent' field and transfer to the appropriate agent based on the intent.",
                    },
                )
                .add(    # Use add to add a single handoff
                    source_agent=order_refund_agent.name,
                    target_agent=triage_agent.name,
                    description="Transfer to this agent if the issue is NOT refund related. Transfer if the issue is related to order status or cancellation. Transfer if the request is from the user",
                )
                .add(
                    source_agent=order_status_agent.name,
                    target_agent=triage_agent.name,
                    description="Transfer to this agent if the issue is NOT order status related. Transfer if the issue is related to refund or cancellation. Transfer if the request is from the user",
                )
                .add(
                    source_agent=order_cancel_agent.name,
                    target_agent=triage_agent.name,
                    description="Transfer to this agent if the issue is NOT order cancellation related. Transfer if the issue is related to refund or order status. Transfer if the request is from the user",
                )
            )

            handoff_orchestration = HandoffOrchestration(
                members=[
                    triage_agent,
                    order_refund_agent,
                    order_status_agent,
                    order_cancel_agent,
                ],
                handoffs=handoffs,
                agent_response_callback=agent_response_callback,
                human_response_function=human_response_function,
            )

            runtime = InProcessRuntime()
            runtime.start()

            orchestration_result = await handoff_orchestration.invoke(
                task="What's the return policy",
                runtime=runtime,
            )
            try:
                value = await orchestration_result.get()
                print(value)

            except Exception as e:
                print(f"[ERROR]: Error occurred: {e}")

            await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main())
    print("Agent orchestration completed.")
