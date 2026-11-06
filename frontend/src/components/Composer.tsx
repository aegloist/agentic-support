import type { FormEvent, KeyboardEvent, RefObject } from "react";
import { ArrowUp, Square } from "lucide-react";

interface ComposerProps {
  busy: boolean;
  onSend: (message: string) => void;
  onStop: () => void;
  draft: string;
  onDraft: (value: string) => void;
  inputRef: RefObject<HTMLTextAreaElement | null>;
}

export function Composer({ busy, onSend, onStop, draft, onDraft, inputRef }: ComposerProps) {
  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!busy && draft.trim()) { onSend(draft); onDraft(""); }
  }
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }
  return <div className="composer-wrap">
    <form className="composer" onSubmit={submit}>
      <textarea ref={inputRef} value={draft} onChange={(event) => { onDraft(event.target.value); event.target.style.height = "auto"; event.target.style.height = `${Math.min(event.target.scrollHeight, 180)}px`; }} onKeyDown={keyDown} placeholder="Ask a question" rows={1} maxLength={4000} aria-label="Message" />
      <div className="composer-bottom"><span className="composer-hint">Shift + Enter new line</span>
        {busy ? <button type="button" className="send-button stop-button" aria-label="Stop response" title="Stop response" onClick={onStop}><Square size={15} fill="currentColor" /></button>
          : <button type="button" className="send-button" aria-label="Send message" title="Send message" disabled={!draft.trim()} onClick={() => submit()}><ArrowUp size={19} strokeWidth={2.5} /></button>}
      </div>
    </form>
    <p className="composer-disclaimer">Agentic Support can make mistakes. Verify important information.</p>
  </div>;
}
