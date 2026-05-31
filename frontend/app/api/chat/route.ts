import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await fetch(`${BACKEND}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  }

  const text = await res.text();
  return NextResponse.json(
    {
      response: text || "Backend returned a non-JSON response.",
      chart: null,
      sql: null,
      sources_used: [],
    },
    { status: res.status },
  );
}
