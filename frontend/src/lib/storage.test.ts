import { afterEach, describe, expect, it, vi } from "vitest";
import { loadConversations, saveConversations } from "./storage";

afterEach(() => vi.unstubAllGlobals());

describe("authenticated local history", () => {
  it("keeps users separate and does not load legacy shared history", () => {
    const values = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
    });
    const conversation = { id: "session-1", title: "Private order", updatedAt: 1, messages: [] };
    values.set("agentic-support-web:v1", JSON.stringify([conversation]));
    expect(loadConversations("other")).toEqual([]);
    saveConversations("owner", [conversation]);
    expect(loadConversations("owner")).toEqual([conversation]);
    expect(loadConversations("other")).toEqual([]);
  });
});
