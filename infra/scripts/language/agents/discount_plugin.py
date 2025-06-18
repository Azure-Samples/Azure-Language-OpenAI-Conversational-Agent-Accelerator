from semantic_kernel.functions import kernel_function

"""
Sample plugin for processing discounts in a customer support system - this plugin simulates the discount process
"""
class OrderDiscountPlugin:
    @kernel_function
    def apply_discount(self, order_id: str, discount_code: str) -> str:
        """Apply a discount to an order."""
        # Simulate applying a discount
        print(f"Applying discount code '{discount_code}' to order {order_id}.")
        return f"Discount code '{discount_code}' has been applied to order {order_id} successfully."