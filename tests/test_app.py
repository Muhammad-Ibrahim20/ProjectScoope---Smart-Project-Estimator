"""ProjectScope tests. The AI is always mocked; no paid API calls are made."""
import json
from pathlib import Path

import pytest

import app as app_module
from services import ai_service, estimator
from services.demo_data import get_demo_plan
from services.plan_schema import AIResponseError, parse_plan

ROOT = Path(__file__).resolve().parent.parent
VALID = {
    "idea": "An AI-powered resume screening and job matching system",
    "platform": "Web",
    "team_size": 2,
    "weekly_hours": 20,
    "hourly_rate": 1500,
    "currency": "PKR",
    "contingency_percent": 15,
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


@pytest.fixture
def mock_ai(monkeypatch):
    """Pretend the key is set and the model returns the given raw text."""
    def _install(raw):
        monkeypatch.setenv("AI_API_KEY", "test-key-not-real")
        monkeypatch.setattr(ai_service, "_call_model", lambda prompt: raw)
    return _install


def post(client, **overrides):
    body = dict(VALID, **overrides)
    return client.post("/api/estimate", json=body)


# --- Routes -----------------------------------------------------------------

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_index_serves_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Generate Project Plan" in res.data


def test_valid_request_with_mocked_ai(client, mock_ai):
    mock_ai(json.dumps(get_demo_plan()))
    res = post(client)
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] and data["mode"] == "live"
    assert data["estimates"]["total_hours"] == 160
    assert data["estimates"]["total_budget"] == 276000


# --- Request validation -------------------------------------------------------

def test_empty_idea_rejected(client):
    res = post(client, idea="   ")
    assert res.status_code == 400
    assert "idea" in res.get_json()["fields"]


def test_too_long_idea_rejected(client):
    assert post(client, idea="x" * 3001).status_code == 400


@pytest.mark.parametrize("team", [0, -1, 21, 2.5, "abc", ""])
def test_invalid_team_size(client, team):
    res = post(client, team_size=team)
    assert res.status_code == 400
    assert "team_size" in res.get_json()["fields"]


@pytest.mark.parametrize("hours", [0, -5, 81, "x"])
def test_invalid_weekly_hours(client, hours):
    res = post(client, weekly_hours=hours)
    assert res.status_code == 400
    assert "weekly_hours" in res.get_json()["fields"]


def test_negative_rate(client):
    res = post(client, hourly_rate=-1)
    assert res.status_code == 400
    assert "hourly_rate" in res.get_json()["fields"]


@pytest.mark.parametrize("pct", [-1, 51])
def test_invalid_contingency(client, pct):
    assert post(client, contingency_percent=pct).status_code == 400


def test_unsupported_currency(client):
    res = post(client, currency="EUR")
    assert res.status_code == 400
    assert "currency" in res.get_json()["fields"]


def test_non_json_body(client):
    res = client.post("/api/estimate", data="hello", content_type="text/plain")
    assert res.status_code == 400


# --- Estimation engine ---------------------------------------------------------

def test_hours_aggregation():
    tasks = [{"hours": 10}, {"hours": 5.5}, {"hours": 0}]
    assert estimator.total_hours(tasks) == 15.5


def test_duration_math():
    exact, display = estimator.duration_weeks(100, 20, 2)
    assert exact == 2.5 and display == 3
    assert estimator.duration_weeks(80, 20, 2) == (2.0, 2)
    with pytest.raises(ValueError):
        estimator.duration_weeks(10, 0, 2)


def test_contingency_math():
    base, cont, total = estimator.budget(100, 1500, 15)
    assert base == 150000 and cont == 22500 and total == 172500
    assert estimator.budget(10, 0, 15) == (0, 0, 0)


# --- AI response handling ---------------------------------------------------------

def test_malformed_ai_json_returns_retryable_error(client, mock_ai):
    mock_ai("this is not json {")
    res = post(client)
    assert res.status_code == 502
    body = res.get_json()
    assert body["retryable"] is True and body["code"] == "ai_invalid_response"


def test_incomplete_ai_response(client, mock_ai):
    plan = get_demo_plan()
    del plan["task_estimates"]
    mock_ai(json.dumps(plan))
    assert post(client).status_code == 502


def test_negative_task_hours_rejected():
    plan = get_demo_plan()
    plan["task_estimates"][0]["hours"] = -4
    with pytest.raises(AIResponseError):
        parse_plan(plan)


def test_ai_failure_no_leak(client, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "secret-key-123")

    def boom(prompt):
        raise ai_service.AIServiceError("connection refused at internal host")
    monkeypatch.setattr(ai_service, "_call_model", boom)
    res = post(client)
    assert res.status_code == 502
    text = res.get_data(as_text=True)
    assert "secret-key-123" not in text and "internal host" not in text
    assert "Traceback" not in text


