# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from semantic_kernel.functions import kernel_function

"""
Sample plugin for processing cancellations in a customer support system - this plugin simulates the cancellation process
and is used with a chat completion agent in a handoff orchestration system.
"""
class OrderCancellationPlugin:
    @kernel_function
    def process_cancellation(self, order_id: str) -> str:
        """Process a cancellation for an order."""
        # Simulate processing a cancellation
        print(f"[CancellationPlugin] Processing cancellation for order {order_id}")
        return f"Cancellation for order {order_id} has been processed successfully."