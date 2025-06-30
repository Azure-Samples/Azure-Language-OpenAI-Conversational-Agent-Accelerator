# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from semantic_kernel.functions import kernel_function

"""
Sample plugin for processing refunds in a customer support system - this plugin simulates the refund process
and is used with a chat completion agent in a handoff orchestration system.
"""
class OrderRefundPlugin:
    @kernel_function
    def process_refund(self, order_id: str) -> str:
        """Process a refund for an order."""
        # Simulate processing a refund
        print(f"[RefundPlugin] Processing refund for order {order_id}")
        return f"Refund for order {order_id} has been processed successfully."