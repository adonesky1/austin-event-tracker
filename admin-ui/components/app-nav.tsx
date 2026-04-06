"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/preferences", label: "Preferences" },
  { href: "/prompts", label: "Prompts" },
  { href: "/tracked-items", label: "Tracked Items" },
  { href: "/sources", label: "Sources" },
  { href: "/calendar", label: "Calendar" },
  { href: "/jobs", label: "Jobs" },
  { href: "/digests", label: "Digests" },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="nav-grid">
      {LINKS.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={active ? "nav-link nav-link-active" : "nav-link"}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
