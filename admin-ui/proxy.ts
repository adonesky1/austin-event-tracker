import { NextResponse } from "next/server";

import { auth } from "@/auth";

export default auth((request) => {
  const pathname = request.nextUrl.pathname;
  const isSignedIn = Boolean(request.auth);
  const isSignInPage = pathname === "/signin";
  const isAuthRoute = pathname.startsWith("/api/auth");

  if (isAuthRoute) {
    return NextResponse.next();
  }

  if (!isSignedIn && !isSignInPage) {
    return NextResponse.redirect(new URL("/signin", request.nextUrl));
  }

  if (isSignedIn && isSignInPage) {
    return NextResponse.redirect(new URL("/", request.nextUrl));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
