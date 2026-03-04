import { NextResponse } from "next/server";

const TH3LAB_ASK_URL = process.env.TH3LAB_ASK_URL ?? "http://localhost:8090/mcp/world/ask";
const TH3LAB_WORLD_ID = process.env.TH3LAB_WORLD_ID ?? "amniotic";

function backendBaseFromAskUrl(askUrl: string): string {
  return askUrl.replace(/\/mcp\/world\/ask\/?$/, "");
}

export async function GET() {
  try {
    const backendBase = backendBaseFromAskUrl(TH3LAB_ASK_URL);
    const url = `${backendBase}/api/library/worlds/${TH3LAB_WORLD_ID}/documents`;

    const response = await fetch(url, { cache: "no-store" });
    const text = await response.text();
    let data: unknown = text;
    try {
      data = JSON.parse(text);
    } catch {
      // keep raw text
    }

    if (!response.ok) {
      return NextResponse.json({ error: "Documents query failed", detail: data }, { status: 502 });
    }

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown documents error" },
      { status: 500 }
    );
  }
}
