import { auth } from "@/auth";
import { requireEnv } from "@/lib/env";

function buildBackendUrl(pathname: string): string {
  const base = requireEnv("BACKEND_BASE_URL").replace(/\/$/, "");
  return `${base}${pathname}`;
}

export async function proxyToBackend(
  request: Request,
  pathname: string,
): Promise<Response> {
  const session = await auth();
  if (!session?.user?.email) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const headers = new Headers(request.headers);
  headers.set("x-api-key", requireEnv("BACKEND_ADMIN_API_KEY"));
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");

  const method = request.method.toUpperCase();
  const canHaveBody = !["GET", "HEAD"].includes(method);
  const body = canHaveBody ? await request.text() : undefined;

  if (canHaveBody && body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  const upstream = await fetch(buildBackendUrl(pathname), {
    method,
    headers,
    body,
    cache: "no-store",
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
