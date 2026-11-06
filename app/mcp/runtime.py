"""Local and remote MCP backends behind the same call_tool contract."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.exceptions import ToolExecutionError

LOCAL_CATALOG: list[dict[str, str]] = [
    {
        "name": "mcp_store_hours",
        "description": (
            "Check customer-support hours and whether refund requests are reviewed overnight. "
            "Use for questions about weekday, weekend, or overnight availability. "
            "Use mcp_warehouse_cutoff for dispatch cutoffs, search_knowledge for refund policies, and get_refund_status for an existing refund. "
            "No parameters are required. Returns weekday and weekend hours and whether overnight refund review is available. Do not promise an overnight refund when review is unavailable."
        ),
        "transport": "local",
    },
    {
        "name": "mcp_warehouse_cutoff",
        "description": (
            "Check the warehouse cutoff for possible same-day dispatch. "
            "Use for questions about the order time required for same-day shipping. "
            "Use track_shipment for carrier tracking, mcp_store_hours for support hours, and search_knowledge for shipping policies. "
            "No parameters are required. Returns the cutoff time; payment before the cutoff does not guarantee same-day dispatch."
        ),
        "transport": "local",
    },
]

_LOCAL_HANDLERS: dict[str, dict[str, Any]] = {
    "mcp_store_hours": {
        "weekday": "09:00-21:00",
        "weekend": "10:00-18:00",
        "night_refund_review": False,
        "source": "mcp_local",
    },
    "mcp_warehouse_cutoff": {
        "cutoff": "16:00",
        "same_day_if_paid_before": "16:00",
        "source": "mcp_local",
    },
}


async def call_mcp_tool(
    *,
    name: str,
    arguments: dict[str, Any],
    transport: str,
    endpoint: str = "",
) -> dict[str, Any]:
    if transport == "local":
        if name not in _LOCAL_HANDLERS:
            raise ToolExecutionError(f"unknown local MCP tool: {name}")
        return {**_LOCAL_HANDLERS[name], "arguments": arguments}
    if not endpoint:
        raise ToolExecutionError(f"remote MCP tool {name} has no endpoint")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                endpoint,
                json={"name": name, "arguments": arguments},
                headers={"content-type": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise ToolExecutionError(f"remote MCP transport error: {name}") from exc
    if response.status_code >= 400:
        raise ToolExecutionError(f"remote MCP HTTP {response.status_code}")
    body = response.json()
    if not isinstance(body, dict):
        raise ToolExecutionError("remote MCP returned non-object JSON")
    return body
