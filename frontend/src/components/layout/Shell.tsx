import { useState, useEffect } from "react";
import { NavLink, useSearchParams } from "react-router-dom";
import { Radio } from "lucide-react";
import type { ReactNode } from "react";

const NAV_ITEMS = [
  { to: "/orgs",            label: "Overview" },
  { to: "/teams",           label: "Teams" },
  { to: "/employees",       label: "Employees" },
  { to: "/insights",        label: "Insights" },
  { to: "/recommendations", label: "Actions" },
  { to: "/simulations",     label: "Simulation" },
];

interface ShellProps {
  children: ReactNode;
  orgName?: string;
  asOf?: string;
  onDateChange?: (date: string) => void;
}

export function Shell({ children, orgName, asOf, onDateChange }: ShellProps) {
  const [, setSearchParams] = useSearchParams();
  const [clock, setClock] = useState(() =>
    new Date().toLocaleTimeString("en-US", { hour12: false })
  );

  useEffect(() => {
    const id = setInterval(() => {
      setClock(new Date().toLocaleTimeString("en-US", { hour12: false }));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  function handleDateChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    if (onDateChange) {
      onDateChange(val);
    } else {
      setSearchParams((prev) => { prev.set("as_of", val); return prev; });
    }
  }

  const token = import.meta.env.VITE_API_TOKEN ?? "admin-token";
  const role = token.replace("-token", "").toUpperCase();

  return (
    <div
      className="flex flex-col w-full overflow-hidden"
      style={{ background: "var(--bg-default)", height: "100dvh" }}
    >
      {/* ── Top bar ── */}
      <header
        style={{
          background: "var(--bg-surface)",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}
      >
        {/* Primary row: logo + nav + controls */}
        <div className="flex items-center gap-0 px-5" style={{ height: "52px" }}>

          {/* Logo */}
          <div className="flex items-center gap-2.5 pr-6 shrink-0" style={{ borderRight: "1px solid var(--border)" }}>
            <div
              className="flex items-center justify-center font-display font-bold text-[11px] tracking-wider"
              style={{
                width: "30px",
                height: "30px",
                borderRadius: "4px",
                background: "rgba(0,216,255,0.1)",
                border: "1px solid rgba(0,216,255,0.28)",
                color: "var(--accent-cyan)",
                boxShadow: "0 0 14px rgba(0,216,255,0.18)",
              }}
            >
              WS
            </div>
            <div className="flex flex-col leading-none gap-0.5">
              <span
                className="font-display font-semibold tracking-widest text-[11px]"
                style={{ color: "var(--accent-cyan)" }}
              >
                W·S·I·P
              </span>
              <span
                className="font-mono text-[8px] tracking-widest uppercase"
                style={{ color: "var(--text-muted)" }}
              >
                Signal Intel
              </span>
            </div>
          </div>

          {/* Nav tabs — scrollable on narrow screens */}
          <nav
            className="flex items-stretch gap-0 pl-2 flex-1 h-full"
            style={{ overflowX: "auto", scrollbarWidth: "none" }}
          >
            {NAV_ITEMS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className="relative flex items-center px-4 h-full transition-colors duration-100"
                style={({ isActive }) => ({
                  color: isActive ? "var(--accent-cyan)" : "var(--text-secondary)",
                  background: "transparent",
                  fontSize: "12px",
                  fontFamily: "var(--font-display)",
                  fontWeight: 600,
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                  textDecoration: "none",
                })}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLElement;
                  if (!el.querySelector(".active-bar")) {
                    el.style.color = "var(--text-primary)";
                  }
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLElement;
                  if (!el.querySelector(".active-bar")) {
                    el.style.color = "var(--text-secondary)";
                  }
                }}
              >
                {({ isActive }) => (
                  <>
                    {label}
                    {/* Active underline */}
                    {isActive && (
                      <span
                        className="active-bar"
                        style={{
                          position: "absolute",
                          bottom: 0,
                          left: "12px",
                          right: "12px",
                          height: "2px",
                          background: "var(--accent-cyan)",
                          boxShadow: "0 0 8px var(--accent-cyan)",
                          borderRadius: "2px 2px 0 0",
                        }}
                      />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Right controls — never compress */}
          <div className="flex items-center gap-3 pl-4 shrink-0" style={{ borderLeft: "1px solid var(--border)", flexShrink: 0 }}>

            {/* System status */}
            <div className="flex items-center gap-1.5">
              <Radio
                size={9}
                className="blink-dot"
                style={{ color: "var(--accent-green)" }}
              />
              <span
                className="font-mono text-[9px] tracking-widest uppercase"
                style={{ color: "var(--accent-green)" }}
              >
                Online
              </span>
            </div>

            <div style={{ width: "1px", height: "16px", background: "var(--border)" }} />

            {/* Clock */}
            <span
              className="font-mono text-[11px] tabular-nums"
              style={{ color: "var(--text-muted)" }}
            >
              {clock}
            </span>

            <div style={{ width: "1px", height: "16px", background: "var(--border)" }} />

            {/* Date picker */}
            <input
              type="date"
              value={asOf ?? ""}
              onChange={handleDateChange}
              className="font-mono text-[11px] px-2 py-1 rounded"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
                colorScheme: "dark",
                outline: "none",
              }}
            />

            <div style={{ width: "1px", height: "16px", background: "var(--border)" }} />

            {/* Role chip */}
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded"
              style={{
                background: "rgba(0,216,255,0.07)",
                border: "1px solid rgba(0,216,255,0.2)",
              }}
            >
              <span
                className="blink-dot"
                style={{
                  display: "inline-block",
                  width: "5px",
                  height: "5px",
                  borderRadius: "50%",
                  background: "var(--accent-green)",
                  boxShadow: "0 0 6px var(--accent-green)",
                  flexShrink: 0,
                }}
              />
              <span
                className="font-display font-semibold text-[10px] tracking-widest"
                style={{ color: "var(--accent-cyan)" }}
              >
                {role}
              </span>
            </div>
          </div>
        </div>

        {/* Context strip: breadcrumb below the nav when an org is active */}
        {orgName && (
          <div
            className="flex items-center gap-2 px-5 py-1.5"
            style={{
              borderTop: "1px solid var(--border)",
              background: "var(--bg-elevated)",
            }}
          >
            <span
              className="font-mono text-[9px] tracking-widest uppercase"
              style={{ color: "var(--text-muted)" }}
            >
              ORG
            </span>
            <span style={{ color: "var(--text-muted)", fontSize: "9px" }}>›</span>
            <span
              className="font-display text-[11px] font-semibold tracking-wide"
              style={{ color: "var(--text-primary)" }}
            >
              {orgName}
            </span>
          </div>
        )}
      </header>

      {/* ── Content ── */}
      <main className="flex-1 overflow-auto cockpit-grid p-6">
        {children}
      </main>
    </div>
  );
}
