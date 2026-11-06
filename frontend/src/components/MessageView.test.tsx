import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MessageView } from "./MessageView";
import type { Conversation } from "../types";

describe("answer presentation", () => {
  it("shows the answer and source without internal timing or route metadata", () => {
    const conversation: Conversation = {
      id: "chat-1",
      title: "returnpolicy",
      updatedAt: 0,
      messages: [{
        id: "answer-1",
        role: "assistant",
        state: "complete",
        content: "Under the return policy, defective items can be reviewed for a return.",
        strategy: "multi",
        latencyMs: 4200,
        citations: [{ chunk_id: "chunk-1", document_id: "policy-1", title: "Return policy", section: null }],
      }],
    };
    const html = renderToStaticMarkup(
      <MessageView conversation={conversation} busy={false} onConfirm={() => {}} onCancel={() => {}} />,
    );
    expect(html).toContain("defective items can be reviewed for a return");
    expect(html).toContain("Return policy");
    expect(html).not.toContain("multi-hop retrieval");
    expect(html).not.toContain("4.2 seconds");
  });
});
