import { useState, type FormEvent } from "react";
import { authenticate } from "../lib/api";
import type { AuthSession } from "../types";
import { Logo } from "./Logo";

export function SignIn({ onSignIn }: { onSignIn: (session: AuthSession) => void }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !token.trim()) return;
    setBusy(true);
    setError("");
    try {
      const userId = await authenticate(token.trim());
      onSignIn({ userId, token: token.trim() });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not connect. Please try again.");
      setBusy(false);
    }
  }

  return <main className="sign-in">
    <form className="sign-in-card" onSubmit={(event) => void submit(event)}>
      <Logo />
      <h1>Agentic Support</h1>
      <p>Enter the access token provided by the demo owner.</p>
      <label htmlFor="access-token">Access token</label>
      <input id="access-token" type="password" value={token} onChange={(event) => setToken(event.target.value)} autoComplete="off" required disabled={busy} />
      {error && <p role="alert">{error}</p>}
      <button className="confirm-button" type="submit" disabled={busy || !token.trim()}>{busy ? "Connecting…" : "Open support"}</button>
      <p>Your access token is kept in memory for this visit.</p>
    </form>
  </main>;
}
