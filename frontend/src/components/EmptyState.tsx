interface EmptyStateProps {
  message?: string;
}

export function EmptyState({ message = "No data available." }: EmptyStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center py-16 gap-2 rounded"
      style={{
        border: "1px dashed var(--border)",
        background: "transparent",
      }}
    >
      <span
        className="font-mono text-[10px] tracking-widest uppercase"
        style={{ color: "var(--text-muted)" }}
      >
        — {message} —
      </span>
    </div>
  );
}
