import type { Metadata } from "next";
import { ReactNode } from "react";

import { auth } from "@/auth";
import { AppNav } from "@/components/app-nav";
import { SignOutButton } from "@/components/signout-button";

import "./globals.css";

export const metadata: Metadata = {
  title: "Austin Event Tracker Admin",
  description: "Admin UI for preferences, prompts, tracked items, and calendar sync",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  const session = await auth();

  return (
    <html lang="en">
      <body>
        {session?.user ? (
          <div className="app-shell">
            <header className="app-header">
              <div>
                <p className="eyebrow">Austin Event Tracker</p>
                <h1 className="app-title">Admin Console</h1>
              </div>
              <div className="header-actions">
                <span className="signed-in-email">{session.user.email}</span>
                <SignOutButton />
              </div>
            </header>
            <AppNav />
            <main className="app-main">{children}</main>
          </div>
        ) : (
          <main className="signin-shell">{children}</main>
        )}
      </body>
    </html>
  );
}
