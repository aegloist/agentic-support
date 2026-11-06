"""Order tools: order and item lookup."""

from pydantic import BaseModel, Field

from app.core.enums import ToolRisk
from app.schemas.agent import ToolResult
from app.tools.base import Tool, ToolContext
from app.tools.deps import RepositoryBackedTool


class OrderIdInput(BaseModel):
    order_id: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Order number, e.g. ORD1001; do not pass a tracking number, user_id, or phone number",
    )


class GetOrderTool(RepositoryBackedTool, Tool):
    name = "get_order"
    description = (
        "Look up an order header by order number: status, amounts, payment/shipping/delivery times, and a tracking-number summary."
        "When to use: the user asks whether payment succeeded, about order status, amounts, or whether an order has shipped."
        "When not to use: for tracking only use track_shipment; for item details only use get_order_items; for refund records only use get_refund_status."
        "Prefer get_order when the user asks about status/amount/payment; use track_shipment when they ask where the parcel is."
        "Parameter order_id: 3-32 chars of letters, digits, - or _, e.g. ORD1001; do not pass SF123456 or u_demo."
        "Returns status, total_cents (unit: cents), paid_at/shipped_at/delivered_at, tracking_no; call get_order_items afterwards if item details are needed."
    )
    risk = ToolRisk.READ
    input_model = OrderIdInput

    async def execute(self, parsed: OrderIdInput, context: ToolContext) -> ToolResult:
        order = await self.repository.get_visible_order(parsed.order_id, context.user_id)
        return ToolResult(name=self.name, success=True, output=order.model_dump(mode="json"))


class GetOrderItemsTool(RepositoryBackedTool, Tool):
    name = "get_order_items"
    description = (
        "Look up item details within an order: SKU, name, quantity, unit price, and whether the item is customized."
        "When to use: the user asks what they bought, whether an item can be returned, whether it is customized, or if the quantity is correct."
        "When not to use: for order status or amount due use get_order."
        "Prefer get_order when only status/amount is needed; otherwise use this tool for line items."
        "Parameter order_id: same as get_order, e.g. ORD1001; not a sku or a product name."
        "Returns items[]: sku, name, quantity, unit_price_cents (in cents), customized; later returns/refunds should be based on customized and sku."
    )
    risk = ToolRisk.READ
    input_model = OrderIdInput

    async def execute(self, parsed: OrderIdInput, context: ToolContext) -> ToolResult:
        order = await self.repository.get_visible_order(parsed.order_id, context.user_id)
        return ToolResult(
            name=self.name,
            success=True,
            output={"items": [item.model_dump() for item in order.items]},
        )
