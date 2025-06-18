from semantic_kernel.functions import kernel_function

"""
Sample plugin for processing returns in a customer support system - this plugin simulates the return process
and is used with a chat completion agent in a handoff orchestration system.
"""
class OrderReturnPlugin:
    @kernel_function
    def process_return(self, order_id: str, reason: str) -> str:
        """Process a return for an order."""
        # Simulate processing a return
        print(f"Processing return for order {order_id} due to: {reason}")
        return f"Return for order {order_id} has been processed successfully."