import { NextRequest, NextResponse } from "next/server";

const TH3LAB_ASK_URL = process.env.TH3LAB_ASK_URL ?? "http://localhost:8090/mcp/world/ask";
const TH3LAB_WORLD_ID = process.env.TH3LAB_WORLD_ID ?? "amniotic";
const TH3LAB_PROJECT_ID = process.env.TH3LAB_PROJECT_ID ?? "_admin";

function backendBaseFromAskUrl(askUrl: string): string {
  // .../mcp/world/ask -> base root
  return askUrl.replace(/\/mcp\/world\/ask\/?$/, "");
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "Missing file" }, { status: 400 });
    }

    const ext = (file.name.split(".").pop() || "").toLowerCase();
    const allowedDocs = new Set(["pdf", "txt", "md", "epub", "docx"]);
    const kind = allowedDocs.has(ext) ? "document" : "media";

    if (kind === "media") {
      // Media is accepted as session reference for now.
      return NextResponse.json({
        ok: true,
        kind,
        filename: file.name,
        note: "Media attached as session context (ingestion supports text docs only)."
      });
    }

    const backendBase = backendBaseFromAskUrl(TH3LAB_ASK_URL);
    const ingestUrl = `${backendBase}/api/library/worlds/${TH3LAB_WORLD_ID}/ingest`;

    const upstream = new FormData();
    upstream.set("file", file);
    upstream.set("project_id", TH3LAB_PROJECT_ID);

    const response = await fetch(ingestUrl, {
      method: "POST",
      body: upstream,
      cache: "no-store"
    });

    const text = await response.text();
    let data: unknown = text;
    try {
      data = JSON.parse(text);
    } catch {
      // keep raw text
    }

    if (!response.ok) {
      return NextResponse.json(
        { error: "Ingest failed", status: response.status, detail: data, ingestUrl },
        { status: 502 }
      );
    }

    return NextResponse.json({ ok: true, kind, filename: file.name, ingest: data });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown upload error" },
      { status: 500 }
    );
  }
}
