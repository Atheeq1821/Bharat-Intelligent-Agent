"""
Coral CLI client that executes SQL via:
  coral sql --format json "<SQL>"

Set CORAL_EXECUTABLE in backend/.env if coral is not on PATH.
"""

import json
import os
import re
import subprocess
from collections import defaultdict
from difflib import get_close_matches
from typing import Any

CORAL_EXE = os.getenv("CORAL_EXECUTABLE", "coral")
MAX_ROWS = 50


def _run_sql_json(sql: str, timeout: int = 30) -> tuple[list[dict], str | None]:
    """Run Coral SQL and return (rows, error)."""
    try:
        result = subprocess.run(
            [CORAL_EXE, "sql", "--format", "json", sql],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            err = (result.stderr or result.stdout or "unknown error").strip()
            return [], f"Coral error: {err[:500]}"

        raw = result.stdout.strip()
        if not raw:
            return [], None

        data = json.loads(raw)
        rows = data if isinstance(data, list) else [data]
        return rows, None

    except FileNotFoundError:
        return [], (
            "coral executable not found. "
            "Set CORAL_EXECUTABLE=/full/path/to/coral in backend/.env"
        )
    except subprocess.TimeoutExpired:
        return [], "Coral query timed out after 30 seconds."
    except json.JSONDecodeError:
        return [], "Coral returned non-JSON output."
    except Exception as exc:
        return [], f"Unexpected error: {exc}"


def _sql_escape(value: str) -> str:
    return value.replace("'", "''")


def _extract_table_refs(sql: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"\b(?:from|join|update|into)\s+([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)",
        re.IGNORECASE,
    )
    refs: list[tuple[str, str]] = []
    for schema, table in pattern.findall(sql):
        refs.append((schema.lower(), table.lower()))
    # De-duplicate while preserving order.
    seen: set[tuple[str, str]] = set()
    ordered: list[tuple[str, str]] = []
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        ordered.append(ref)
    return ordered


def _fetch_columns_for_refs(refs: list[tuple[str, str]]) -> list[dict]:
    if not refs:
        return []
    where_parts = [
        f"(LOWER(schema_name) = '{_sql_escape(schema)}' AND LOWER(table_name) = '{_sql_escape(table)}')"
        for schema, table in refs
    ]
    sql = (
        "SELECT schema_name, table_name, column_name "
        "FROM coral.columns "
        f"WHERE {' OR '.join(where_parts)} "
        "ORDER BY schema_name, table_name, column_name"
    )
    rows, err = _run_sql_json(sql)
    return [] if err else rows


def _find_missing_column(err_text: str) -> str | None:
    patterns = [
        r"No column named `([^`]+)`",
        r"No column `([^`]+)` is in scope",
        r"column \"([^\"]+)\" does not exist",
    ]
    for pat in patterns:
        m = re.search(pat, err_text, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _find_missing_table(err_text: str) -> str | None:
    patterns = [
        r"No table named `([^`]+)`",
        r"table \"([^\"]+)\" does not exist",
    ]
    for pat in patterns:
        m = re.search(pat, err_text, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _build_error_hint(sql: str, err: str) -> str:
    refs = _extract_table_refs(sql)
    details: list[str] = []

    if refs:
        details.append(
            "Referenced tables: " + ", ".join(f"{schema}.{table}" for schema, table in refs)
        )
        ref_columns = _fetch_columns_for_refs(refs)
        if ref_columns:
            grouped: dict[str, list[str]] = defaultdict(list)
            for row in ref_columns:
                key = f"{row.get('schema_name')}.{row.get('table_name')}"
                grouped[key].append(str(row.get("column_name")))
            details.append("Available columns:")
            for key, cols in grouped.items():
                preview = ", ".join(cols[:25])
                suffix = " ..." if len(cols) > 25 else ""
                details.append(f"- {key}: {preview}{suffix}")

    missing_col = _find_missing_column(err)
    if missing_col:
        all_cols = []
        ref_columns = _fetch_columns_for_refs(refs)
        for row in ref_columns:
            name = str(row.get("column_name", ""))
            if name:
                all_cols.append(name)
        suggestions = get_close_matches(missing_col, all_cols, n=6, cutoff=0.5)
        if suggestions:
            details.append(
                f"Closest column names for '{missing_col}': " + ", ".join(suggestions)
            )

    missing_table = _find_missing_table(err)
    if missing_table:
        like = _sql_escape(missing_table.lower())
        rows, search_err = _run_sql_json(
            "SELECT schema_name, table_name FROM coral.tables "
            f"WHERE LOWER(table_name) LIKE '%{like}%' OR LOWER(schema_name) LIKE '%{like}%' "
            "ORDER BY schema_name, table_name LIMIT 20"
        )
        if not search_err and rows:
            found = [f"{r.get('schema_name')}.{r.get('table_name')}" for r in rows]
            details.append("Similar available tables: " + ", ".join(found))

    if not details:
        return err
    return err + "\n\nSchema hints:\n" + "\n".join(details)


async def get_catalog_snapshot() -> tuple[dict[str, list[str]], str | None]:
    """
    Return installed source catalog as {schema_name: [table_name, ...]}.
    Excludes Coral's internal schema.
    """
    rows, err = _run_sql_json(
        "SELECT schema_name, table_name FROM coral.tables ORDER BY schema_name, table_name"
    )
    if err:
        return {}, err

    catalog: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        schema = str(row.get("schema_name", "")).strip()
        table = str(row.get("table_name", "")).strip()
        if not schema or not table or schema == "coral":
            continue
        catalog[schema].append(table)

    return dict(catalog), None


async def search_catalog(topic: str, limit: int = 20) -> str:
    """
    Search schemas/tables/columns by keyword for NL->SQL grounding.
    Returns compact JSON text.
    """
    query = topic.strip().lower()
    if not query:
        query = ""
    like = _sql_escape(query)

    table_sql = (
        "SELECT schema_name, table_name "
        "FROM coral.tables "
        "WHERE schema_name <> 'coral' "
        + (
            ""
            if not like
            else f"AND (LOWER(schema_name) LIKE '%{like}%' OR LOWER(table_name) LIKE '%{like}%') "
        )
        + f"ORDER BY schema_name, table_name LIMIT {max(1, min(limit, 100))}"
    )
    col_sql = (
        "SELECT schema_name, table_name, column_name "
        "FROM coral.columns "
        + (
            ""
            if not like
            else f"WHERE LOWER(schema_name) LIKE '%{like}%' OR LOWER(table_name) LIKE '%{like}%' OR LOWER(column_name) LIKE '%{like}%' "
        )
        + f"ORDER BY schema_name, table_name, column_name LIMIT {max(1, min(limit * 4, 300))}"
    )

    table_rows, t_err = _run_sql_json(table_sql)
    col_rows, c_err = _run_sql_json(col_sql)
    if t_err:
        return t_err
    if c_err:
        return c_err

    payload = {"topic": topic, "tables": table_rows, "columns": col_rows}
    return json.dumps(payload, indent=2, default=str)


def _try_parse_json(value: Any) -> dict | list | None:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text[0] not in "[{":
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, (dict, list)):
            return parsed
    except Exception:
        return None
    return None


async def profile_table(table_ref: str, sample_rows: int = 5) -> str:
    """
    Profile a table with schema, sample rows, and discovered JSON keys.
    table_ref format: schema.table
    """
    table_ref = table_ref.strip()
    if "." not in table_ref:
        return "Invalid table_ref. Use format: schema.table"

    schema, table = table_ref.split(".", 1)
    schema = schema.strip()
    table = table.strip()
    if not schema or not table:
        return "Invalid table_ref. Use format: schema.table"

    where = (
        f"LOWER(schema_name) = '{_sql_escape(schema.lower())}' "
        f"AND LOWER(table_name) = '{_sql_escape(table.lower())}'"
    )
    cols_sql = (
        "SELECT schema_name, table_name, column_name "
        "FROM coral.columns "
        f"WHERE {where} "
        "ORDER BY column_name"
    )
    cols, cols_err = _run_sql_json(cols_sql)
    if cols_err:
        return cols_err
    if not cols:
        return f"Table not found in catalog: {schema}.{table}"

    safe_limit = max(1, min(sample_rows, 25))
    sample_sql = f'SELECT * FROM "{schema}"."{table}" LIMIT {safe_limit}'
    samples, sample_err = _run_sql_json(sample_sql)
    if sample_err:
        return sample_err

    json_key_map: dict[str, list[str]] = {}
    for row in samples:
        for key, value in row.items():
            parsed = _try_parse_json(value)
            if isinstance(parsed, dict):
                discovered = json_key_map.setdefault(key, [])
                for k in parsed.keys():
                    k_str = str(k)
                    if k_str not in discovered:
                        discovered.append(k_str)

    payload = {
        "table": f"{schema}.{table}",
        "columns": [c.get("column_name") for c in cols],
        "sample_rows": samples,
        "json_object_keys_by_column": json_key_map,
    }
    return json.dumps(payload, indent=2, default=str)


async def execute_sql(sql: str) -> str:
    """Run SQL through Coral CLI and return a JSON string of rows."""
    rows, err = _run_sql_json(sql)
    if err:
        return _build_error_hint(sql, err)
    if not rows:
        return "Query returned no results."

    preview = rows[:MAX_ROWS]
    suffix = (
        f"\n\n({len(rows)} total rows - showing first {MAX_ROWS})"
        if len(rows) > MAX_ROWS
        else ""
    )
    return json.dumps(preview, indent=2, default=str) + suffix
