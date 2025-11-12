import { NextResponse } from "next/server";
import { getPredictionsPayload } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET() {
  const payload = getPredictionsPayload();
  return NextResponse.json(payload, {
    headers: {
      "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
    },
  });
}
