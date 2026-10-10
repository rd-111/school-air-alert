"""General activity-planning notes; no activity-specific safety thresholds exist."""

ACTIVITIES = ("pe", "sports", "recess", "assembly", "bus_wait")


def activity_guidance(status: str, *, complete_school_hours: bool) -> list[dict[str, str]]:
    """Attach transparent general guidance without inventing activity rules."""
    if status not in {"GREEN", "YELLOW", "RED", "UNKNOWN"}:
        raise ValueError("status must be a supported forecast status")
    if not complete_school_hours or status == "UNKNOWN":
        code = "INCOMPLETE_FORECAST"
    elif status == "RED":
        code = "RED_POLICY_REVIEW"
    else:
        code = "GENERAL_POLICY"
    return [{"activity": activity, "guidance_code": code} for activity in ACTIVITIES]
