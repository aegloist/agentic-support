import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  failed: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Frontend rendering failed", error, info.componentStack);
  }

  render(): ReactNode {
    if (!this.state.failed) return this.props.children;

    return (
      <main className="fatal-error" role="alert">
        <h1>This page could not load</h1>
        <p>Refresh to try again. Your saved conversations will be restored.</p>
        <button onClick={() => window.location.reload()}>Refresh page</button>
      </main>
    );
  }
}
