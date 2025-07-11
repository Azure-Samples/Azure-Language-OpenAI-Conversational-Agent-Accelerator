import os
import json
from semantic_kernel.agents import AzureAIAgent, AgentGroupChat, GroupChatOrchestration, RoundRobinGroupChatManager, GroupChatManager
from semantic_kernel.agents.strategies import TerminationStrategy, SequentialSelectionStrategy
from semantic_kernel.agents.runtime import InProcessRuntime
from agents.order_status_plugin import OrderStatusPlugin
from agents.order_refund_plugin import OrderRefundPlugin
from agents.order_cancel_plugin import OrderCancellationPlugin
from semantic_kernel.contents import AuthorRole, ChatMessageContent
from azure.ai.projects import AIProjectClient
from typing import Callable
from azure.identity.aio import DefaultAzureCredential

import asyncio
from semantic_kernel.agents import GroupChatManager, BooleanResult, StringResult, MessageResult
from semantic_kernel.contents import ChatMessageContent, ChatHistory
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
        if not chat_history:
            return BooleanResult(result=False, reason="No messages in chat history.")

        # Get the last message from the chat history
        last_message = chat_history[-1]

        try:
            # Parse the last message content as JSON
            parsed_content = json.loads(last_message.content)

            # Check if 'need_more_info' exists and is True
            need_more_info = parsed_content.get("need_more_info") == "True"
            if need_more_info:
                return BooleanResult(result=True, reason="User input is required based on the last message.")
        except json.JSONDecodeError:
            return BooleanResult(
                result=False,
                reason="Last message content is not valid JSON."
            )
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
                print("[SYSTEM]: Last message is from the USER, routing to TriageAgent for initial triage...")
                
                try:
                    return StringResult(
                    result=next((agent for agent in participant_descriptions.keys() if agent == "TriageAgent"), None),
                    reason="Routing to TriageAgent for initial triage."
                    )
                except Exception as e:
                    print(f"[SYSTEM]: Error routing to TriageAgent, returning None. Exception: {e}")
                    return StringResult(
                        result=None,
                        reason="Error routing to TriageAgent."
                    )
            else:
                print("[SYSTEM]: Last message is from the USER, routing back to custom agent...")
                
                # If the last message is from the user, route to the last agent that responded
                last_agent = chat_history[-2].name if len(chat_history) > 1 else None
                if last_agent and last_agent in participant_descriptions:
                    print(f"[SYSTEM]: Routing back to last agent: {last_agent}")
                    return StringResult(
                        result=last_agent,
                        reason=f"Routing back to last agent: {last_agent}."
                    )
                else:
                    print("[SYSTEM]: No valid last agent found, returning None.")
                    return StringResult(
                        result=None,
                        reason="No valid last agent found."
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
                    # print("[SYSTEM]: CLU result received, checking intent, entities, and confidence...")
                    # intent = parsed["response"]["result"]["prediction"]["topIntent"]
                    # confidence = parsed["response"]["result"]["prediction"]["intents"][0]["confidenceScore"]
    
                    # # Filter based on confidence threshold
                    # if confidence < confidence_threshold:
                    #     print("CLU confidence threshold not met")
                    #     raise ValueError("CLU confidence threshold not met")
                    # else:
                    #     print("[TriageAgent]: Detected Intent:", intent)
                    #     print("[TriageAgent]: Identified Intent and Entities, routing to HeadSupportAgent for custom agent selection...")
                    #     return StringResult(
                    #         result=next((agent for agent in participant_descriptions.keys() if agent == "HeadSupportAgent"), None),
                    #         reason="Routing to HeadSupportAgent for custom agent selection."
                    #     )
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
    
        # Default case
        print("[SYSTEM]: No valid routing logic found, returning None.")
        return StringResult(
            result=None,
            reason="No valid routing logic found."
        )
    

    # Function for requesting user input (TODO: Implement this after migration is completed)
    async def request_user_input(self, chat_history, participant_descriptions):
        return await super().request_user_input(chat_history, participant_descriptions)

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
        
        # Check if the last message contains termination or need_more_info flags
        try:
            parsed_content = json.loads(last_message.content)
            terminated = parsed_content.get("terminated") == "True"
            need_more_info = parsed_content.get("need_more_info") == "True"
    
            if terminated or need_more_info:
                return BooleanResult(
                    result=True,
                    reason="Chat terminated due to agent response."
                )
        except json.JSONDecodeError:
            return BooleanResult(
                result=False,
                reason="Failed to parse last message content."
            )
    
        # Default case: no termination
        return BooleanResult(
            result=False,
            reason="No termination flags found in last message."
        )
    

async def human_response_function(chat_histoy: ChatHistory) -> ChatMessageContent:
    """Function to get user input."""
    user_input = input("User: ")
    return ChatMessageContent(role=AuthorRole.USER, content=user_input)

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
                description=" "
                #description="A triage agent that routes inquiries to the proper custom agent and you must actually call the API tool. YOU MUST USE THE INTENTS FROM THE TRAINED CLU MODEL. DO NOT JUST RETURN THE INPUT PAYLOAD. ENSURE YOU CALL THE CLU OR CQA API TOOLS. Ensure you do not use any special characters in the JSON response, as this will cause the agent to fail. The response must be a valid JSON object.",
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

            head_support_agent_definition = await client.agents.get_agent(AGENT_IDS["HEAD_SUPPORT_AGENT_ID"])
            head_support_agent = AzureAIAgent(
                client=client,
                definition=head_support_agent_definition,
                description="A head support agent that routes inquiries to the proper custom agent. Ensure you do not use any special characters in the JSON response, as this will cause the agent to fail. The response must be a valid JSON object.",
            )

            print("Agents initialized successfully.")
            print(f"Triage Agent ID: {triage_agent.id}")
            print(f"Head Support Agent ID: {head_support_agent.id}")
            print(f"Order Status Agent ID: {order_status_agent.id}")
            print(f"Order Cancel Agent ID: {order_cancel_agent.id}")
            print(f"Order Refund Agent ID: {order_refund_agent.id}")

            created_agents = [triage_agent, head_support_agent, order_status_agent, order_cancel_agent, order_refund_agent]

            orchestration = GroupChatOrchestration(
                members=created_agents,
                manager=CustomGroupChatManager(
                    human_response_function=human_response_function,
                ),
            )

            for attempt in range(1, 3):
                print(f"\n[RETRY ATTEMPT {attempt}] Starting new runtime...")
                runtime = InProcessRuntime(ignore_unhandled_exceptions=False)
                runtime.start()

                try:
                    task_json = {
                            "current_question": "order id 1234",
                            "history": [
                                "user: I wanna refund my order",
                                "bot: what's the order id"
                            ]
                        }
                    
                    task_string = json.dumps(task_json)
                    print(task_string)
                    print(type(task_string))

                    orchestration_result = await orchestration.invoke(
                        task=task_string,
                        runtime=runtime,
                    )

                    try:
                        # Timeout to avoid indefinite hangs
                        # value = await asyncio.wait_for(orchestration_result.get(), timeout=5)
                        value = await orchestration_result.get(timeout=60)
                        print(f"\n***** Result *****\n{value}")
                        break  # Success

                    except asyncio.TimeoutError:
                        print("[TIMEOUT]: The orchestration result took too long.")
                    except Exception as e:
                        print(f"[EXCEPTION]: Orchestration failed with exception: {e}")

                finally:
                    try:
                        await runtime.stop_when_idle()
                    except Exception as e:
                        print(f"[SHUTDOWN ERROR]: Runtime failed to shut down cleanly: {e}")
                await asyncio.sleep(2)  # short delay before retry
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
    print("Agent setup completed successfully.")
