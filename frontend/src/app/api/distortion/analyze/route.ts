import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const clientIp =
    request.headers.get("x-forwarded-for") ??
    request.headers.get("x-real-ip") ??
    "unknown";

  try {
    const body = await request.text();
    const data = await backendFetch("/api/v1/distortion/analyze", {
      method: "POST",
      body,
      headers: { "X-Forwarded-For": clientIp },
    });
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        error.data ?? { detail: error.statusText },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Analysis failed" }, { status: 500 });
  }
}
