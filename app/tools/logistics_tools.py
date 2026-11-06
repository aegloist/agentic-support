"""Logistics tools: shipment tracking."""

from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import ToolRisk
from app.schemas.agent import ToolResult
from app.tools.base import Tool, ToolContext
from app.tools.deps import RepositoryBackedTool


class TrackInput(BaseModel):
    order_id: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Order number, such as ORD1001. Do not enter a carrier tracking number.",
    )


class TrackShipmentTool(RepositoryBackedTool, Tool):
    name = "track_shipment"
    description = (
        "Look up shipment events and the carrier tracking number by order number. "
        "Use for delivery progress, tracking, or confirmation of delivery. Use get_order for payment, amount, or order status; search_knowledge for shipping policies; and mcp_warehouse_cutoff for same-day dispatch cutoffs. "
        "Do not pass a carrier tracking number as order_id. Returns tracking number, destination city, and events. An empty event list means no shipment scan is available; it does not mean delivered."
    )
    risk = ToolRisk.READ
    input_model = TrackInput

    async def execute(self, parsed: TrackInput, context: ToolContext) -> ToolResult:
        order = await self.repository.get_visible_order(parsed.order_id, context.user_id)
        events: list[dict[str, Any]] = []
        if order.paid_at:
            events.append({"status": "warehouse", "at": order.paid_at.isoformat()})
        if order.shipped_at:
            events.append(
                {
                    "status": "in_transit",
                    "tracking_no": order.tracking_no,
                    "at": order.shipped_at.isoformat(),
                }
            )
        if order.delivered_at:
            events.append({"status": "delivered", "at": order.delivered_at.isoformat()})
        return ToolResult(
            name=self.name,
            success=True,
            output={
                "order_id": order.order_id,
                "tracking_no": order.tracking_no,
                "city": order.receiver_city,
                "events": events,
            },
        )
