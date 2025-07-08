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
        "name": "order_status_single_utterance",
        "input": "What's the status of order 12345?",
        "expected_response": ["Order 12345 is shipped and will arrive in 2-3 days."]
    },
    {
        "name": "order_refund_single_utterance",
        "input": "I want to check on my refund for order 0984?",
        "expected_response": ["Refund for order 0984 has been processed successfully."]
    },
    {
        "name": "order_cancel_single_utterance",
        "input": "Please cancel my order 56789",
        "expected_response": ["Cancellation for order 56789 has been processed successfully."]
    },
    {
        "name": "return_policy",
        "input": "What is the return policy",
        "expected_response": [
            "Contoso Outdoors is proud to offer a 30 day refund policy. Return unopened, unused products within 30 days of purchase to any Contoso Outdoors store for a full refund."
        ]
    },
    {
        "name": "multiple_utterances",
        "input": "What's the status of order 0913280918409? Please cancel my order 62346?",
        "expected_response": [
            "Order 0913280918409 is shipped and will arrive in 2-3 days.",
            "Cancellation for order 62346 has been processed successfully."
        ]
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
    # try:
    #     # Make request
    response = requests.post(
        f"{uvicorn_server}/chat",
        json={"message": test_case["input"]},
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
