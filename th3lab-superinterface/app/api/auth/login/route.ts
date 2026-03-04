import { NextRequest, NextResponse } from "next/server";

const USER = process.env.BASIC_AUTH_USER;
const PASS = process.env.BASIC_AUTH_PASS;

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as { username?: string; password?: string };
    const username = (body.username || "").trim();
    const password = body.password || "";

    if (!USER || !PASS) {
      return NextResponse.json(
        { error: "Missing BASIC_AUTH_USER/BASIC_AUTH_PASS env vars" },
        { status: 500 }
      );
    }

    if (username !== USER || password !== PASS) {
      return NextResponse.json({ error: "Credenciales invalidas" }, { status: 401 });
    }

    const response = NextResponse.json({ ok: true });
    response.cookies.set({
      name: "th3lab_session",
      value: "ok",
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60 * 24 * 7
    });

    return response;
  } catch {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
}
