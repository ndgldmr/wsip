"""
Persona definitions for synthetic data generation.

Each persona models a distinct employee archetype with realistic daily signal
rates (Poisson lambdas) and trajectory modifiers.
"""

from dataclasses import dataclass, field


@dataclass
class PersonaConfig:
    name: str
    role_family: str                  # engineering / research / management / ops
    job_levels: list[str] = field(default_factory=list)

    # Daily Poisson lambda for each signal type (expected events per working day)
    commit_lambda: float = 0.0
    pr_lambda: float = 0.0
    review_lambda: float = 0.0
    experiment_lambda: float = 0.0
    research_artifact_lambda: float = 0.0
    doc_lambda: float = 0.0
    task_lambda: float = 0.0
    meeting_lambda: float = 0.0
    meeting_duration_mean: float = 45.0   # minutes per meeting
    chat_lambda: float = 0.0
    training_lambda: float = 0.0          # probability of a training event per month

    # Skill / collaboration profile (0–1)
    skill_depth: float = 0.5              # drives inferred_skill_score breadth
    collab_breadth: float = 0.5          # drives unique collaborator edges

    # Trajectory controls how daily rates scale over time
    # stable: constant; rising: 0.3→1.0 ramp; declining: 1.0→0.3 ramp
    trajectory: str = "stable"

    # Fraction of employees with this persona (used by generator for distribution)
    population_weight: float = 0.1


