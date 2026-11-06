"""Terminal rendering helpers for the interactive CLI.

Pure formatting functions plus the stdout writers shared by the client and the
command layer. Kept free of I/O beyond ``stdout`` so it stays easy to test.
"""

from __future__ import annotations

import ast
import json
import sys
from typing import Any

NODE_LABELS = {
    "apply_guardrail": "guardrail",
    "classify_intent": "intent",
    "route_complexity": "route",
    "retrieve_docs": "retrieval",
    "plan_tasks": "plan",
    "execute_tools": "execute",
    "generate_answer": "generate",
    "refuse_answer": "refuse",
    "check_faithfulness": "faithfulness",
    "compact_memory": "memory",
}

HELP = """Type a question and press Enter, then keep asking.
  /help  command list
  /new   start a new session
  /y     confirm a write action (refund/cancel etc.)
  /n     dismiss the pending confirmation
  /quit  exit
Demo orders: ORD10001 shipped headphones - ORD10002 delivered personalized mug - ORD10003 unshipped T-shirt
"""


def parse_sse_data_line(line: str) -> dict[str, Any] | None:
    """Parse one SSE ``data:`` line into a dict, or return None for noise."""
    stripped = line.strip()
    if not stripped.startswith("data:"):
        return None
    payload = stripped[5:].strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        parsed: Any = json.loads(payload)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(payload)
        except (SyntaxError, ValueError):
            return None
    return parsed if isinstance(parsed, dict) else None


def format_meta(body: dict[str, Any]) -> str:
    """Render the one-line metadata summary shown under each answer."""
    bits = [
        body.get("intent") or "-",
        body.get("strategy") or "-",
        body.get("complexity") or "-",
    ]
    total = (body.get("latency") or {}).get("total_ms")
    if isinstance(total, int | float):
        bits.append(f"{total / 1000:.1f}s")
    return " · ".join(str(item) for item in bits)


def emit(text: str) -> None:
    """Write text to stdout and flush, so streaming output appears immediately."""
    sys.stdout.write(text)
    sys.stdout.flush()


def apply_event(
    event: dict[str, Any], *, show_tokens: bool, printed_nodes: bool
) -> tuple[dict[str, Any] | None, bool]:
    """Render one stream event; return the final answer body when it arrives."""
    kind = event.get("event")
    if kind == "node":
        node = str(event.get("node") or "")
        label = NODE_LABELS.get(node, node)
        prefix = "" if printed_nodes else "  "
        emit(f"{prefix}[{label}]")
        return None, True
    if kind == "token" and show_tokens:
        emit(str(event.get("text") or ""))
        return None, printed_nodes
    if kind == "answer":
        data = event.get("data")
        if isinstance(data, dict):
            return data, printed_nodes
    return None, printed_nodes
