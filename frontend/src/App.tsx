import { useEffect, useRef, useState } from "react";
import { ArrowDown, CircleHelp, Menu, PanelLeftOpen } from "lucide-react";
import { checkHealth } from "./lib/api";
import { useChat } from "./hooks/useChat";
import { Composer } from "./components/Composer";
import { Logo } from "./components/Logo";
import { MessageView } from "./components/MessageView";
import { SearchDialog } from "./components/SearchDialog";
import { Sidebar } from "./components/Sidebar";
import { SignIn } from "./components/SignIn";
import type { ActionProposal, AuthSession } from "./types";

const SUGGESTIONS = [
  { icon: "↗", title: "Returns policy", prompt: "Can I return a custom item that arrived damaged?" },
  { icon: "◎", title: "Shipping status", prompt: "Track order ORD10001" },
  { icon: "◇", title: "Payments and invoices", prompt: "How do I request a business invoice?" },
  { icon: "✳", title: "Returns and support", prompt: "What information do I need to request a return?" },
];

function App() {
  const [session, setSession] = useState<AuthSession | null>(null);
  return session
    ? <SupportWorkspace key={session.userId} session={session} onSignOut={() => setSession(null)} />
    : <SignIn onSignIn={setSession} />;
}

function SupportWorkspace({ session, onSignOut }: { session: AuthSession; onSignOut: () => void }) {
  const chat = useChat(session.userId, session.token);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">(() => localStorage.getItem("agentic-support-theme") === "dark" ? "dark" : "light");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("agentic-support-theme", theme);
  }, [theme]);
  useEffect(() => {
    const controller = new AbortController();
    void checkHealth(controller.signal).then(setHealthy);
    return () => controller.abort();
  }, []);
  useEffect(() => {
    function onKey(event: globalThis.KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setSearchOpen(true); }
      if (event.key === "Escape") { setSearchOpen(false); setSidebarOpen(false); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function newChat() {
    chat.select(null);
    setDraft("");
    setSidebarOpen(false);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }

  function selectChat(id: string) { chat.select(id); setSidebarOpen(false); setSearchOpen(false); }
  function suggest(prompt: string) { setDraft(prompt); inputRef.current?.focus(); }
  function confirm(action: ActionProposal, messageId: string) {
    if (!chat.active) return;
    const conversationId = chat.active.id;
    void chat.send("Confirm action", action.action_id).then((succeeded) => {
      if (succeeded) chat.dismissAction(conversationId, messageId);
    });
  }

  return <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
    <Sidebar conversations={chat.conversations} activeId={chat.active?.id ?? null} open={sidebarOpen} onClose={() => { setSidebarOpen(false); setSidebarCollapsed(true); }} onNew={newChat} onSelect={selectChat} onRemove={chat.remove} onSearch={() => setSearchOpen(true)} onTheme={() => setTheme(theme === "light" ? "dark" : "light")} theme={theme} />
    <main className="main-panel">
      <header className="topbar">
        <button className="icon-button open-sidebar" aria-label="Open sidebar" title="Open sidebar" onClick={() => { setSidebarCollapsed(false); setSidebarOpen(true); }}>{sidebarCollapsed ? <PanelLeftOpen size={20} /> : <Menu size={20} />}</button>
        <span className="model-title">Agentic Support</span>
        <button className="cancel-button" onClick={onSignOut}>Sign out</button>
        <div className="topbar-right"><span className={`connection-pill ${healthy === false ? "offline" : ""}`}><span />{healthy === null ? "Connecting" : healthy ? "Connected" : "Service unavailable"}</span><button className="icon-button help-button" title="Help" aria-label="Help" onClick={() => window.open("/docs", "_blank", "noopener,noreferrer")}><CircleHelp size={19} /></button></div>
      </header>
      {healthy === false && <div className="service-banner" role="status"><strong>Cannot connect to the service</strong><span>Check that the API is running, then try again.</span></div>}
      {chat.active ? <div className="chat-content"><MessageView conversation={chat.active} busy={chat.busy} onConfirm={confirm} onCancel={(messageId) => chat.dismissAction(chat.active!.id, messageId)} /></div>
        : <div className="welcome"><div className="welcome-inner"><Logo /><h1>How can I help?</h1><p>Get policy answers, order details, and support actions in one conversation.</p><div className="suggestions">{SUGGESTIONS.map((item) => <button key={item.title} onClick={() => suggest(item.prompt)}><span className="suggestion-icon">{item.icon}</span><span><strong>{item.title}</strong><small>{item.prompt}</small></span><ArrowDown size={15} /></button>)}</div></div></div>}
      <Composer busy={chat.busy} onSend={(message) => void chat.send(message)} onStop={chat.stop} draft={draft} onDraft={setDraft} inputRef={inputRef} />
    </main>
    {searchOpen && <SearchDialog conversations={chat.conversations} onClose={() => setSearchOpen(false)} onSelect={selectChat} />}
  </div>;
}

export default App;