PERSONAS: dict[str, PersonaConfig] = {
    # -------------------------------------------------------------------------
    # High-volume coder; primary signal is git commits and PRs
    # -------------------------------------------------------------------------
    "prolific_engineer": PersonaConfig(
        name="prolific_engineer",
        role_family="engineering",
        job_levels=["L3", "L4", "L5"],
        commit_lambda=5.0,
        pr_lambda=0.8,
        review_lambda=1.2,
        experiment_lambda=0.1,
        research_artifact_lambda=0.01,
        doc_lambda=0.3,
        task_lambda=2.0,
        meeting_lambda=1.2,
        meeting_duration_mean=35.0,
        chat_lambda=8.0,
        training_lambda=0.15,
        skill_depth=0.7,
        collab_breadth=0.5,
        trajectory="stable",
        population_weight=0.20,
    ),

    # -------------------------------------------------------------------------
    # Deep research focus; experiments and artifacts dominate; few commits
    # -------------------------------------------------------------------------
    "deep_researcher": PersonaConfig(
        name="deep_researcher",
        role_family="research",
        job_levels=["R3", "R4", "R5"],
        commit_lambda=0.2,
        pr_lambda=0.05,
        review_lambda=0.15,
        experiment_lambda=2.0,
        research_artifact_lambda=0.15,
        doc_lambda=0.5,
        task_lambda=0.5,
        meeting_lambda=1.5,
        meeting_duration_mean=60.0,
        chat_lambda=4.0,
        training_lambda=0.25,
        skill_depth=0.9,
        collab_breadth=0.3,
        trajectory="stable",
        population_weight=0.15,
    ),

    # -------------------------------------------------------------------------
    # Cross-team connector; high meetings, reviews, docs — the invisible glue
    # -------------------------------------------------------------------------
    "glue_person": PersonaConfig(
        name="glue_person",
        role_family="engineering",
        job_levels=["L4", "L5", "L6"],
        commit_lambda=1.5,
        pr_lambda=0.3,
        review_lambda=2.5,
        experiment_lambda=0.2,
        research_artifact_lambda=0.03,
        doc_lambda=1.2,
        task_lambda=1.5,
        meeting_lambda=3.5,
        meeting_duration_mean=50.0,
        chat_lambda=12.0,
        training_lambda=0.10,
        skill_depth=0.6,
        collab_breadth=0.9,
        trajectory="stable",
        population_weight=0.15,
    ),

    # -------------------------------------------------------------------------
    # Senior expert producing little output; underutilized relative to skill
    # -------------------------------------------------------------------------
    "underutilized_expert": PersonaConfig(
        name="underutilized_expert",
        role_family="research",
        job_levels=["R4", "R5", "R6"],
        commit_lambda=0.3,
        pr_lambda=0.05,
        review_lambda=0.2,
        experiment_lambda=0.4,
        research_artifact_lambda=0.05,
        doc_lambda=0.2,
        task_lambda=0.4,
        meeting_lambda=0.8,
        meeting_duration_mean=55.0,
        chat_lambda=2.0,
        training_lambda=0.05,
        skill_depth=0.95,
        collab_breadth=0.2,
        trajectory="stable",
        population_weight=0.10,
    ),

    # -------------------------------------------------------------------------
    # Tech lead / manager drowning in meetings and coordination; declining output
    # -------------------------------------------------------------------------
    "overloaded_lead": PersonaConfig(
        name="overloaded_lead",
        role_family="management",
        job_levels=["L6", "L7", "M1"],
        commit_lambda=1.0,
        pr_lambda=0.15,
        review_lambda=1.5,
        experiment_lambda=0.3,
        research_artifact_lambda=0.02,
        doc_lambda=0.8,
        task_lambda=1.0,
        meeting_lambda=6.0,
        meeting_duration_mean=55.0,
        chat_lambda=15.0,
        training_lambda=0.05,
        skill_depth=0.7,
        collab_breadth=0.8,
        trajectory="declining",
        population_weight=0.10,
    ),

    # -------------------------------------------------------------------------
    # Quietly disengaging; activity drops steadily with no visible incident
    # -------------------------------------------------------------------------
    "silent_disengagement": PersonaConfig(
        name="silent_disengagement",
        role_family="engineering",
        job_levels=["L3", "L4", "L5"],
        commit_lambda=2.0,
        pr_lambda=0.3,
        review_lambda=0.4,
        experiment_lambda=0.1,
        research_artifact_lambda=0.01,
        doc_lambda=0.2,
        task_lambda=1.0,
        meeting_lambda=1.0,
        meeting_duration_mean=40.0,
        chat_lambda=3.0,
        training_lambda=0.03,
        skill_depth=0.5,
        collab_breadth=0.3,
        trajectory="declining",
        population_weight=0.06,
    ),

    # -------------------------------------------------------------------------
    # High-potential engineer ramping up across all dimensions
    # -------------------------------------------------------------------------
    "rising_star": PersonaConfig(
        name="rising_star",
        role_family="engineering",
        job_levels=["L3", "L4"],
        commit_lambda=2.5,
        pr_lambda=0.4,
        review_lambda=0.6,
        experiment_lambda=0.3,
        research_artifact_lambda=0.04,
        doc_lambda=0.4,
        task_lambda=1.5,
        meeting_lambda=1.5,
        meeting_duration_mean=40.0,
        chat_lambda=6.0,
        training_lambda=0.30,
        skill_depth=0.5,
        collab_breadth=0.6,
        trajectory="rising",
        population_weight=0.08,
    ),

    # -------------------------------------------------------------------------
    # Deep narrow research domain; very high experiment volume, minimal other signals
    # -------------------------------------------------------------------------
    "specialist_researcher": PersonaConfig(
        name="specialist_researcher",
        role_family="research",
        job_levels=["R4", "R5"],
        commit_lambda=0.1,
        pr_lambda=0.02,
        review_lambda=0.1,
        experiment_lambda=3.0,
        research_artifact_lambda=0.2,
        doc_lambda=0.3,
        task_lambda=0.3,
        meeting_lambda=0.8,
        meeting_duration_mean=70.0,
        chat_lambda=2.0,
        training_lambda=0.20,
        skill_depth=0.98,
        collab_breadth=0.15,
        trajectory="stable",
        population_weight=0.04,
    ),

    # -------------------------------------------------------------------------
    # People manager; almost no code; very high meeting load
    # -------------------------------------------------------------------------
    "meeting_heavy_manager": PersonaConfig(
        name="meeting_heavy_manager",
        role_family="management",
        job_levels=["M1", "M2", "M3"],
        commit_lambda=0.05,
        pr_lambda=0.01,
        review_lambda=0.1,
        experiment_lambda=0.0,
        research_artifact_lambda=0.0,
        doc_lambda=0.6,
        task_lambda=0.5,
        meeting_lambda=8.0,
        meeting_duration_mean=50.0,
        chat_lambda=18.0,
        training_lambda=0.08,
        skill_depth=0.3,
        collab_breadth=0.95,
        trajectory="stable",
        population_weight=0.10,
    ),

    # -------------------------------------------------------------------------
    # Recent hire in the first year; low baseline, rising trajectory
    # -------------------------------------------------------------------------
    "new_hire_ramp": PersonaConfig(
        name="new_hire_ramp",
        role_family="engineering",
        job_levels=["L2", "L3"],
        commit_lambda=0.5,
        pr_lambda=0.1,
        review_lambda=0.2,
        experiment_lambda=0.1,
        research_artifact_lambda=0.01,
        doc_lambda=0.2,
        task_lambda=0.8,
        meeting_lambda=2.0,
        meeting_duration_mean=45.0,
        chat_lambda=5.0,
        training_lambda=0.50,
        skill_depth=0.3,
        collab_breadth=0.4,
        trajectory="rising",
        population_weight=0.02,
    ),
}

# Ordered persona list for deterministic distribution assignment
PERSONA_NAMES: list[str] = list(PERSONAS.keys())

# Weights array parallel to PERSONA_NAMES (must sum to 1.0)
PERSONA_WEIGHTS: list[float] = [PERSONAS[n].population_weight for n in PERSONA_NAMES]
