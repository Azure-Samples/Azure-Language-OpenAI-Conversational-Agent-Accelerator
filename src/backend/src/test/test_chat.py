# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import pytest
import os
import sys
import subprocess
import requests
import time
from typing import Generator, List

# Run tests with `pytest test_chat.py -s -v`

# Test cases for the chat endpoint
TEST_CASES = [
    {
        "name": "return_policy",
        "current_question": "What is the return policy",
        "history": "empty",
        "expected_response": [
            "Contoso Outdoors is proud to offer a 30 day refund policy. Return unopened, unused products within 30 days of purchase to any Contoso Outdoors store for a full refund."
        ]
    },
    {
        "name": "order_status",
        "current_question": "What is the status of order 12345?",
        "history": "empty",
        "expected_response": ["Order 12345 is shipped and will arrive in 2-3 days."]
    },
    {
        "name": "order_refund",
        "current_question": "I want to refund order 0984",
        "history": "empty",
        "expected_response": ["Refund for order 0984 has been processed successfully."]
    },
    {
        "name": "order_cancel",
        "current_question": "Please cancel my order 56789",
        "history": "empty",
        "expected_response": ["Cancellation for order 56789 has been processed successfully."]
    },
    {
        "name": "need_more_info_refund",
        "current_question": "Was I refunded for my order?",
        "history": "empty",
        "expected_response": ["Please provide more information about your order so I can better assist you."]
    },
    {
        "name": "need_more_info_order_status",
        "current_question": "I want to know the status of my order",
        "history": "empty",
        "expected_response": ["Please provide more information about your order so I can better assist you."]
    },
    {
        "name": "need_more_info_order_cancel",
        "current_question": "I want to cancel my order",
        "history": "empty",
        "expected_response": ["Please provide more information about your order so I can better assist you."]
    },
    {
        "name": "second_pass_cancel",
        "current_question": "order id 19328",
        "history": "user: I want to cancel my order, system: Please provide more information about your order so I can better assist you.",
        "expected_response": ["Cancellation for order 19328 has been processed successfully."]
    }
]

# Launch the FastAPI server using uvicorn for testing purposes
@pytest.fixture(scope="session")
def uvicorn_server() -> Generator:
    """Start uvicorn server for testing"""
    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    # Start server using python -m
    process = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "app:app",
        "--host", "127.0.0.1",
        "--port", "7000",
        "--reload"
    ], env=env)

    # Wait for server to start
    url = "http://127.0.0.1:7000"
    for _ in range(30):
        try:
            requests.get(url)
            break
        except requests.ConnectionError:
            time.sleep(1)
    
    yield url  # Return the server URL for tests to use
    
    # Cleanup
    process.terminate()
    process.wait()

# Test the chat endpoint with parameterized test cases
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda x: x["name"])
def test_chat_endpoint(uvicorn_server: str, test_case: dict):
    """Test chat endpoint responses"""

    # Create formatted string for input
    formatted_string = f"current question: {test_case["current_question"]}, history: {test_case["history"]}"
    print(formatted_string)

    response = requests.post(
        f"{uvicorn_server}/chat",
        json={"message": formatted_string},
        timeout=180
    )
    
    # Check response
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    data = response.json()
    
    # Verify response
    assert data["messages"] == test_case["expected_response"], (
        f"Response mismatch for test '{test_case['name']}'. "
        f"Expected: {test_case['expected_response']}, Actual: {data['messages']}"
    )
