import { afterEach, describe, expect, it, vi } from "vitest";
import { authenticate, streamChat } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("support credentials", () => {
  it("verifies tokens with the server and attaches them to chat headers", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ user_id: "owner" })))
      .mockResolvedValueOnce(new Response('data: {"event":"done","trace_id":"test"}\n\n'));
    vi.stubGlobal("fetch", fetchMock);
    expect(await authenticate("private-token")).toBe("owner");
    await streamChat({ message: "hello" }, () => {}, new AbortController().signal, "private-token");
    for (const [, init] of fetchMock.mock.calls) {
      expect(init.headers.Authorization).toBe("Bearer private-token");
      expect(init.body ?? "").not.toContain("private-token");
    }
  });

  it("rejects invalid tokens before opening the workspace", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 401 })));
    await expect(authenticate("invalid-token")).rejects.toThrow("not accepted");
  });
});
