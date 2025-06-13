# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
import logging
import pii_redacter
from typing import Callable
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ListSortOrder
from router.clu_router import parse_response as parse_clu_response
from router.cqa_router import parse_response as parse_cqa_response
from utils import get_azure_credential

_logger = logging.getLogger(__name__)

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
        try: 
            # Process the agent run and handle retries
            max_retries = int(os.environ.get("MAX_AGENT_RETRY", 3))
            for attempt in range(1, max_retries + 1):
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

                # Create and process the agent run
                run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
                _logger.info(f"Run attempt {attempt} finished with status: {run.status}")

                if run.status == "completed":
                    # Fetch and log all messages if successful run
                    messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
                    for msg in messages:
                        if msg.text_messages:
                            last_text = msg.text_messages[-1]
                            _logger.info(f"{msg.role}: {last_text.text.value}")

                            # Load the agent response into a JSON
                            if msg.role == "assistant" :
                                # Check if agent response is able to be parsed
                                try:
                                    _logger.info(f"Agent response parsed successfully: {last_text.text.value}")
                                    data = json.loads(last_text.text.value)
                                    _logger.info(f"Agent response parsed successfully: {data}")
                                    parsed_result = parse_response(data)
                                    return parsed_result
                                
                                except Exception as e:
                                    _logger.error(f"Runtime call failed with error: {e}")
                                    if attempt == max_retries:
                                        return {
                                            "error": e
                                        }
                                    else:
                                        # Exit the inner loop to retry agent run
                                        _logger.info(f"Retrying agent run due to runtime error... Attempt {attempt + 1}/{max_retries}")
                                        break
            
                # If run fails, handle retries or raise an error if max retries reached
                elif attempt == max_retries:
                    _logger.error(f"Run failed after {max_retries} attempts: {run.last_error}")
                    _logger.error(f"Runtime call failed with error: {e}")
                    return {
                         "error": e
                    }
                
                else:
                    _logger.warning(f"Run failed on attempt {attempt}: {run.last_error}. Retrying...")
        
        # Add error handling for unexpected exceptions
        except Exception as e:
            _logger.error(f"An error occurred while processing the triage agent: {e}")
            return {
                "error": e
            }

            _logger.info(f"Triage agent did not return a value.")

    return triage_agent_router

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

