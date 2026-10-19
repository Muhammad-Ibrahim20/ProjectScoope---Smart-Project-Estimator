"""Validation for incoming estimate requests."""
import math

PLATFORMS = ["Web", "Mobile", "Desktop", "Cross-platform"]
CURRENCIES = ["PKR", "USD"]
IDEA_MIN, IDEA_MAX = 20, 3000
TITLE_MAX = 120
DEFAULTS = {
    "platform": "Web",
    "team_size": 2,
    "weekly_hours": 20,
    "hourly_rate": 1500,
    "currency": "PKR",
    "contingency_percent": 15,
}


class RequestValidationError(Exception):
    """Raised when user input is invalid. `errors` maps field -> message."""

    def __init__(self, errors):
        super().__init__("Invalid request")
        self.errors = errors


def _number(value, field, errors, integer=False):
    if isinstance(value, bool) or value is None or value == "":
        errors[field] = "Must be a number."
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        errors[field] = "Must be a number."
        return None
    if not math.isfinite(num):
        errors[field] = "Must be a finite number."
        return None
    if integer:
        if num != int(num):
            errors[field] = "Must be a whole number."
            return None
        return int(num)
    return num


def validate_estimate_request(data):
    """Return a clean params dict or raise RequestValidationError."""
    if not isinstance(data, dict):
        raise RequestValidationError({"body": "Request body must be a JSON object."})
    errors = {}

    idea = data.get("idea")
    idea = idea.strip() if isinstance(idea, str) else ""
    if not idea:
        errors["idea"] = "Please describe your software idea."
    elif len(idea) < IDEA_MIN:
        errors["idea"] = f"Description must be at least {IDEA_MIN} characters."
    elif len(idea) > IDEA_MAX:
        errors["idea"] = f"Description must be at most {IDEA_MAX} characters."

    title = data.get("title") or ""
    title = title.strip() if isinstance(title, str) else ""
    if len(title) > TITLE_MAX:
        errors["title"] = f"Title must be at most {TITLE_MAX} characters."

    platform = data.get("platform", DEFAULTS["platform"]) or DEFAULTS["platform"]
    if platform not in PLATFORMS:
        errors["platform"] = "Platform must be one of: " + ", ".join(PLATFORMS) + "."

    def get(field):
        value = data.get(field)
        return DEFAULTS[field] if value is None else value

    team_size = _number(get("team_size"), "team_size", errors, integer=True)
    if team_size is not None and not 1 <= team_size <= 20:
        errors["team_size"] = "Team size must be between 1 and 20."

    weekly_hours = _number(get("weekly_hours"), "weekly_hours", errors)
    if weekly_hours is not None and not 1 <= weekly_hours <= 80:
        errors["weekly_hours"] = "Weekly hours must be between 1 and 80."

    hourly_rate = _number(get("hourly_rate"), "hourly_rate", errors)
    if hourly_rate is not None and hourly_rate < 0:
        errors["hourly_rate"] = "Hourly rate cannot be negative."
    elif hourly_rate is not None and hourly_rate > 10_000_000:
        errors["hourly_rate"] = "Hourly rate is unrealistically large."

    currency = get("currency")
    if currency not in CURRENCIES:
        errors["currency"] = "Currency must be one of: " + ", ".join(CURRENCIES) + "."

    contingency = _number(get("contingency_percent"), "contingency_percent", errors)
    if contingency is not None and not 0 <= contingency <= 50:
        errors["contingency_percent"] = "Contingency must be between 0 and 50%."

    if errors:
        raise RequestValidationError(errors)

    return {
        "idea": idea,
        "title": title,
        "platform": platform,
        "team_size": team_size,
        "weekly_hours": weekly_hours,
        "hourly_rate": hourly_rate,
        "currency": currency,
        "contingency_percent": contingency,
    }
