"""
LangGraph ReAct agent for Bharat Intelligence.

Tools:
  - coral_query: executes SQL through Coral CLI
  - generate_chart: creates base64 PNG charts from tabular JSON
"""

import os
import re
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv(override=True)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from chart import create_chart
from coral_client import (
    execute_sql,
    get_catalog_snapshot,
    profile_table,
    search_catalog,
)
from database import save_query_history


def _build_system_prompt(catalog: dict[str, list[str]], catalog_error: str | None) -> str:
    catalog_lines: list[str] = []
    if catalog_error:
        catalog_lines.append(f"- catalog_error: {catalog_error}")
    elif not catalog:
        catalog_lines.append("- No non-internal schemas are currently installed.")
    else:
        for schema in sorted(catalog.keys()):
            tables = ", ".join(sorted(catalog[schema]))
            catalog_lines.append(f"- {schema}: {tables}")

    catalog_section = "\n".join(catalog_lines)

    return f"""You are Bharat Intelligence, a business analytics assistant.
You answer questions by writing Coral SQL via the coral_query tool.

## Live Coral Catalog (truth source)
{catalog_section}

## Rules
1. Use ONLY schemas/tables listed in the live catalog above.
2. Never claim missing sources unless they are actually missing from catalog.
3. If user asks for unavailable source, say exactly what is available and how to add the missing source.
4. Use short, practical answers. Include key numbers and findings.
5. For trend/revenue tables with numeric outputs, use generate_chart.
6. When you are unsure about table/column names, call coral_schema_search first.
7. If coral_query returns a schema/column/table error, fix SQL and retry.
8. For broad exploration queries, start with a LIMIT and then refine.
9. If user asks for a field that is not a direct column, inspect table via coral_profile_table.
10. If using derived fields from JSON-like payloads, explicitly disclose that in the answer.
11. End each analytical answer with a one-line confidence note:
    - "Confidence: high (direct columns)"
    - "Confidence: medium (includes derived fields)"
    - "Confidence: low (limited/partial data)"
"""


@tool
async def coral_query(sql: str) -> str:
    """Execute SQL against Coral-connected sources."""
    return await execute_sql(sql)


@tool
async def coral_schema_search(topic: str = "", limit: int = 20) -> str:
    """
    Search available Coral schemas/tables/columns by keyword.
    Use before writing SQL when field names are unclear.
    """
    return await search_catalog(topic=topic, limit=limit)


@tool
async def coral_profile_table(table_ref: str, sample_rows: int = 5) -> str:
    """
    Inspect a table's columns and sample rows. Also discovers top-level JSON keys
    in JSON-like columns so the agent can derive fields safely.
    table_ref format: schema.table
    """
    return await profile_table(table_ref=table_ref, sample_rows=sample_rows)


@tool
def generate_chart(
    data_json: str,
    chart_type: str = "bar",
    title: str = "Chart",
    x_label: str = "",
    y_label: str = "",
) -> str:
    """
    Generate a bar/line/pie/horizontal_bar chart from JSON data.
    Returns a base64 PNG data URI.
    """
    return create_chart(data_json, chart_type, title, x_label, y_label)


_llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    api_key=os.environ["ANTHROPIC_API_KEY"],
)


def _extract_results(messages: list[BaseMessage]) -> dict[str, Any]:
    sql: Optional[str] = None
    chart: Optional[str] = None
    sources: list[str] = []

    for msg in messages:
        if hasattr(msg, "tool_calls"):
            for tool_call in msg.tool_calls:  # type: ignore[union-attr]
                if tool_call["name"] == "coral_query":
                    sql = tool_call["args"].get("sql", sql)
                    if sql:
                        found = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.", sql)
                        for src in found:
                            if src.lower() != "coral":
                                sources.append(src.lower())

        if isinstance(msg, ToolMessage) and msg.name == "generate_chart":
            if isinstance(msg.content, str) and msg.content.startswith("data:image/png"):
                chart = msg.content

    return {"sql": sql, "chart": chart, "sources_used": list(dict.fromkeys(sources))}


async def run_agent(message: str, session_id: str = "web") -> dict[str, Any]:
    catalog, catalog_error = await get_catalog_snapshot()
    system_prompt = _build_system_prompt(catalog, catalog_error)
    agent = create_react_agent(
        _llm,
        [coral_schema_search, coral_profile_table, coral_query, generate_chart],
        prompt=system_prompt,
    )

    result = await agent.ainvoke({"messages": [("user", message)]})

    msgs: list[BaseMessage] = result["messages"]
    ai_msgs = [m for m in msgs if isinstance(m, AIMessage)]
    response_text = ai_msgs[-1].content if ai_msgs else "I couldn't generate a response."

    if isinstance(response_text, list):
        text_blocks = [
            block["text"]
            for block in response_text
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        response_text = "\n".join(text_blocks)

    extras = _extract_results(msgs)

    await save_query_history(
        session_id,
        message,
        extras["sql"],
        str(response_text)[:500],
        extras["sources_used"],
    )

    return {
        "response": response_text,
        "chart": extras["chart"],
        "sql": extras["sql"],
        "sources_used": extras["sources_used"],
    }
