import { NextRequest, NextResponse } from "next/server";

/**
 * Route guard for SaaS-only pages.
 *
 * Auth tokens live in localStorage (see lib/auth.ts), which middleware
 * (edge runtime) cannot read. lib/auth.ts additionally sets a presence-only
 * `dt_session` cookie alongside the real tokens — never the token itself,
 * just a boolean "a session exists" flag — so this guard has something to
 * check before the page renders.
 *
 * Only the SaaS-specific pages are gated. The original DeepTutor pages
 * (chat, solve, research, guide, co-writer, playground) are intentionally
 * left open — they work anonymously in local/single-user deployments
 * (AUTH_REQUIRED=false) and are not part of the SaaS surface this guards.
 */
const PROTECTED_PREFIXES = ["/dashboard", "/admin", "/billing", "/team"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
  if (!isProtected) {
    return NextResponse.next();
  }

  const hasSession = request.cookies.has("dt_session");
  if (hasSession) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*", "/billing/:path*", "/team/:path*"],
};
