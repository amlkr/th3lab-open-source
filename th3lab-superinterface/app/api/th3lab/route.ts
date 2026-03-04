import { NextRequest, NextResponse } from "next/server";

interface IncomingMessage {
  role: "user" | "assistant" | string;
  content: string;
}

interface BridgeBody {
  messages?: IncomingMessage[];
  message?: string;
  input?: string;
}

const MCP_URL = process.env.TH3LAB_MCP_URL ?? "http://localhost:3000/mcp";
const MCP_TOOL = process.env.TH3LAB_MCP_TOOL ?? "chat_con_agente_principal";
const TH3LAB_ASK_URL = process.env.TH3LAB_ASK_URL ?? "http://localhost:8090/mcp/world/ask";
const TH3LAB_WORLD_ID = process.env.TH3LAB_WORLD_ID ?? "amniotic";
const TH3LAB_PROJECT_ID = process.env.TH3LAB_PROJECT_ID ?? "_admin";

function candidateMcpUrls(): string[] {
  const fromEnv = process.env.TH3LAB_MCP_URL;
  if (fromEnv && fromEnv.trim()) {
    return fromEnv
      .split(",")
      .map((u) => u.trim())
      .filter(Boolean);
  }

  return [
    "http://localhost:3000/mcp",
    "http://localhost:3000",
    "http://localhost:8090/mcp",
    "http://localhost:8090"
  ];
}

function extractUserText(body: BridgeBody): string {
  if (body.message?.trim()) return body.message.trim();
  if (body.input?.trim()) return body.input.trim();

  const messages = Array.isArray(body.messages) ? body.messages : [];
  const latestUserMessage = [...messages]
    .reverse()
    .find((msg) => msg.role === "user" && typeof msg.content === "string" && msg.content.trim());

  return latestUserMessage?.content?.trim() ?? "";
}

function extractToolText(result: unknown): string {
  if (!result || typeof result !== "object") return "Sin respuesta";

  const asAny = result as Record<string, unknown>;

  const direct = ["output", "result", "response", "text", "message"]
    .map((key) => asAny[key])
    .find((value) => typeof value === "string" && value.trim());

  if (typeof direct === "string") return direct;

  const content = asAny.content;
  if (Array.isArray(content)) {
    const textPart = content.find(
      (item) =>
        item &&
        typeof item === "object" &&
        "type" in item &&
        (item as { type?: string }).type === "text" &&
        "text" in item &&
        typeof (item as { text?: string }).text === "string"
    ) as { text?: string } | undefined;

    if (textPart?.text?.trim()) return textPart.text;
  }

  return JSON.stringify(result, null, 2);
}

async function tryJsonRpcCall(message: string, baseUrl: string): Promise<string> {
  const payload = {
    jsonrpc: "2.0",
    id: Date.now(),
    method: "tools/call",
    params: {
      name: MCP_TOOL,
      arguments: {
        message,
        mensaje: message,
        input: message,
        prompt: message
      }
    }
  };

  const response = await fetch(baseUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`MCP JSON-RPC error (${response.status}) on ${baseUrl}`);
  }

  const data = (await response.json()) as Record<string, unknown>;
  if (data.error) {
    throw new Error(typeof data.error === "string" ? data.error : JSON.stringify(data.error));
  }

  return extractToolText(data.result);
}

async function tryRestToolCall(message: string, baseUrl: string): Promise<string> {
  const endpoint = `${baseUrl.replace(/\/$/, "")}/tools/${MCP_TOOL}`;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json"
    },
    body: JSON.stringify({ message, input: message, prompt: message }),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`MCP REST tool error (${response.status}) on ${endpoint}`);
  }

  const data = (await response.json()) as Record<string, unknown>;
  return extractToolText(data);
}

async function tryTh3labAsk(message: string): Promise<string> {
  const response = await fetch(TH3LAB_ASK_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json"
    },
    body: JSON.stringify({
      world_id: TH3LAB_WORLD_ID,
      message,
      project_id: TH3LAB_PROJECT_ID
    }),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`TH3LAB ask error (${response.status}) on ${TH3LAB_ASK_URL}`);
  }

  const data = (await response.json()) as Record<string, unknown>;
  return extractToolText(data);
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as BridgeBody;
    const userText = extractUserText(body);

    if (!userText) {
      return NextResponse.json({ error: "Missing user message" }, { status: 400 });
    }

    const attempts: string[] = [];
    for (const baseUrl of candidateMcpUrls()) {
      try {
        const reply = await tryJsonRpcCall(userText, baseUrl);
        return NextResponse.json({ reply, tool: MCP_TOOL, transport: "jsonrpc", baseUrl });
      } catch (jsonErr) {
        attempts.push(
          `JSON-RPC ${baseUrl}: ${jsonErr instanceof Error ? jsonErr.message : String(jsonErr)}`
        );
      }

      try {
        const reply = await tryRestToolCall(userText, baseUrl);
        return NextResponse.json({ reply, tool: MCP_TOOL, transport: "rest", baseUrl });
      } catch (restErr) {
        attempts.push(
          `REST ${baseUrl}: ${restErr instanceof Error ? restErr.message : String(restErr)}`
        );
      }
    }

    try {
      const reply = await tryTh3labAsk(userText);
      return NextResponse.json({
        reply,
        tool: MCP_TOOL,
        transport: "th3lab-ask",
        baseUrl: TH3LAB_ASK_URL
      });
    } catch (askErr) {
      attempts.push(
        `TH3LAB_ASK ${TH3LAB_ASK_URL}: ${
          askErr instanceof Error ? askErr.message : String(askErr)
        }`
      );
    }

    return NextResponse.json(
      {
        error: "Could not reach TH3LAB MCP server",
        tool: MCP_TOOL,
        tried: attempts
      },
      { status: 502 }
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown bridge error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
