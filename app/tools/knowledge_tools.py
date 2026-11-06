"""Knowledge tools: policy search, coupons, warranty and escalation."""

from pydantic import BaseModel, Field

from app.core.enums import ToolRisk
from app.retrieval.hybrid import HybridRetriever
from app.schemas.agent import ToolResult
from app.tools.base import Tool, ToolContext


class KnowledgeSearchInput(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=200,
        description="A short question about a store policy. Do not enter an order number.",
    )


class CouponInput(BaseModel):
    user_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional authenticated demo user ID, such as u_demo. Do not enter an email address or phone number.",
    )


class WarrantyInput(BaseModel):
    sku: str = Field(
        min_length=2,
        max_length=32,
        description="Product SKU, such as SKU-A1. Do not enter a product name.",
    )


class SearchKnowledgeTool(Tool):
    name = "search_knowledge"
    description = (
        "Search FAQ, returns, shipping, and other published policies. This tool does not look up account-specific orders or inventory. "
        "Use for general eligibility, timing, shipping, or return-policy questions. Use get_coupon for coupon details, get_warranty for a known SKU, mcp_store_hours for support hours, and mcp_warehouse_cutoff for dispatch cutoffs. "
        "The query must be 1–200 characters and must not contain an order number. "
        "Returns chunks with IDs, titles, and excerpts. Treat excerpts as policy evidence, never as facts about a particular order."
    )
    risk = ToolRisk.READ
    input_model = KnowledgeSearchInput

    def __init__(self, retriever: HybridRetriever) -> None:
        self._retriever = retriever

    async def execute(self, parsed: KnowledgeSearchInput, context: ToolContext) -> ToolResult:
        chunks = await self._retriever.retrieve(parsed.query, top_k=4)
        return ToolResult(
            name=self.name,
            success=True,
            output={
                "chunks": [
                    {"chunk_id": c.chunk_id, "title": c.title, "content": c.content[:400]}
                    for c in chunks
                ]
            },
        )


class GetCouponTool(Tool):
    name = "get_coupon"
    description = (
        "Read the current coupon codes and combination rules. This tool does not apply or claim a coupon. "
        "Use for coupon availability, stacking, and discounts. Use get_order for the amount paid. "
        "The optional user_id is a demo account ID, not an email address or phone number. "
        "Returns coupon codes and descriptions; do not claim a coupon is already in the customer account."
    )
    risk = ToolRisk.READ
    input_model = CouponInput

    async def execute(self, parsed: CouponInput, context: ToolContext) -> ToolResult:
        return ToolResult(
            name=self.name,
            success=True,
            output={
                "coupons": [
                    {
                        "code": "NEW10",
                        "desc": "$10 off orders of $99 or more; cannot be combined with category coupons",
                    },
                    {
                        "code": "SHIP0",
                        "desc": "Free standard shipping on eligible orders; remote-area surcharges may apply",
                    },
                ]
            },
        )


class GetWarrantyTool(Tool):
    name = "get_warranty"
    description = (
        "Return a structured warranty duration and exclusions for a known SKU. "
        "Use search_knowledge for general warranty policies and get_product_detail for price or specifications. "
        "Returns SKU, warranty months, and a short note. Do not promise coverage beyond the returned note."
    )
    risk = ToolRisk.READ
    input_model = WarrantyInput

    async def execute(self, parsed: WarrantyInput, context: ToolContext) -> ToolResult:
        return ToolResult(
            name=self.name,
            success=True,
            output={
                "sku": parsed.sku,
                "warranty_months": 12,
                "note": "Accidental damage is excluded; see the order page for proof of purchase.",
            },
        )


class EscalateInput(BaseModel):
    reason: str = Field(
        min_length=1,
        max_length=200,
        description="A short reason for human review. Do not use an order number as the reason.",
    )


class EscalateToHumanTool(Tool):
    name = "escalate_to_human"
    description = (
        "Create a ticket for the human-support queue. This tool does not look up orders or answer policy questions. "
        "Use when the customer explicitly requests a person or when available lookup tools cannot resolve a sensitive issue. "
        "Try the relevant read-only tools first when they can answer the question. "
        "The reason must be 1–200 characters. Returns a queued ticket, not a connected live agent."
    )
    risk = ToolRisk.EXTERNAL
    input_model = EscalateInput

    async def execute(self, parsed: EscalateInput, context: ToolContext) -> ToolResult:
        return ToolResult(
            name=self.name,
            success=True,
            output={
                "ticket_id": f"t_{context.session_id[:10]}",
                "queue": "human",
                "reason": parsed.reason,
            },
        )
