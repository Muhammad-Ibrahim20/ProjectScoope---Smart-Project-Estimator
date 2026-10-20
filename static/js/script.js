/* Form handling, validation, request lifecycle and view switching. */
(function () {
  "use strict";

  const form = document.getElementById("estimate-form");
  const landing = document.getElementById("landing");
  const results = document.getElementById("results");
  const submitBtn = document.getElementById("submit-btn");
  const demoBtn = document.getElementById("demo-btn");
  const spinner = submitBtn.querySelector(".spinner");
  const label = submitBtn.querySelector(".btn-label");
  const loadingText = document.getElementById("loading-text");
  const errorBox = document.getElementById("form-error");
  const errorText = document.getElementById("form-error-text");
  const retryBtn = document.getElementById("retry-btn");
  const idea = document.getElementById("idea");
  const ideaCount = document.getElementById("idea-count");

  const LIMITS = {
    team_size: { min: 1, max: 20, integer: true, msg: "Team size must be a whole number from 1 to 20." },
    weekly_hours: { min: 1, max: 80, msg: "Weekly hours must be between 1 and 80." },
    hourly_rate: { min: 0, max: 10000000, msg: "Hourly rate must be 0 or more." },
    contingency_percent: { min: 0, max: 50, msg: "Contingency must be between 0 and 50%." },
  };
  const IDEA_MIN = 20;
  const IDEA_MAX = Number(idea.getAttribute("maxlength")) || 3000;

  let busy = false;
  let lastDemo = false;

  idea.addEventListener("input", function () { ideaCount.textContent = idea.value.length; });

  function setFieldError(field, msg) {
    const box = form.querySelector('.field-error[data-for="' + field + '"]');
    const input = document.getElementById(field);
    if (box) box.textContent = msg || "";
    if (input) input.classList.toggle("invalid", !!msg);
  }

  function clearErrors() {
    form.querySelectorAll(".field-error").forEach(function (b) { b.textContent = ""; });
    form.querySelectorAll(".invalid").forEach(function (i) { i.classList.remove("invalid"); });
    errorBox.classList.add("hidden");
    retryBtn.classList.add("hidden");
  }

  function showError(msg, retryable) {
    errorText.textContent = msg;
    errorBox.classList.remove("hidden");
    retryBtn.classList.toggle("hidden", !retryable);
  }

  function collect() {
    const v = function (id) { return document.getElementById(id).value; };
    return {
      title: v("title").trim(),
      idea: v("idea").trim(),
      platform: v("platform"),
      team_size: v("team_size") === "" ? NaN : Number(v("team_size")),
      weekly_hours: v("weekly_hours") === "" ? NaN : Number(v("weekly_hours")),
      hourly_rate: v("hourly_rate") === "" ? NaN : Number(v("hourly_rate")),
      currency: v("currency"),
      contingency_percent: v("contingency_percent") === "" ? NaN : Number(v("contingency_percent")),
    };
  }

  function validate(data) {
    let ok = true;
    if (data.idea.length < IDEA_MIN) { setFieldError("idea", "Please describe your idea in at least " + IDEA_MIN + " characters."); ok = false; }
    else if (data.idea.length > IDEA_MAX) { setFieldError("idea", "Description must be at most " + IDEA_MAX + " characters."); ok = false; }
    Object.keys(LIMITS).forEach(function (k) {
      const lim = LIMITS[k], n = data[k];
      if (!Number.isFinite(n) || n < lim.min || n > lim.max || (lim.integer && !Number.isInteger(n))) {
        setFieldError(k, lim.msg); ok = false;
      }
    });
    return ok;
  }

  function setLoading(on, demo) {
    busy = on;
    submitBtn.disabled = on;
    if (demoBtn) demoBtn.disabled = on;
    spinner.classList.toggle("hidden", !on);
    label.textContent = on ? (demo ? "Loading sample…" : "Generating plan…") : "Generate Project Plan";
    loadingText.textContent = on && !demo ? "Analysing your idea. This usually takes 10–40 seconds." : "";
  }

  function showLanding() {
    results.classList.add("hidden");
    results.replaceChildren();
    landing.classList.remove("hidden");
    window.scrollTo(0, 0);
    idea.focus();
  }

  async function submit(demo) {
    if (busy) return;
    clearErrors();
    const data = collect();
    if (!validate(data)) { showError("Please fix the highlighted fields.", false); return; }
    lastDemo = demo;
    if (demo) data.demo = true;
    setLoading(true, demo);
    try {
      const res = await fetch("/api/estimate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      let body = null;
      try { body = await res.json(); } catch (e) { body = null; }
      if (!res.ok || !body || !body.ok) {
        if (body && body.fields) Object.keys(body.fields).forEach(function (f) { setFieldError(f, body.fields[f]); });
        let msg = (body && body.error) || "The server returned an unexpected response (" + res.status + ").";
        if (res.status === 503) setBadge(false);
        // 400 = fix input, 503 = configure AI (not retryable); 502/5xx = retryable.
        const retryable = res.status !== 503 && res.status !== 400 &&
          (!!(body && body.retryable) || res.status >= 500 || !body);
        showError(msg, retryable);
        return;
      }
      landing.classList.add("hidden");
      results.classList.remove("hidden");
      const reqData = Object.assign({}, data);
      delete reqData.demo;
      window.PSRender.renderResults(results, body, showLanding, function (btn, status) {
        downloadPdf(btn, status, { request: reqData, plan: body.plan, mode: body.mode });
      });
      window.scrollTo(0, 0);
    } catch (e) {
      showError("Network error: could not reach the server. Check your connection and try again.", true);
    } finally {
      setLoading(false, demo);
    }
  }

  // Ask the server to build a PDF of the shown plan (totals are recalculated server-side).
  let pdfBusy = false;
  async function downloadPdf(btn, status, payload) {
    if (pdfBusy) return;
    pdfBusy = true;
    btn.disabled = true;
    btn.textContent = "Preparing PDF…";
    status.textContent = "";
    try {
      const res = await fetch("/api/report.pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        let msg = "Could not create the PDF (" + res.status + ").";
        try { const b = await res.json(); if (b && b.error) msg = b.error; } catch (e) { /* ignore */ }
        status.textContent = msg + " You can still use Print report.";
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "projectscope-report.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
      status.textContent = "PDF downloaded.";
    } catch (e) {
      status.textContent = "Network error while creating the PDF. Please try again.";
    } finally {
      pdfBusy = false;
      btn.disabled = false;
      btn.textContent = "Download PDF";
    }
  }

  // Keep the header badge in sync with the server's AI configuration.
  const badge = document.getElementById("ai-badge");
  function setBadge(ready) {
    if (!badge) return;
    badge.textContent = ready ? "Live AI ready" : "AI mode: API key needed";
    badge.classList.toggle("badge-ok", ready);
    badge.classList.toggle("badge-warn", !ready);
  }
  fetch("/api/health").then(function (r) { return r.ok ? r.json() : null; })
    .then(function (h) { if (h && typeof h.ai_configured === "boolean") setBadge(h.ai_configured); })
    .catch(function () { /* badge keeps its server-rendered state */ });

  form.addEventListener("submit", function (e) { e.preventDefault(); submit(false); });
  if (demoBtn) demoBtn.addEventListener("click", function () { submit(true); });
  retryBtn.addEventListener("click", function () { submit(lastDemo); });
})();
