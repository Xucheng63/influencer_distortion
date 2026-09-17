import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await params;
  const qs = request.nextUrl.searchParams.toString();

  try {
    const data = await backendFetch(
      `/api/v1/distortion/analyze/${jobId}?${qs}`,
      { method: "GET" },
    );
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        error.data ?? { detail: error.statusText },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Status check failed" }, { status: 500 });
  }
}
