"""
ETL configuration: contribution weight matrices per role_family.

Weights are applied to normalised signal-unit categories to produce a single
`contribution_units` score per employee per day.  The six categories are:

    code           — lines of code, files touched
    research       — experiments, research artefacts
    documentation  — doc events, word volume
    collaboration  — code reviews, meeting participation
    strategic      — placeholder (Sprint 4)
    impact         — story points closed

Weights must sum to 1.0 per role family.  Use "default" for any role_family
not explicitly listed.
"""

CONTRIBUTION_WEIGHTS: dict[str, dict[str, float]] = {
    "engineering": {
        "code": 0.45,
        "research": 0.05,
        "documentation": 0.10,
        "collaboration": 0.20,
        "strategic": 0.05,
        "impact": 0.15,
    },
    "research": {
        "code": 0.15,
        "research": 0.40,
        "documentation": 0.20,
        "collaboration": 0.15,
        "strategic": 0.05,
        "impact": 0.05,
    },
    "management": {
        "code": 0.05,
        "research": 0.05,
        "documentation": 0.15,
        "collaboration": 0.40,
        "strategic": 0.20,
        "impact": 0.15,
    },
    "ops": {
        "code": 0.10,
        "research": 0.05,
        "documentation": 0.25,
        "collaboration": 0.30,
        "strategic": 0.20,
        "impact": 0.10,
    },
    "default": {
        "code": 0.20,
        "research": 0.15,
        "documentation": 0.20,
        "collaboration": 0.25,
        "strategic": 0.10,
        "impact": 0.10,
    },
}
