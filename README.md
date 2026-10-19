# ProjectScope — Smart Project Estimator

> From idea to implementation, smarter and faster.

Describe a software idea and get a structured plan back: features, tech stack, task estimates, roadmap, risks and assumptions.
The AI (Google Gemini) does the analysis and breaks the idea into tasks. **Python calculates every total**: hours, weeks, base cost, contingency and budget.

## Stack
Flask, plain HTML/CSS/JavaScript, `google-genai` and pytest. There is no database and no login.

## Setup
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py            # open http://localhost:5000
```
You can also run `npm install` and then `npm run dev`. These npm scripts only wrap the pip install and `python app.py`.

## Turning on live AI
1. Get a free Gemini API key at https://aistudio.google.com/apikey.
2. Copy `.env.example` to `.env` and set `AI_API_KEY=...`. In the hosted preview, add it in the **Secrets panel** instead.
   `AI_MODEL` is optional and defaults to `gemini-2.5-flash`.
3. Restart the app. The header badge changes to "Live AI ready".

With no key set, the app shows a setup message and a **clearly labelled demo**. The demo is a fixed sample plan, and your form values are still used for the calculations.
If a live request fails, you get an error message and a Retry button. The app never swaps in demo data without telling you.

## PDF export (optional)
On the results dashboard, click **Download PDF** to save the report. The PDF is built with ReportLab, which is listed in `requirements.txt`.
The browser sends back the plan and form inputs, and the server checks the plan again and **recalculates every total** before building the PDF, so numbers can't be changed on the client side.
If ReportLab isn't installed, the endpoint returns a clear message (HTTP 501) and **Print report** still works.

## API
- `GET /api/health` returns `{status, ai_configured, pdf_available}`.
- `POST /api/report.pdf` takes `{request: {...same fields as /api/estimate}, plan, mode}` and returns `application/pdf`.
- `POST /api/estimate` takes `{idea, title?, platform, team_size, weekly_hours, hourly_rate, currency, contingency_percent}` and returns `{ok, mode, plan, estimates}`.
  Status codes: 400 for invalid input, 502 when the AI fails or returns an invalid response (retryable), 503 when AI is not configured.

## Formulas
- Total hours = sum of the validated task hours
- Weeks = hours ÷ (weekly hours × team size). The screen shows this rounded up, with the exact value next to it.
- Base = hours × rate. Contingency = base × % ÷ 100. Total = base + contingency.

All figures are approximate. Infrastructure costs are not included and no currency conversion is done.

## Tests
```bash
python -m pytest -q
```
The AI is mocked in every test, so running them makes no paid API calls.

## Structure
```
app.py                    Flask routes
services/ai_service.py    Gemini integration and prompt (all provider code)
services/plan_schema.py   AI JSON parsing and schema validation
services/estimator.py     hours, duration and budget math
services/validation.py    request validation
services/demo_data.py     fixed demo plan
services/pdf_report.py    optional ReportLab PDF report
templates/index.html      page
static/css, static/js     styles (including print) and safe DOM rendering
tests/test_app.py         pytest suite
```
