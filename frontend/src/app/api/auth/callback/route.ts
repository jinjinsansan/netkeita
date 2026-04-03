import { NextRequest, NextResponse } from "next/server";

const API_BASE = "https://bot.dlogicai.in/nk";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const error = url.searchParams.get("error");

  if (error || !code) {
    return NextResponse.redirect(new URL("/login?error=cancelled", request.url));
  }

  try {
    const resp = await fetch(`${API_BASE}/api/auth/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, state: state || "" }),
    });
    const data = await resp.json();

    if (data.success && data.token) {
      const redirectUrl = new URL("/auth/success", request.url);
      redirectUrl.searchParams.set("token", data.token);
      if (data.user?.display_name) {
        redirectUrl.searchParams.set("name", data.user.display_name);
      }
      return NextResponse.redirect(redirectUrl);
    }

    return NextResponse.redirect(new URL("/login?error=failed", request.url));
  } catch {
    return NextResponse.redirect(new URL("/login?error=network", request.url));
  }
}
