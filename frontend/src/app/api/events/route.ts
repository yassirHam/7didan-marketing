import { FUNNEL_EVENTS, type FunnelEvent } from "@/lib/contract";
import { backendUrl, forward, json, readJson } from "@/lib/server/upstream";
import { isId } from "@/lib/validation";

export async function POST(req: Request) {
  const body = await readJson(req);
  if (!body || !isId(body.conversation_id) || !FUNNEL_EVENTS.includes(body.event as FunnelEvent)) {
    return json({ error: "Unknown event." }, 400);
  }
  // Demo mode has no database: the event is accepted and dropped. The FastAPI backend stores it
  // in reporting.conversation_events for the dashboard.
  if (backendUrl()) await forward("/api/events", { conversation_id: body.conversation_id, event: body.event }, 5_000);
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}
