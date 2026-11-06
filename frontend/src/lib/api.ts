import type { Capabilities, ChatRequest, StreamEvent } from "../types";
import { SseDecoder } from "./sse";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function authenticate(token: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(response.status === 401
    ? "That access token was not accepted. Check it and try again."
    : "Sign-in is temporarily unavailable. Please try again.");
  const body: unknown = await response.json();
  if (typeof body !== "object" || body === null || !("user_id" in body) || typeof body.user_id !== "string") {
    throw new Error("The service returned an invalid sign-in response.");
  }
  return body.user_id;
}

export async function checkHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/health`, { signal });
    return response.ok;
  } catch {
    return false;
  }
}

export async function getCapabilities(signal?: AbortSignal): Promise<Capabilities | null> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/capabilities`, { signal });
    return response.ok ? await response.json() as Capabilities : null;
  } catch {
    return null;
  }
}

export async function streamChat(
  payload: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
  token: string,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok) {
    let message = response.status >= 500
      ? "The service is temporarily unavailable. Please try again."
      : `Request failed (HTTP ${response.status})`;
    try {
      const error: unknown = await response.json();
      if (typeof error === "object" && error !== null && "message" in error) {
        const detail = String(error.message);
        message = detail === "internal error" ? "The service is temporarily unavailable. Please try again." : detail;
      }
  } catch { /* Use the HTTP status when no JSON error body is available. */ }
    throw new Error(message);
  }
  if (!response.body) throw new Error("This browser does not support streaming responses.");

  const reader = response.body.getReader();
  const decoder = new SseDecoder();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const event of decoder.feed(value)) onEvent(event);
    }
    for (const event of decoder.finish()) onEvent(event);
  } finally {
    reader.releaseLock();
  }
}
