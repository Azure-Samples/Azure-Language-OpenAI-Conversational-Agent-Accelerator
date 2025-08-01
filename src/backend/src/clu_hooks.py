# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
"""
Contoso-Outdoors example function hooks for each CLU intent:
"""


def get_order_id(entities: list[dict]) -> str:
    triage_agent = os.environ.get("ROUTER_TYPE") == "TRIAGE_AGENT"

    for ent in entities:
        if (triage_agent and ent.get("name") == "OrderId") or (ent.get("category") == "OrderId"):
            return ent["text"]
    return None


def CancelOrder(entities: list[dict]) -> str:
    order_id = get_order_id(entities)

    if not order_id:
        return "Please specify order ID in order to cancel order."

    return f"Order {order_id} has successfully been cancelled."


def RefundStatus(entities: list[dict]) -> str:
    order_id = get_order_id(entities)

    if not order_id:
        return "Please specify order ID in order to check refund status."

    return f"Refund is still processing for order {order_id}."


def OrderStatus(entities: list[dict]) -> str:
    order_id = get_order_id(entities)

    if not order_id:
        return "Please specify order ID in order to check order status."

    return f"Order {order_id} has shipped."
