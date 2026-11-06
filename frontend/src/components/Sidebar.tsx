import { MessageSquare, Moon, MoreHorizontal, PanelLeftClose, Plus, Search, Sun, Trash2 } from "lucide-react";
import type { Conversation } from "../types";
import { Logo } from "./Logo";

function dateGroup(timestamp: number): string {
  const today = new Date();
  const date = new Date(timestamp);
  if (date.toDateString() === today.toDateString()) return "Today";
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  if (today.getTime() - timestamp < 7 * 24 * 60 * 60 * 1000) return "Previous 7 days";
  return "Earlier";
}

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  open: boolean;
  onClose: () => void;
  onNew: () => void;
  onSelect: (id: string) => void;
  onRemove: (id: string) => void;
  onSearch: () => void;
  onTheme: () => void;
  theme: "light" | "dark";
}

export function Sidebar(props: SidebarProps) {
  const groups = new Map<string, Conversation[]>();
  for (const item of [...props.conversations].sort((a, b) => b.updatedAt - a.updatedAt)) {
    const key = dateGroup(item.updatedAt);
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }

  return <>
    {props.open && <button className="sidebar-scrim" aria-label="Close sidebar" onClick={props.onClose} />}
    <aside className={`sidebar ${props.open ? "sidebar-open" : ""}`} aria-label="Conversations">
      <div className="sidebar-top">
        <button className="icon-button sidebar-toggle" aria-label="Collapse sidebar" title="Collapse sidebar" onClick={props.onClose}><PanelLeftClose size={19} /></button>
        <button className="icon-button" aria-label="New chat" title="New chat" onClick={props.onNew}><Plus size={20} /></button>
      </div>
      <div className="sidebar-actions">
        <button className="sidebar-action" onClick={props.onNew}><Logo small /><span>New chat</span></button>
        <button className="sidebar-action" onClick={props.onSearch}><Search size={19} /><span>Search conversations</span><kbd>⌘ K</kbd></button>
      </div>
      <nav className="conversation-list" aria-label="Local conversations">
        {[...groups].map(([group, conversations]) => <div className="conversation-group" key={group}>
          <h2>{group}</h2>
          {conversations.map((item) => <div className={`conversation-row ${props.activeId === item.id ? "selected" : ""}`} key={item.id}>
            <button className="conversation-select" onClick={() => props.onSelect(item.id)} title={item.title}>
              <MessageSquare size={16} className="conversation-icon" /><span>{item.title}</span>
            </button>
            <button className="conversation-delete" title="Delete conversation" aria-label={`Delete conversation ${item.title}`} onClick={() => props.onRemove(item.id)}><Trash2 size={15} /></button>
          </div>)}
        </div>)}
      </nav>
      <div className="sidebar-footer">
        <button className="sidebar-footer-button" onClick={props.onTheme}>
          {props.theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
          <span>{props.theme === "light" ? "Dark mode" : "Light mode"}</span>
        </button>
        <div className="profile-row"><span className="profile-avatar">A</span><span><strong>Agentic Support</strong><small>Local demo workspace</small></span><MoreHorizontal size={18} /></div>
      </div>
    </aside>
  </>;
}
