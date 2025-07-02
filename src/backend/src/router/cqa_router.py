# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import logging
from typing import Callable
from azure.ai.language.questionanswering import QuestionAnsweringClient
from utils import get_azure_credential

_logger = logging.getLogger(__name__)


def create_cqa_router() -> Callable[[str, str, str], dict]:
    """
    Create CQA runtime routing function.
    """
    project_name = os.environ['CQA_PROJECT_NAME']
    deployment_name = os.environ['CQA_DEPLOYMENT_NAME']
    endpoint = os.environ['LANGUAGE_ENDPOINT']
    credential = get_azure_credential()
    client = QuestionAnsweringClient(endpoint, credential)

    def call_runtime(
        question: str,
        language: str,
        id: str
    ) -> dict:
        """
        Call CQA runtime.
        """
        try:
            _logger.info(f"Calling {project_name}:{deployment_name} runtime")

            response = client.get_answers(
                question=question,
                top=1,
                project_name=project_name,
                deployment_name=deployment_name
            )

            _logger.info(f"Runtime response: {response}")
            return parse_response_sdk(
                response=response
            )

        except Exception as e:
            _logger.error(f"Runtime call failed: {e}")
            return {
                "error": e
            }

    return call_runtime


def parse_response_sdk(
    response: dict
) -> dict:
    """
    Parse CQA runtiem response from SDK.
    """
    confidence_threshold = float(os.environ.get("CQA_CONFIDENCE_THRESHOLD", "0.5"))
    top_answer = response.answers[0]
    confidence = top_answer.confidence
    answer = top_answer.answer
    answer_id = top_answer.qna_id
    question = None
    error = None

    # Filter based on confidence threshold:
    if confidence < confidence_threshold:
        _logger.warning("CQA confidence threshold not met")
        error = "CQA confidence threshold not met"

    # Filter based on answer id:
    if answer_id == -1:
        # -1 means default answer was returned.
        _logger.warning("No answer found")
        error = "No answer found"
    else:
        question = top_answer.questions[0]

    return {
        "kind": "cqa_result",
        "error": error,
        "answer": answer,
        "question": question,
        "confidence": confidence,
        "api_response": response
    }


def parse_response(
    response: dict
) -> dict:
    """
    Parse CQA runtime response (JSON output).
    """
    confidence_threshold = float(os.environ.get("CQA_CONFIDENCE_THRESHOLD", "0.5"))

    answer = None
    question = None
    confidence = None
    error = None

    # Filter based on answer id:
    if len(response["answers"]) == 0 or response["answers"][0]["id"] == -1:
        # -1 means default answer was returned.
        _logger.warning("No answer found")
        error = "No answer found"

    # Filter based on confidence threshold:
    elif response["answers"][0]["confidenceScore"] < confidence_threshold:
        _logger.warning("CQA confidence threshold not met")
        error = "CQA confidence threshold not met"

    # Happy path:
    else:
        top_answer = response["answers"][0]
        answer = top_answer["answer"]
        question = top_answer["questions"][0]
        confidence = top_answer["confidenceScore"]

    return {
        "kind": "cqa_result",
        "error": error,
        "answer": answer,
        "question": question,
        "confidence": confidence,
        "api_response": response
    }
