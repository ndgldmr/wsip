import type { ReactNode } from "react";
import { ShieldOff } from "lucide-react";
import { isAccessDenied } from "@/api/errors";
import { useEmployeeProfile, type EmployeeProfileOut } from "@/api/employees";

interface AuditGateProps {
  employeeId: string;
  asOf: string;
  children: (profile: EmployeeProfileOut) => ReactNode;
}

export function AuditGate({ employeeId, asOf, children }: AuditGateProps) {
  const { data, isLoading, error } = useEmployeeProfile(employeeId, asOf);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 p-6 animate-pulse">
        <div className="h-6 w-48 rounded" style={{ background: "var(--bg-elevated)" }} />
        <div className="h-4 w-32 rounded" style={{ background: "var(--bg-elevated)" }} />
        <div className="grid grid-cols-5 gap-4 mt-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 rounded" style={{ background: "var(--bg-elevated)" }} />
          ))}
        </div>
      </div>
    );
  }

  if (isAccessDenied(error)) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <ShieldOff size={36} style={{ color: "var(--accent-red)" }} />
        <div className="text-center">
          <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
            Access restricted.
          </p>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Your access attempt has been logged.
          </p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div
        className="flex items-center justify-center h-32 text-sm"
        style={{ color: "var(--text-muted)" }}
      >
        Employee not found.
      </div>
    );
  }

  return <>{children(data)}</>;
}
