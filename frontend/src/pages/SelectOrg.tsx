import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const GHOST_ROWS = [
  { name: "████████████",   count: "███", status: "ACTIVE" },
  { name: "██████ ████",    count: "██",  status: "ACTIVE" },
  { name: "███████████████", count: "████", status: "LIMITED" },
];

function GlitchTitle() {
  const letters = "W·S·I·P".split("");
  return (
    <div className="flex items-end justify-center gap-0 select-none" aria-label="WSIP">
      {letters.map((char, i) => (
        <span
          key={i}
          className="font-display font-bold"
          style={{
            fontSize: char === "·" ? "2.5rem" : "5.5rem",
            lineHeight: 1,
            color: char === "·" ? "rgba(0,216,255,0.25)" : "var(--text-primary)",
            letterSpacing: "-0.02em",
            animation: `sweep-in 0.4s ${i * 0.06}s ease both`,
            display: "inline-block",
            textShadow: char !== "·" ? "0 0 40px rgba(0,216,255,0.15)" : "none",
          }}
        >
          {char}
        </span>
      ))}
    </div>
  );
}

export function SelectOrg() {
  const [orgId, setOrgId] = useState("");
  const [focused, setFocused] = useState(false);
  const [cursorVisible, setCursorVisible] = useState(true);
  const navigate = useNavigate();

  // Blinking cursor
  useEffect(() => {
    const id = setInterval(() => setCursorVisible((v) => !v), 530);
    return () => clearInterval(id);
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const id = orgId.trim();
    if (id) {
      localStorage.setItem("wsip_org_id", id);
      navigate(`/orgs/${id}`);
    }
  }

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div
      className="relative flex flex-col items-center justify-center w-full cockpit-grid"
      style={{ background: "var(--bg-void)", minHeight: "100dvh" }}
    >
      {/* Horizontal scan line accent */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "1px",
          background: "linear-gradient(90deg, transparent 0%, var(--accent-cyan) 50%, transparent 100%)",
          opacity: 0.2,
        }}
      />

      <div
        className="flex flex-col items-center gap-10 w-full max-w-md px-6"
        style={{ animation: "fade-in 0.6s ease both" }}
      >
        {/* Wordmark */}
        <div className="flex flex-col items-center gap-3">
          <GlitchTitle />

          <div
            className="flex items-center gap-3"
            style={{ animation: "sweep-in 0.4s 0.4s ease both" }}
          >
            <div style={{ height: "1px", width: "40px", background: "var(--border)" }} />
            <span
              className="font-display text-[10px] tracking-[0.25em] uppercase"
              style={{ color: "var(--text-muted)" }}
            >
              Work Signal Intelligence Platform
            </span>
            <div style={{ height: "1px", width: "40px", background: "var(--border)" }} />
          </div>
        </div>

        {/* Form — HUD-bracketed terminal */}
        <div
          className="hud-card w-full rounded flex flex-col gap-4 p-6"
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            boxShadow: "0 0 60px rgba(0,216,255,0.04), 0 0 0 1px rgba(0,216,255,0.06)",
            animation: "sweep-in 0.4s 0.25s ease both",
          }}
        >
          <div className="flex flex-col gap-1">
            <span
              className="font-display text-[10px] tracking-widest uppercase"
              style={{ color: "var(--text-muted)" }}
            >
              ORG Identifier
            </span>
            <span
              className="font-mono text-[9px]"
              style={{ color: "var(--text-muted)" }}
            >
              Enter a valid UUID to initiate access
            </span>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            {/* Terminal-style input */}
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded"
              style={{
                background: "var(--bg-elevated)",
                border: `1px solid ${focused ? "rgba(0,216,255,0.35)" : "var(--border)"}`,
                boxShadow: focused ? "0 0 0 2px rgba(0,216,255,0.07)" : "none",
                transition: "border-color 0.15s, box-shadow 0.15s",
              }}
            >
              <span
                className="font-mono text-xs select-none"
                style={{ color: "var(--accent-cyan)", opacity: 0.7 }}
              >
                ▸
              </span>
              <input
                type="text"
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                className="flex-1 bg-transparent font-mono text-xs outline-none"
                style={{
                  color: "var(--text-primary)",
                  caretColor: "var(--accent-cyan)",
                } as React.CSSProperties}
                autoFocus
                spellCheck={false}
                autoComplete="off"
              />
              {/* Blinking cursor when empty and focused */}
              {!orgId && focused && (
                <span
                  className="font-mono text-xs"
                  style={{
                    color: "var(--accent-cyan)",
                    opacity: cursorVisible ? 1 : 0,
                    transition: "opacity 0.05s",
                    userSelect: "none",
                  }}
                >
                  █
                </span>
              )}
            </div>

            <button
              type="submit"
              disabled={!orgId.trim()}
              className="font-display font-semibold tracking-widest uppercase text-xs py-2.5 rounded transition-all duration-150 disabled:opacity-30"
              style={{
                background: orgId.trim()
                  ? "rgba(0,216,255,0.12)"
                  : "var(--bg-elevated)",
                border: orgId.trim()
                  ? "1px solid rgba(0,216,255,0.35)"
                  : "1px solid var(--border)",
                color: orgId.trim() ? "var(--accent-cyan)" : "var(--text-muted)",
                boxShadow: orgId.trim() ? "0 0 16px rgba(0,216,255,0.08)" : "none",
              }}
            >
              Initiate Access ▶
            </button>
          </form>
        </div>

        {/* Ghost data — suggests what's inside */}
        <div
          className="w-full flex flex-col gap-0 rounded overflow-hidden"
          style={{
            border: "1px solid var(--border-neutral)",
            opacity: 0.35,
            filter: "blur(0.5px)",
            animation: "sweep-in 0.4s 0.45s ease both",
            userSelect: "none",
            pointerEvents: "none",
          }}
        >
          <div
            className="flex items-center justify-between px-3 py-1.5"
            style={{
              borderBottom: "1px solid var(--border-neutral)",
              background: "var(--bg-surface)",
            }}
          >
            <span className="font-display text-[9px] tracking-widest uppercase" style={{ color: "var(--text-muted)" }}>
              Organizations · ██ total
            </span>
            <span className="font-mono text-[9px]" style={{ color: "var(--text-muted)" }}>
              {today}
            </span>
          </div>
          {GHOST_ROWS.map((row, i) => (
            <div
              key={i}
              className="flex items-center gap-4 px-3 py-2"
              style={{
                background: i % 2 === 0 ? "var(--bg-surface)" : "var(--bg-elevated)",
                borderBottom: i < GHOST_ROWS.length - 1 ? "1px solid var(--border-neutral)" : "none",
              }}
            >
              <span className="font-mono text-[10px] flex-1" style={{ color: "var(--text-secondary)" }}>
                {row.name}
              </span>
              <span className="font-mono text-[10px]" style={{ color: "var(--text-muted)" }}>
                {row.count} emp
              </span>
              <span
                className="font-display text-[9px] tracking-widest"
                style={{ color: row.status === "ACTIVE" ? "var(--accent-green)" : "var(--accent-amber)" }}
              >
                {row.status}
              </span>
            </div>
          ))}
        </div>

        {/* System footer */}
        <div
          className="flex items-center gap-4"
          style={{ animation: "sweep-in 0.4s 0.55s ease both" }}
        >
          <span className="font-mono text-[9px]" style={{ color: "var(--text-muted)" }}>
            WSIP v0.9.0-dev
          </span>
          <span style={{ color: "var(--text-muted)", fontSize: "9px" }}>·</span>
          <span className="font-mono text-[9px]" style={{ color: "var(--text-muted)" }}>
            {today}
          </span>
          <span style={{ color: "var(--text-muted)", fontSize: "9px" }}>·</span>
          <span className="font-display text-[9px] tracking-widest uppercase" style={{ color: "var(--text-muted)" }}>
            Restricted Access
          </span>
        </div>
      </div>

      {/* Bottom scan line accent */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "1px",
          background: "linear-gradient(90deg, transparent 0%, var(--accent-cyan) 50%, transparent 100%)",
          opacity: 0.12,
        }}
      />
    </div>
  );
}
