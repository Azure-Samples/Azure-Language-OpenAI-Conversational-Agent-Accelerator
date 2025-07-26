# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import pytest
import os
import sys
import subprocess
import requests
import time
from typing import Generator

"""
This module contains test cases for the chat endpoint of the FastAPI application.
It includes single-turn and multi-turn interactions with parameterized test cases.
The tests are designed to validate the responses from the chat endpoint based on predefined scenarios.

Launch this test suite using pytest:
cd src/backend/src/
pytest test/test_chat.py -s -v
"""

# Test cases for the chat endpoint
SINGLE_TURN_TEST_CASES = [
    {
        "name": "return_policy",
        "current_question": "What is the return policy",
        "history": [
            {
                "role": "",
                "content": ""
            }
        ],
        "expected_response": [
            "Contoso Outdoors is proud to offer a 30 day refund policy. Return unopened, unused products within 30 days of purchase to any Contoso Outdoors store for a full refund."
        ]
    },
    {
        "name": "order_status",
        "current_question": "What is the status of order 12345?",
        "history": [
            {
                "role": "",
                "content": ""
            }
        ],
        "expected_response": ["Order 12345 is shipped and will arrive in 2-3 days."]
    },
    {
        "name": "order_refund",
        "current_question": "I want to refund order 0984",
        "history": [
            {
                "role": "",
                "content": ""
            }
        ],
        "expected_response": ["Refund for order 0984 has been processed successfully."]
    },
    {
        "name": "order_cancel",
        "current_question": "Please cancel my order 56789",
        "history": [
            {
                "role": "",
                "content": ""
            }
        ],
        "expected_response": ["Cancellation for order 56789 has been processed successfully."]
    },
    {
        "name": "need_more_info_refund",
        "current_question": "Was I refunded for my order?",
        "history": [
            {
                "role": "",
                "content": ""
            }
        ],
        "expected_response": ["Please provide more information about your order so I can better assist you."]
    },
    {
        "name": "need_more_info_order_status",
        "current_question": "I want to know the status of my order",
        "history": [
            {
                "role": "",
                "content": ""
            }
        ],
        "expected_response": ["Please provide more information about your order so I can better assist you."]
    },
    {
        "name": "need_more_info_order_cancel",
        "current_question": "I want to cancel my order",
        "history": [
            {
                "role": "",
                "content": ""
            }
        ],
        "expected_response": ["Please provide more information about your order so I can better assist you."]
    },
    {
        "name": "spanish_refund",
        "current_question": "Quiero un reembolso por mi pedido 091428",
        "history": [
            {
                "role": "",
                "content": ""
            }
        ],
        "expected_response": ["Reembolso por pedido 091428 se ha procesado con éxito."]
    }
]


