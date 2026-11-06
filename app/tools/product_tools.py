"""Product tools: search, detail, recommendation and inventory."""

from pydantic import BaseModel, Field

from app.core.enums import ToolRisk
from app.core.exceptions import InvalidRequestError
from app.schemas.agent import ToolResult
from app.tools.base import Tool, ToolContext
from app.tools.deps import RepositoryBackedTool


class SearchInput(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=80,
        description="Product search terms, such as noise-canceling headphones. Do not enter a SKU or order number.",
    )


class SkuInput(BaseModel):
    sku: str = Field(
        min_length=2,
        max_length=32,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Product SKU, such as SKU-A1. Do not enter a product name or order number.",
    )


class RecommendInput(BaseModel):
    category: str | None = Field(
        default=None,
        max_length=32,
        description="Optional product category, such as electronics. Do not enter a SKU.",
    )
    query: str = Field(
        default="",
        max_length=80,
        description="Optional shopping need, such as a birthday gift. Use this or category.",
    )


class SearchProductsTool(RepositoryBackedTool, Tool):
    name = "search_products"
    description = (
        "Search the product catalog by name, category, or attribute; returns up to five matches. "
        "Use for specific searches such as wireless headphones or running shoes. "
        "Use get_product_detail when the SKU is known, recommend_products for open-ended suggestions, and search_knowledge for policy questions. "
        "The query must be 1–80 characters and must not be a SKU or order number. "
        "Returns products with SKU, name, category, price in cents, and inventory."
    )
    risk = ToolRisk.READ
    input_model = SearchInput

    async def execute(self, parsed: SearchInput, context: ToolContext) -> ToolResult:
        products = await self.repository.search_products(parsed.query)
        return ToolResult(
            name=self.name,
            success=True,
            output={"products": [p.model_dump() for p in products]},
        )


class GetProductDetailTool(RepositoryBackedTool, Tool):
    name = "get_product_detail"
    description = (
        "Look up a product by SKU and return its name, category, price, inventory, tags, and description. "
        "Use when the customer asks for details about a known product. Use search_products if the SKU is unknown, check_inventory for stock only, and get_warranty for warranty terms. "
        "The SKU must contain 2–32 letters, digits, underscores, or hyphens. Do not use a product name or order number. Prices are returned in cents."
    )
    risk = ToolRisk.READ
    input_model = SkuInput

    async def execute(self, parsed: SkuInput, context: ToolContext) -> ToolResult:
        product = await self.repository.get_product(parsed.sku)
        if product is None:
            raise InvalidRequestError(f"product not found: {parsed.sku}")
        return ToolResult(name=self.name, success=True, output=product.model_dump())


class RecommendProductsTool(RepositoryBackedTool, Tool):
    name = "recommend_products"
    description = (
        "Recommend up to three products by category or shopping need. "
        "Use for open-ended requests, occasions, or budgets. Use search_products for a specific query and get_product_detail for a known SKU. "
        "Provide category or query; if both are empty, popular items are returned. Do not enter a SKU. "
        "Results are catalog matches, not personalized or live recommendations."
    )
    risk = ToolRisk.READ
    input_model = RecommendInput

    async def execute(self, parsed: RecommendInput, context: ToolContext) -> ToolResult:
        query = parsed.category or parsed.query or "popular"
        products = await self.repository.search_products(query)
        return ToolResult(
            name=self.name,
            success=True,
            output={"products": [p.model_dump() for p in products[:3]]},
        )


class CheckInventoryTool(RepositoryBackedTool, Tool):
    name = "check_inventory"
    description = (
        "Check inventory for a known SKU. Use get_product_detail when price or specifications are also needed, and search_products when the SKU is unknown. "
        "Returns the SKU and stock count; zero means out of stock. Do not invent a restock date."
    )
    risk = ToolRisk.READ
    input_model = SkuInput

    async def execute(self, parsed: SkuInput, context: ToolContext) -> ToolResult:
        product = await self.repository.get_product(parsed.sku)
        if product is None:
            raise InvalidRequestError(f"product not found: {parsed.sku}")
        return ToolResult(
            name=self.name,
            success=True,
            output={"sku": product.sku, "inventory": product.inventory},
        )
