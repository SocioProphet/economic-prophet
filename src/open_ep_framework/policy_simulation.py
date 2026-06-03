from __future__ import annotations

import json
from pathlib import Path

from .validation import validate_json_file


def load_policy_simulation_profile(path: str) -> dict:
    """Load and validate a policy simulation profile.

    The profile is a schema-first assimilation boundary for economic simulation
    patterns. It deliberately does not import donor runtimes, start training jobs,
    or authorize live policy actions.
    """
    validate_json_file(path, "schemas/policy_simulation_profile.schema.json")
    return json.loads(Path(path).read_text())


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def summarize_policy_simulation_profile(data: dict) -> dict:
    """Return deterministic audit-facing summary metrics for a profile."""
    faces = data.get("triparty_faces", [])
    gross_quantity = sum(float(face.get("lambda_evid", 0.0)) for face in faces)
    admitted_quantity = sum(float(face.get("lambda_admit", 0.0)) for face in faces)
    released_quantity = sum(float(face.get("lambda_release", 0.0)) for face in faces)
    residual_quantity = sum(float(face.get("residual", 0.0)) for face in faces)

    return {
        "profile_id": data.get("profile_id", ""),
        "scenario_id": data.get("scenario", {}).get("scenario_id", ""),
        "actor_count": len(data.get("actors", [])),
        "component_count": len(data.get("components", [])),
        "reward_functional_count": len(data.get("reward_functionals", [])),
        "triparty_face_count": len(faces),
        "runtime_dependency": data.get("donor_corpus", {}).get("runtime_dependency", False),
        "gross_quantity": gross_quantity,
        "admitted_quantity": admitted_quantity,
        "released_quantity": released_quantity,
        "residual_quantity": residual_quantity,
        "admission_ratio": _safe_ratio(admitted_quantity, gross_quantity),
        "release_ratio": _safe_ratio(released_quantity, gross_quantity),
        "residual_ratio": _safe_ratio(residual_quantity, gross_quantity),
        "replay_available": data.get("audit_receipt", {}).get("replay_available", False),
    }


def run_policy_simulation_profile(path: str) -> dict:
    """Load a profile and return summary plus validated profile data."""
    data = load_policy_simulation_profile(path)
    return {
        "summary": summarize_policy_simulation_profile(data),
        "profile": data,
    }
