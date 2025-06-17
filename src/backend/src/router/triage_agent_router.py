# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import sys
import json
import logging
from typing import Callable
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ListSortOrder, AgentThread
from router.clu_router import parse_response as parse_clu_response
from router.cqa_router import parse_response as parse_cqa_response
from utils import get_azure_credential

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

PII_ENABLED = os.environ.get("PII_ENABLED", "false").lower() == "true"


def create_triage_agent_router() -> Callable[[str, str, str], dict]:
    """
    Create triage agent router.
    """
    project_endpoint = os.environ.get("AGENTS_PROJECT_ENDPOINT")
    credential = get_azure_credential()
    agents_client = AgentsClient(
        endpoint=project_endpoint,
        credential=credential,
        api_version="2025-05-15-preview"
    )
    agent_id = os.environ.get("TRIAGE_AGENT_ID")
    agent = agents_client.get_agent(agent_id=agent_id)

    def triage_agent_router(
        utterance: str,
        language: str,
        id: str
    ) -> dict:
        """
        Triage agent router function.
        """
        # Process the agent run and handle retries
        max_retries = int(os.environ.get("MAX_AGENT_RETRY", 3))
        
        # Initialize error return value
        error_return_value = {
            "error": ValueError("The run did not complete successfully.")
        }
            
        # Create thread and process agent run with retries
        for attempt in range(1, max_retries + 1):
            try:
                # Create thread for communication
                thread = create_thread(agents_client, utterance)

                # Create and process the agent run
                run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
                _logger.info(f"Run attempt {attempt} finished with status: {run.status}")

                # Check the run status
                if run.status == "completed":
                    # If run is successful, handle the response
                    return handle_successful_run(agents_client, thread, attempt)

            # Handle exceptions during agent run processing
            except Exception as e:
                _logger.error(f"Logging error {e}")
                error_return_value["error"] = e
                _logger.error(f"Agent run {attempt + 1} failed with exception: {e}. Retrying...")
        
        # If all attempts fail, return the error
        return error_return_value

    return triage_agent_router


def create_thread(
    agents_client: AgentsClient,
    utterance: str
) -> AgentThread:
    """
    Helper function to create a thread for the agent run.
    """
    # Create thread for communication
    thread = agents_client.threads.create()
    _logger.info(f"Created thread, ID: {thread.id}")

    # Create and add user message to thread
    message = agents_client.messages.create(
        thread_id=thread.id,
        role="user",
        content=utterance,
    )
    _logger.info(f"Created message: {message['id']}")
    
    return thread

def handle_successful_run(
    agents_client: AgentsClient,
    thread: AgentThread, 
    attempt: int
) -> dict:
    """
    Helper function to handle a successful agent run
    """
    # Parse the agent response from the successful run
    _logger.info(f"Agent run succeeded on attempt {attempt}.")
    messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    for msg in messages:
        # Grab the last text message from the assistant
        if msg.text_messages and msg.role == "assistant":
            last_text = msg.text_messages[-1]
            _logger.info(f"{msg.role}: {last_text.text.value}")

            # Load the agent response into a JSON
            try:
                data = json.loads(last_text.text.value)
                _logger.info(f"Agent response parsed successfully: {data}")
                parsed_result = parse_response(data)
                return parsed_result
            
            # Raise error if agent response cannot be parsed
            except Exception as e:
                _logger.error(f"Agent response failed with error: {e}")
                raise ValueError(f"Failed to parse agent response: {e}")
            
    # If no valid response found, raise an error to be handled by the caller
    _logger.error("No valid agent response found in the thread.")
    raise ValueError("No valid agent response found in the thread.")

def parse_response(
    response: dict
) -> dict:
    """
    Parse Triage Agent Message response.
    """
    # Check tool kind used by the agent
    kind = response["type"]
    error = None
    parsed_result = {}

    # Parse the response based on tool used
    if kind == "clu_result":
        parsed_result = parse_clu_response(
            response=response["response"]
        )
    elif kind == "cqa_result":
        parsed_result = parse_cqa_response(
            response=response["response"]
        )
    else:
        error = f"Unexpected agent intent kind: {kind}"

    if error is not None:
        parsed_result["error"] = error
    parsed_result["api_response"] = response["response"]

    return parsed_result