MULTI_TURN_TEST_CASES = [
    {
        "name": "multi_turn_order_status",
        "sequence": [
            {
                "current_question": "What is the status of my order?",
                "history": [
                    {
                        "role": "",
                        "content": ""
                    }
                ],
                "expected_response": ["Please provide more information about your order so I can better assist you."]
            },
            {
                "current_question": "My order number is 12345",
                "history": [
                    {
                        "role": "User",
                        "content": "What is the status of my order?"
                    },
                    {
                        "role": "System",
                        "content": "Please provide more information about your order so I can better assist you."
                    }
                ],
                "expected_response": ["Order 12345 is shipped and will arrive in 2-3 days."]
            }
        ]
    },
    {
        "name": "multi_turn_order_refund",
        "sequence": [
            {
                "current_question": "I want to refund my order",
                "history": [
                    {
                        "role": "",
                        "content": ""
                    }
                ],
                "expected_response": ["Please provide more information about your order so I can better assist you."]
            },
            {
                "current_question": "My order number is 0984",
                "history": [
                    {
                        "role": "User",
                        "content": "I want to refund my order"
                    },
                    {
                        "role": "System",
                        "content": "Please provide more information about your order so I can better assist you."
                    }
                ],
                "expected_response": ["Refund for order 0984 has been processed successfully."]
            }
        ]
    },
    {
        "name": "multi_turn_order_cancel",
        "sequence": [
            {
                "current_question": "I want to cancel my order",
                "history": [
                    {
                        "role": "",
                        "content": ""
                    }
                ],
                "expected_response": ["Please provide more information about your order so I can better assist you."]
            },
            {
                "current_question": "My order number is 56789",
                "history": [
                    {
                        "role": "User",
                        "content": "I want to cancel my order"
                    },
                    {
                        "role": "System",
                        "content": "Please provide more information about your order so I can better assist you."
                    }
                ],
                "expected_response": ["Cancellation for order 56789 has been processed successfully."]
            }
        ]
    },
    {
        "name": "multi_turn_spanish_refund",
        "sequence": [
            {
                "current_question": "Quiero un reembolso por mi pedido",
                "history": [
                    {
                        "role": "",
                        "content": ""
                    }
                ],
                "expected_response": ["Por favor, proporcione más información sobre su pedido para que pueda ayudarle mejor."]
            },
            {
                "current_question": "Mi número de pedido es 091428",
                "history": [
                    {
                        "role": "User",
                        "content": "Quiero un reembolso por mi pedido"
                    },
                    {
                        "role": "System",
                        "content": "Por favor, proporcione más información sobre su pedido para que pueda ayudarle mejor."
                    }
                ],
                "expected_response": ["Reembolso por pedido 091428 se ha procesado con éxito."]
            }
        ]
    },
    {
        "name": "multi_turn_english_and_spanish",
        "sequence": [
            {
                "current_question": "What is the return policy?",
                "history": [
                    {
                        "role": "",
                        "content": ""
                    }
                ],
                "expected_response": [
                    "Contoso Outdoors is proud to offer a 30 day refund policy. Return unopened, unused products within 30 days of purchase to any Contoso Outdoors store for a full refund."
                ]
            },
            {
                "current_question": "Quiero cancelar mi pedido",
                "history": [
                    {
                        "role": "",
                        "content": ""
                    }
                ],
                "expected_response": ["Por favor, proporcione más información sobre su pedido para que pueda ayudarle mejor."]
            },
            {
                "current_question": "El numero de mi pedido es 12345",
                "history": [
                    {
                        "role": "User",
                        "content": "Quiero cancelar mi pedido"
                    },
                    {
                        "role": "System",
                        "content": "Por favor, proporcione más información sobre su pedido para que pueda ayudarle mejor."
                    }
                ],
                "expected_response": ["La cancelación del pedido 12389798457 se ha procesado correctamente."]
            }
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


# Test the chat endpoint with parameterized test cases for single turn interactions
@pytest.mark.parametrize("test_case", SINGLE_TURN_TEST_CASES, ids=lambda x: x["name"])
def test_single_turn(uvicorn_server: str, test_case: dict):
    """Test chat endpoint responses"""

    response = requests.post(
        f"{uvicorn_server}/chat",
        json={"message": test_case["current_question"], "history": test_case["history"]},
    )

    # Check response
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    data = response.json()

    # Verify response
    assert data["messages"] == test_case["expected_response"], (
        f"Response mismatch for test '{test_case['name']}'. "
        f"Expected: {test_case['expected_response']}, Actual: {data['messages']}"
    )


# Test the chat endpoint with a multi-turn conversation
@pytest.mark.parametrize("test_case", MULTI_TURN_TEST_CASES, ids=lambda x: x["name"])
def test_multi_turn(uvicorn_server: str, test_case: dict):
    """Test multi-turn chat endpoint responses"""

    for step in test_case["sequence"]:
        response = requests.post(
            f"{uvicorn_server}/chat",
            json={"message": step["current_question"], "history": step["history"]},
            timeout=180
        )

        # Check response
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        data = response.json()

        # Verify response
        assert data["messages"] == step["expected_response"], (
            f"Response mismatch for test '{test_case['name']}'. "
            f"Expected: {step['expected_response']}, Actual: {data['messages']}"
        )
