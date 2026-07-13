import { getIronSession } from "iron-session";
import { NextResponse, type NextRequest } from "next/server";
import { sessionOptions, type SessionData } from "@/lib/session";

export async function proxy(request: NextRequest) {
  // /login: unauthenticated by definition. /api/trigger-scan: hit by
  // cron-job.org, authenticated by its own TRIGGER_SECRET query param
  // instead of the session cookie.
  if (request.nextUrl.pathname.startsWith("/login") || request.nextUrl.pathname.startsWith("/api/trigger-scan")) {
    return NextResponse.next();
  }

  const response = NextResponse.next();
  const session = await getIronSession<SessionData>(request, response, sessionOptions);

  if (!session.authenticated) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
