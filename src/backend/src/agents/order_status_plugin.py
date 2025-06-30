# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from semantic_kernel.functions import kernel_function

"""
Sample plugin for returning order status in a customer support system - this plugin states order status
and is used with a chat completion agent in a handoff orchestration system.
"""
class OrderStatusPlugin:
    @kernel_function
    def check_order_status(self, order_id: str) -> str:
        """Check the status of an order."""
        print(f"[OrderStatusPlugin] Checking status for order {order_id}")
        return f"Order {order_id} is shipped and will arrive in 2-3 days."