def test_no_key_returns_setup_error_not_demo(client):
    res = post(client)
    assert res.status_code == 503
    assert res.get_json()["code"] == "ai_not_configured"


def test_demo_mode_labelled(client):
    res = post(client, demo=True)
    data = res.get_json()
    assert res.status_code == 200 and data["mode"] == "demo"


def test_demo_refused_when_key_configured(client, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "k")
    assert post(client, demo=True).status_code == 400


# --- Safe text handling -------------------------------------------------------------

def test_html_in_ai_text_is_returned_as_plain_data(client, mock_ai):
    plan = get_demo_plan()
    plan["project_title"] = "<script>alert(1)</script>"
    mock_ai(json.dumps(plan))
    data = post(client).get_json()
    assert data["plan"]["project_title"] == "<script>alert(1)</script>"


def test_frontend_never_uses_innerhtml():
    for name in ("render.js", "script.js"):
        src = (ROOT / "static" / "js" / name).read_text(encoding="utf-8")
        assert "innerHTML" not in src and "insertAdjacentHTML" not in src


# --- Full workflow --------------------------------------------------------------------

def test_full_workflow(client, mock_ai):
    plan = get_demo_plan()
    plan["task_estimates"] = [
        {"name": "Design", "description": "UI", "hours": 30},
        {"name": "Build", "description": "Code", "hours": 50},
    ]
    mock_ai(json.dumps(plan))
    res = post(client, team_size=1, weekly_hours=30, hourly_rate=10, currency="USD", contingency_percent=10)
    assert res.status_code == 200
    est = res.get_json()["estimates"]
    assert est["total_hours"] == 80
    assert est["duration_weeks_exact"] == 2.67 and est["duration_weeks"] == 3
    assert est["base_cost"] == 800 and est["contingency_amount"] == 80 and est["total_budget"] == 880
    assert est["currency"] == "USD" and est["approximate"] is True


# --- PDF export (Phase 2) ---------------------------------------------------------------

def _pdf_payload(**overrides):
    payload = {"request": dict(VALID), "plan": parse_plan(get_demo_plan()), "mode": "live"}
    payload.update(overrides)
    return payload


def test_pdf_download(client):
    pytest.importorskip("reportlab")
    res = client.post("/api/report.pdf", json=_pdf_payload())
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    assert res.data.startswith(b"%PDF")
    assert "attachment" in res.headers["Content-Disposition"]


def test_pdf_handles_markup_in_ai_text(client):
    pytest.importorskip("reportlab")
    plan = parse_plan(get_demo_plan())
    plan["project_summary"] = "<b>bold & <unclosed tag"
    res = client.post("/api/report.pdf", json=_pdf_payload(plan=plan))
    assert res.status_code == 200 and res.data.startswith(b"%PDF")


def test_pdf_rejects_invalid_plan(client):
    pytest.importorskip("reportlab")
    plan = parse_plan(get_demo_plan())
    del plan["task_estimates"]
    assert client.post("/api/report.pdf", json=_pdf_payload(plan=plan)).status_code == 400


def test_pdf_rejects_invalid_request(client):
    pytest.importorskip("reportlab")
    bad = dict(VALID, team_size=0)
    assert client.post("/api/report.pdf", json=_pdf_payload(request=bad)).status_code == 400


def test_pdf_unavailable_message(client, monkeypatch):
    monkeypatch.setattr(app_module.pdf_report, "is_available", lambda: False)
    res = client.post("/api/report.pdf", json=_pdf_payload())
    assert res.status_code == 501
    assert res.get_json()["code"] == "pdf_unavailable"


# --- Estimate flow error handling (Phase 1) ---------------------------------------------

def test_unexpected_ai_exception_is_retryable_502(client, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "k")

    def boom(prompt):
        raise RuntimeError("weird provider bug")
    monkeypatch.setattr(ai_service, "_call_model", boom)
    res = post(client)
    assert res.status_code == 502
    body = res.get_json()
    assert body["retryable"] is True and "weird" not in res.get_data(as_text=True)


def test_empty_ai_response_is_502(client, mock_ai):
    mock_ai("   ")
    res = post(client)
    assert res.status_code == 502 and res.get_json()["code"] == "ai_invalid_response"


def test_ai_tuple_with_usage(client, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "k")
    usage = {"prompt_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    monkeypatch.setattr(ai_service, "_call_model", lambda p: (json.dumps(get_demo_plan()), usage))
    res = post(client)
    assert res.status_code == 200
    data = res.get_json()
    assert data["mode"] == "live" and data["usage"]["total_tokens"] == 30


def test_live_failure_never_falls_back_to_demo(client, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "k")

    def boom(prompt):
        raise ai_service.AIServiceError("down")
    monkeypatch.setattr(ai_service, "_call_model", boom)
    body = post(client).get_json()
    assert body["ok"] is False and "plan" not in body
