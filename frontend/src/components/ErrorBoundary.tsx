import { Component, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback;

    const msg = this.state.error?.message ?? "Unknown error";
    return (
      <div
        className="flex flex-col items-center justify-center h-full gap-4 p-8"
        style={{ background: "var(--bg-default)" }}
      >
        <AlertTriangle size={32} style={{ color: "var(--accent-red)" }} />
        <div className="text-center flex flex-col gap-1.5">
          <p
            className="font-display font-semibold text-sm tracking-wide"
            style={{ color: "var(--text-primary)" }}
          >
            Something went wrong
          </p>
          <p
            className="font-mono text-xs max-w-sm"
            style={{ color: "var(--text-secondary)" }}
          >
            {msg}
          </p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="font-display text-xs tracking-widest uppercase px-4 py-2 rounded"
          style={{
            background: "rgba(255,51,85,0.1)",
            border: "1px solid rgba(255,51,85,0.3)",
            color: "var(--accent-red)",
          }}
        >
          Reload
        </button>
      </div>
    );
  }
}
