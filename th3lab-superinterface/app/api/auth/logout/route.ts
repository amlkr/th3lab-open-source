import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: "th3lab_session",
    value: "",
    path: "/",
    maxAge: 0
  });
  return response;
}
