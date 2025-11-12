import { NextResponse } from "next/server";
import { getGoaliePulse } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET() {
  const payload = getGoaliePulse();
  return NextResponse.json(payload, {
    headers: {
      "Cache-Control": "public, max-age=300, stale-while-revalidate=900",
    },
  });
}
