"""Parse and schema-check the AI's JSON plan. Produces a clean, normalised dict."""
import json
import math


class AIResponseError(Exception):
    """The AI response was malformed or incomplete (retryable)."""


PRIORITIES = {"high", "medium", "low"}
SEVERITIES = {"high", "medium", "low"}
CONFIDENCE = {"low", "medium", "high"}
FEATURE_CATEGORIES = {"mvp", "future"}
MAX_TEXT = 2000
MAX_ITEMS = 60
MAX_TASK_HOURS = 5000


def _text(value, field, required=True, max_len=MAX_TEXT):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise AIResponseError(f"Missing field: {field}")
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str):
        raise AIResponseError(f"Field {field} must be text")
    return value.strip()[:max_len]


def _text_list(value, field, required=True):
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        if required:
            raise AIResponseError(f"Field {field} must be a list")
        return []
    items = [_text(v, field, required=False) for v in value[:MAX_ITEMS]]
    items = [i for i in items if i]
    if required and not items:
        raise AIResponseError(f"Field {field} is empty")
    return items


def _obj_list(value, field, required=True):
    if not isinstance(value, list) or (required and not value):
        raise AIResponseError(f"Field {field} must be a non-empty list")
    items = [v for v in value[:MAX_ITEMS] if isinstance(v, dict)]
    if required and not items:
        raise AIResponseError(f"Field {field} has no valid items")
    return items


def _hours(value, field, required=True):
    if value is None and not required:
        return None
    if isinstance(value, bool):
        raise AIResponseError(f"Invalid hours in {field}")
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise AIResponseError(f"Invalid hours in {field}")
    if not math.isfinite(num) or num < 0 or num > MAX_TASK_HOURS:
        raise AIResponseError(f"Hours out of range in {field}")
    return round(num, 2)


def _choice(value, allowed, default):
    v = str(value or "").strip().lower()
    return v if v in allowed else default


def parse_plan(raw):
    """Accept a JSON string or dict and return a validated plan dict."""
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        try:
            raw = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            raise AIResponseError("AI returned malformed JSON")
    if not isinstance(raw, dict):
        raise AIResponseError("AI response is not a JSON object")

    plan = {
        "project_title": _text(raw.get("project_title"), "project_title", max_len=150),
        "project_summary": _text(raw.get("project_summary"), "project_summary"),
        "project_category": _text(raw.get("project_category"), "project_category", max_len=150),
        "problem_statement": _text(raw.get("problem_statement"), "problem_statement"),
        "target_users": _text_list(raw.get("target_users"), "target_users"),
        "objectives": _text_list(raw.get("objectives"), "objectives"),
        "requirements": _text_list(raw.get("requirements"), "requirements"),
        "assumptions": _text_list(raw.get("assumptions"), "assumptions"),
        "missing_information": _text_list(
            raw.get("missing_information"), "missing_information", required=False
        ),
        "confidence": _choice(raw.get("confidence"), CONFIDENCE, None),
    }
    if plan["confidence"] is None:
        raise AIResponseError("Invalid or missing confidence")

    plan["features"] = [
        {
            "name": _text(f.get("name"), "features.name", max_len=200),
            "description": _text(f.get("description"), "features.description", required=False),
            "category": _choice(f.get("category"), FEATURE_CATEGORIES, "mvp"),
            "priority": _choice(f.get("priority"), PRIORITIES, "medium"),
            "hours": _hours(f.get("hours"), "features.hours", required=False),
        }
        for f in _obj_list(raw.get("features"), "features")
    ]
    plan["technology_stack"] = [
        {
            "name": _text(t.get("name"), "technology_stack.name", max_len=150),
            "category": _text(t.get("category"), "technology_stack.category", required=False, max_len=100) or "Other",
            "reason": _text(t.get("reason"), "technology_stack.reason", required=False),
        }
        for t in _obj_list(raw.get("technology_stack"), "technology_stack")
    ]
    plan["task_estimates"] = [
        {
            "name": _text(t.get("name"), "task_estimates.name", max_len=200),
            "description": _text(t.get("description"), "task_estimates.description", required=False),
            "hours": _hours(t.get("hours"), "task_estimates.hours"),
        }
        for t in _obj_list(raw.get("task_estimates"), "task_estimates")
    ]
    roadmap = []
    for i, r in enumerate(_obj_list(raw.get("roadmap"), "roadmap"), start=1):
        try:
            seq = int(r.get("sequence", i))
        except (TypeError, ValueError):
            seq = i
        roadmap.append({
            "sequence": seq,
            "title": _text(r.get("title"), "roadmap.title", max_len=200),
            "description": _text(r.get("description"), "roadmap.description", required=False),
            "priority": _choice(r.get("priority"), PRIORITIES, "medium"),
            "dependencies": _text_list(r.get("dependencies"), "roadmap.dependencies", required=False),
        })
    plan["roadmap"] = sorted(roadmap, key=lambda r: r["sequence"])
    plan["risks"] = [
        {
            "description": _text(r.get("description"), "risks.description"),
            "severity": _choice(r.get("severity"), SEVERITIES, "medium"),
            "mitigation": _text(r.get("mitigation"), "risks.mitigation", required=False),
        }
        for r in _obj_list(raw.get("risks"), "risks")
    ]
    if sum(t["hours"] for t in plan["task_estimates"]) <= 0:
        raise AIResponseError("Task estimates contain no hours")
    return plan
