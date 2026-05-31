import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
  const refresh = req.nextUrl.searchParams.get("refresh");
  const url = new URL(`${BACKEND}/source-health`);
  if (refresh === "1" || refresh === "true") {
    url.searchParams.set("refresh", "true");
  }

  const res = await fetch(url.toString(), { cache: "no-store" });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
