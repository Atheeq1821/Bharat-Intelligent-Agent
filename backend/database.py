"""Supabase client — query history persistence."""

import os
from typing import Optional

from supabase import Client, create_client

_client: Optional[Client] = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        _client = create_client(url, key)
    return _client


async def save_query_history(
    session_id: str,
    user_message: str,
    sql: Optional[str],
    result_summary: Optional[str],
    sources_used: list[str],
) -> None:
    try:
        get_supabase().table("query_history").insert(
            {
                "session_id": session_id,
                "user_message": user_message,
                "sql_generated": sql,
                "result_summary": result_summary,
                "sources_used": sources_used,
            }
        ).execute()
    except Exception as e:
        print(f"[db] failed to save history: {e}")


async def get_query_history(limit: int = 50) -> list:
    try:
        result = (
            get_supabase()
            .table("query_history")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        print(f"[db] failed to fetch history: {e}")
        return []
