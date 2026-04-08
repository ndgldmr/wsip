import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OrgOverview } from "@/pages/OrgOverview";
import { SelectOrg } from "@/pages/SelectOrg";
import { TeamView } from "@/pages/TeamView";
import { EmployeeProfile } from "@/pages/EmployeeProfile";
import { Recommendations } from "@/pages/Recommendations";
import { Simulation } from "@/pages/Simulation";
import { ErrorBoundary } from "@/components/ErrorBoundary";

// Register axios interceptor for 401/403 handling
import "@/api/errors";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (
          error &&
          typeof error === "object" &&
          "name" in error &&
          (error as { name: string }).name === "ApiError"
        ) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/orgs" replace />} />
          <Route path="/orgs" element={<ErrorBoundary><SelectOrg /></ErrorBoundary>} />
          <Route path="/orgs/:id" element={<ErrorBoundary><OrgOverview /></ErrorBoundary>} />
          <Route path="/teams/:id" element={<ErrorBoundary><TeamView /></ErrorBoundary>} />
          <Route path="/employees/:id" element={<ErrorBoundary><EmployeeProfile /></ErrorBoundary>} />
          <Route path="/recommendations" element={<ErrorBoundary><Recommendations /></ErrorBoundary>} />
          <Route path="/simulations" element={<ErrorBoundary><Simulation /></ErrorBoundary>} />
          <Route path="/teams" element={<SelectHint label="Select a team from the Org Overview." />} />
          <Route path="/employees" element={<SelectHint label="Select an employee from a Team View." />} />
          <Route path="/insights" element={<SelectHint label="Insights are shown on the Employee Profile." />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function SelectHint({ label }: { label: string }) {
  return (
    <div
      className="flex items-center justify-center h-screen text-sm"
      style={{ background: "var(--bg-default)", color: "var(--text-muted)" }}
    >
      {label}
    </div>
  );
}
