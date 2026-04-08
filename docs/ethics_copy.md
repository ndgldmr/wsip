# WSIP Data Ethics — UI Copy

> This document provides the canonical copy for data ethics disclosures, banners, and
> contextual notes that appear throughout the WSIP interface. All UI text that touches
> individual employee data must reference one of these blocks.

---

## 1. Platform-Level Disclosure (shown on first login and in Settings)

**What this platform does**

WSIP synthesizes signals from the systems your organization already uses — code repositories, task trackers, calendars, and document platforms — to surface team-level patterns that help leaders make better staffing, project, and support decisions.

**What this platform does not do**

WSIP is not a surveillance tool. It does not monitor content (message bodies, document text, code semantics), record keystrokes or screen activity, or produce performance scores that are used directly in compensation or disciplinary decisions.

---

## 2. Aggregate-First Principle (shown above all org/team views)

> **Data shown here is aggregated across teams and roles.**
> No individual employee data is visible on this screen. Insights reflect statistical
> patterns — not assessments of any specific person.

---

## 3. Employee Profile Access Notice (shown at top of every individual profile view)

> **You are viewing an individual employee profile.**
> Access to this view is logged and audited. Use this information to support the employee,
> not to evaluate or compare them without their knowledge.
>
> Role required: `manager` or `hrbp`

---

## 4. Sensitive Signals Footnote (shown near flight-risk, burnout-risk, disengagement scores)

> **How risk scores are calculated**
>
> These scores are derived from changes in work-signal patterns relative to that
> employee's own historical baseline and role-cohort norms. They do not measure intent,
> effort, or performance — only statistical deviation.
>
> A high risk score is a prompt to have a supportive conversation, not a finding of
> misconduct or poor performance.

---

## 5. Simulation Disclosure (shown in the Simulation page header)

> **Simulations use anonymized role archetypes.**
>
> When you model a team composition change, WSIP uses aggregated skill and activity
> profiles — not named individuals — to estimate impact. Results are probabilistic
> estimates, not guarantees.

---

## 6. Right to Explanation (shown in employee-facing exports, if enabled)

> **Your data in WSIP**
>
> Your organization uses WSIP to understand team capacity and health at an aggregate
> level. The signals WSIP uses are drawn from systems you already interact with (git,
> calendar, task tracker) and reflect metadata only — not content.
>
> You have the right to request a summary of the signals associated with your profile.
> Contact your HR Business Partner or People Analytics team to do so.

---

## 7. Data Minimization Statement (internal, shown in Admin → Data Settings)

WSIP ingests only the metadata fields required to compute the analytics in this
platform. Specifically:

| Signal type | Collected | Not collected |
|---|---|---|
| Git | commit timestamp, lines changed, file count | commit message content, diff content |
| Calendar / Meetings | start time, duration, attendee count, meeting type | meeting title, description, attendee identities |
| Chat | message count, channel type, timestamp, after-hours flag | message content, thread content, recipient identities |
| Documents | event timestamp, doc type, action type, word count | document title, document content |
| Tasks | timestamp, type, priority, story points | task description, comments |

---

## 8. Access Control Summary (shown in Admin → Roles)

| Role | What they can see |
|---|---|
| `admin` | All data, generation controls, audit log |
| `org_analytics` | Org overview, team health, aggregated insights — no individual profiles |
| `manager` | Their team's health + individual profiles for direct reports only |
| `hrbp` | Individual profiles for their assigned population |

Access to individual profiles is always logged in the audit trail.

---

## Copy Guidelines for Engineers

- Never use language implying certainty: prefer *"suggests"*, *"indicates"*, *"pattern consistent with"* over *"proves"*, *"shows"*, *"confirms"*.
- Never use language implying blame or judgment: prefer *"activity below cohort baseline"* over *"low performer"*.
- Always pair a risk score with a recommended action that is supportive, not punitive.
- If a score or insight is shown in a context where the employee could see it, add the Right to Explanation block (§6).
