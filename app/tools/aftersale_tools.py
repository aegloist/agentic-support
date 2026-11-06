"""After-sale tools: refund, return and order cancellation."""

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
        description="Order number, e.g. ORD1001; do not pass a refund_id or user_id",
    )


class RefundCreateInput(BaseModel):
    order_id: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Order number to file the after-sale request for, e.g. ORD1001",
    )
    reason: str = Field(
        min_length=1,
        max_length=200,
        description="The user's stated reason, 1-200 chars, e.g. 'size doesn't fit'; do not put an order number here",
    )


class GetRefundStatusTool(RepositoryBackedTool, Tool):
    name = "get_refund_status"
    description = (
        "Read-only lookup of an order's existing refund requests (IDs, statuses, amounts)."
        "When to use: where a refund is, refund request status, or how much is being refunded."
        "When not to use: if no request has been filed and the user wants to submit one, use create_refund_request; to check whether an order was paid use get_order."
        "Prefer this tool once a request exists and only progress is being checked; do not use it as a substitute for filing a new refund."
        "Parameter order_id: e.g. ORD1001, not a refund_id (rf_...) or user_id."
        "Returns refunds[{refund_id, status, amount_cents}]; an empty list means no refund request exists yet, so do not claim a refund has been issued."
    )
    risk = ToolRisk.READ
    input_model = OrderIdInput

    async def execute(self, parsed: OrderIdInput, context: ToolContext) -> ToolResult:
        await self.repository.get_visible_order(parsed.order_id, context.user_id)
        refunds = await self.repository.get_refunds(parsed.order_id)
        return ToolResult(
            name=self.name,
            success=True,
            output={
                "refunds": [
                    {
                        "refund_id": row.refund_id,
                        "status": row.status,
                        "amount_cents": row.amount_cents,
                    }
                    for row in refunds
                ]
            },
        )


class CreateRefundRequestTool(RepositoryBackedTool, Tool):
    name = "create_refund_request"
    description = (
        "Files a refund request (destructive; only truly executed after user confirmation). Refund only — does not create a return."
        "When to use: the user explicitly asks for money back or to file a refund, and an order number is on hand."
        "When not to use: for refund rules only use search_knowledge; to check progress use get_refund_status; for sending an item back use create_return_request; to cancel an unshipped order use cancel_order."
        "Priority: cancel an unshipped order → cancel_order; return a shipped item → create_return_request; refund only (no send-back) → this tool."
        "Parameters: order_id e.g. ORD1001; reason 1-200 chars stating why, e.g. 'no longer needed'; never put the order_id into the reason."
        "A return of {refund_id, status: requested, order_id} means the request was accepted, not that the money has arrived."
    )
    risk = ToolRisk.DESTRUCTIVE
    input_model = RefundCreateInput

    async def execute(self, parsed: RefundCreateInput, context: ToolContext) -> ToolResult:
        await self.repository.get_visible_order(parsed.order_id, context.user_id)
        output = await self.repository.create_refund(
            order_id=parsed.order_id,
            reason=parsed.reason,
            trace_id=context.trace_id,
        )
        return ToolResult(name=self.name, success=True, output=output)


class CreateReturnRequestTool(RepositoryBackedTool, Tool):
    name = "create_return_request"
    description = (
        "Creates a return request (write; only truly executed after user confirmation). Does not automatically refund."
        "When to use: the user wants to send an item back or exchange it."
        "When not to use: for refund rules only use search_knowledge; to cancel an unshipped order use cancel_order; for return policy questions use search_knowledge or get_order_items; for sending money back use create_refund_request."
        "Priority: cancel an unshipped order → cancel_order; refund only → create_refund_request; need to send the item back → this tool."
        "Parameters: order_id e.g. ORD1001; reason 1-200 chars, e.g. 'size doesn't fit'."
        "Returns {return_id, order_id, status: requested}; do not claim a refund has already been issued."
    )
    risk = ToolRisk.WRITE
    input_model = RefundCreateInput

    async def execute(self, parsed: RefundCreateInput, context: ToolContext) -> ToolResult:
        await self.repository.get_visible_order(parsed.order_id, context.user_id)
        output = await self.repository.create_return(
            order_id=parsed.order_id,
            reason=parsed.reason,
            trace_id=context.trace_id,
        )
        return ToolResult(name=self.name, success=True, output=output)


class CancelOrderTool(RepositoryBackedTool, Tool):
    name = "cancel_order"
    description = (
        "Cancels an order that has not shipped yet (destructive; requires user confirmation). Only succeeds when the order status is created or paid."
        "When to use: the user wants to cancel an order that has not shipped."
        "When not to use: do not call for shipped or delivered orders, it will fail and a return via create_return_request is the right path. Do not use this to file a refund request."
        "Priority: canceling an unshipped order → use this tool; returning a shipped item → create_return_request."
        "Parameter: order_id, e.g. ORD1001; do not pass a sku."
        "Returns {order_id, status: cancelled}; failure usually means the order has shipped or its status does not allow cancellation."
    )
    risk = ToolRisk.DESTRUCTIVE
    input_model = OrderIdInput

    async def execute(self, parsed: OrderIdInput, context: ToolContext) -> ToolResult:
        await self.repository.get_visible_order(parsed.order_id, context.user_id)
        output = await self.repository.cancel_order(parsed.order_id, trace_id=context.trace_id)
        return ToolResult(name=self.name, success=True, output=output)
