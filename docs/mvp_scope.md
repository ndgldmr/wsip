# WSIP MVP Scope

**Role**: PM
**Sprint**: S1
**Status**: Approved

---

## MVP Capabilities

The MVP delivers a working analytics pipeline for **one org's synthetic dataset** covering ~300 employees over ~365 days.

### Five core metrics (all 0–1 normalized scores)

| Metric | What it detects |
|---|---|
| **Underutilization** | Mismatch between expected allocation and observed work signals |
| **Overload** | Sustained high meeting load + context switching + execution strain |
| **Disengagement risk** | Sustained activity drop across multiple signal dimensions |
| **Skill utilization** | Gap between employee skills and the work they're actually doing |
| **Glue person score** | Connective contribution — cross-team interactions, reviews, facilitation |

### Insight engine v1

- Rule-based threshold evaluations on feature snapshots
- Each insight includes: `insight_type`, `severity` (critical/high/medium/low), human-readable `insight_description` naming the driving inputs
- Linked `recommendations` with `recommendation_type` and `recommendation_text`

### Modeling

- Archetype clustering (KMeans/GMM) — categorizes employees into 8 contribution archetypes
- Trajectory predictions (baseline logistic/ridge regression) — 60-day forward-looking risk/impact
- Pre/post impact analysis — metric delta windows around `employee_change_events`
- Simulation sandbox — deterministic what-if staffing scenarios

### Access control

- Role-based: `admin`, `org_analytics`, `manager`, `hrbp`
- Object-level: `viewer_permissions` table for explicit individual grants
- Audit logging: every access to individual employee data logged with who/what/when/outcome

### UI (5 pages)

- Org overview — risk KPIs across the organization
- Team view — health metrics + member summary + trends
- Employee profile — individual drill-down (RBAC gated)
- Recommendations — triage queue with accept/feedback
- Simulation sandbox — create staffing moves, compute outcomes

---

## Explicit Non-Goals (MVP)

- **No real connectors** — no integration with GitLab, HRIS, Slack/Teams, or calendar systems
- **No message content** — WSIP never stores or processes message bodies, doc contents, audio transcripts, or keystrokes
- **No automated performance ratings or rankings** — WSIP surfaces signals; humans make decisions
- **No complex streaming ingestion** — batch pipeline only
- **No multi-tenancy** — single organization in MVP
- **No self-service sign-up** — tokens provisioned manually via env var

---

## Sensitive Views

The following views require explicit authorization checks and write an `access_audit_log` row on every access (success or denied):

| View | Endpoint(s) | Required permission |
|---|---|---|
| Employee profile drill-down | `GET /employees/{id}/profile` | `admin`, `hrbp`, or manager of that employee, or explicit `viewer_permissions` grant |
| Employee activity timeline | `GET /employees/{id}/timeline` | Same as above |
| Individual insights | `GET /employees/{id}/insights` | Same as above |
| Simulation with named employees | `POST /simulations/*/moves` | `admin`, `manager`, `hrbp` |
| Audit log retrieval | `GET /admin/audit-log` | `admin` only |

---

## RBAC Roles

| Role | Can see | Cannot see |
|---|---|---|
| `admin` | Everything, including individual profiles, audit log, and simulation | — |
| `org_analytics` | Org/team aggregate views, insights at team/org scope | Individual employee profiles |
| `manager` | Their team's aggregate view + direct reports' individual profiles | Other employees' profiles, audit log |
| `hrbp` | Any employee's individual profile (with audit log) | Audit log contents |

---

## Data Minimization Statement

WSIP is constrained to **metadata signals only**:
- Counts and timestamps (e.g., number of commits, meeting duration)
- Relationship identifiers (who reviewed whose PR, who attended which meeting)
- Derived aggregate scores

WSIP does **not** collect, process, or store:
- Message or document content
- Audio or video recordings
- Keystrokes or screen activity
- Biometric data

Data is collected and processed only for the purposes defined in this document (alignment and utilization insights). Signals will not be repurposed for disciplinary actions, performance ranking, or any purpose not explicitly approved by the data governance process.
