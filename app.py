"""ProjectScope — Smart Project Estimator (Flask entry point)."""
import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

from services import ai_service, estimator  # noqa: E402
from services.demo_data import get_demo_plan  # noqa: E402
from services.plan_schema import AIResponseError, parse_plan  # noqa: E402
from services.validation import (  # noqa: E402
    CURRENCIES, DEFAULTS, IDEA_MAX, PLATFORMS,
    RequestValidationError, validate_estimate_request,
)

logger = logging.getLogger("projectscope")
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


def error(message, status, **extra):
    body = {"ok": False, "error": message}
    body.update(extra)
    return jsonify(body), status


def build_response(plan, params, mode):
    estimates = estimator.calculate(plan["task_estimates"], params)
    if params.get("title") and mode == "live":
        plan["user_title"] = params["title"]
    return {"ok": True, "mode": mode, "plan": plan, "estimates": estimates}


@app.get("/")
def index():
    return render_template(
        "index.html",
        ai_configured=ai_service.is_configured(),
        platforms=PLATFORMS, currencies=CURRENCIES,
        defaults=DEFAULTS, idea_max=IDEA_MAX,
    )


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "ai_configured": ai_service.is_configured()})


@app.post("/api/estimate")
def estimate():
    data = request.get_json(silent=True)
    try:
        params = validate_estimate_request(data)
    except RequestValidationError as exc:
        return error("Please fix the highlighted fields.", 400, fields=exc.errors)

    demo = bool(isinstance(data, dict) and data.get("demo"))
    if demo:
        if ai_service.is_configured():
            return error("Demo mode is only available when no AI key is configured.", 400)
        plan = parse_plan(get_demo_plan())
        return jsonify(build_response(plan, params, "demo"))

    try:
        plan = ai_service.generate_plan(params)
    except ai_service.AIConfigError:
        return error(
            "Live AI is not configured. Add AI_API_KEY in your environment, or try the labelled demo.",
            503, code="ai_not_configured",
        )
    except AIResponseError as exc:
        logger.warning("Invalid AI response: %s", exc)
        return error("The AI returned an incomplete plan. Please try again.", 502, code="ai_invalid_response", retryable=True)
    except ai_service.AIServiceError:
        logger.exception("AI service failure")
        return error("The AI service is unavailable right now. Please try again.", 502, code="ai_failure", retryable=True)
    except Exception:  # never leak stack traces
        logger.exception("Unexpected error")
        return error("Something went wrong. Please try again.", 500, retryable=True)

    try:
        return jsonify(build_response(plan, params, "live"))
    except ValueError:
        return error("Could not calculate the estimate for these inputs.", 400)


@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return error("Not found.", 404)
    return render_template(
        "index.html", ai_configured=ai_service.is_configured(),
        platforms=PLATFORMS, currencies=CURRENCIES, defaults=DEFAULTS, idea_max=IDEA_MAX,
    ), 404


@app.errorhandler(405)
def method_not_allowed(_e):
    return error("Method not allowed.", 405)


@app.errorhandler(413)
def too_large(_e):
    return error("Request is too large.", 413)


@app.errorhandler(500)
def server_error(_e):
    return error("Something went wrong. Please try again.", 500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or 5000)
    app.run(host="0.0.0.0", port=port, debug=False)
