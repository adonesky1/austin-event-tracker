import type { NextRequest } from "next/server";

import { proxyToBackend } from "@/lib/backend";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function handle(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  const { path } = await context.params;
  return proxyToBackend(request, `/${path.join("/")}`);
}

export async function GET(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  return handle(request, context);
}

export async function POST(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  return handle(request, context);
}

export async function PUT(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  return handle(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  return handle(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  return handle(request, context);
}
