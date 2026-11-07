import { demoChat } from "@/lib/server/demo";
import { backendUrl, forward, json, readJson } from "@/lib/server/upstream";
import { isId, LIMITS } from "@/lib/validation";

export async function POST(req: Request) {
  const body = await readJson(req);
  const message = typeof body?.message === "string" ? body.message.trim() : "";
  if (!body || !isId(body.conversation_id) || !message || message.length > LIMITS.message) {
    return json({ error: `Send a message of 1 to ${LIMITS.message} characters.` }, 400);
  }
  const request = { conversation_id: body.conversation_id, message };

  if (!backendUrl()) return json(demoChat(message));

  const r = await forward("/api/chat", request, 40_000);
  if (!r.ok) {
    return json({ error: r.reason === "timeout" ? "The assistant took too long to answer." : "The assistant is not available right now." }, 502);
  }
  return json(r.body, r.status);
}
