/* Results dashboard rendering. All AI text is inserted with textContent, never innerHTML. */
(function () {
  "use strict";

  // Create an element with safe text content and optional class.
  function el(tag, opts, children) {
    const node = document.createElement(tag);
    opts = opts || {};
    if (opts.cls) node.className = opts.cls;
    if (opts.text !== undefined && opts.text !== null) node.textContent = String(opts.text);
    (children || []).forEach(function (c) { if (c) node.appendChild(c); });
    return node;
  }

  function fmtNum(n, digits) {
    return Number(n).toLocaleString(undefined, { maximumFractionDigits: digits === undefined ? 2 : digits });
  }
  function money(n, cur) { return cur + " " + fmtNum(n, 2); }
  function cap(s) { s = String(s || ""); return s.charAt(0).toUpperCase() + s.slice(1); }

  function badge(level, label) {
    const cls = ["high", "medium", "low"].indexOf(level) >= 0 ? "badge badge-" + level : "badge badge-neutral";
    return el("span", { cls: cls, text: label || cap(level) });
  }

  function list(items) {
    const ul = el("ul", { cls: "list" });
    (items || []).forEach(function (t) { ul.appendChild(el("li", { text: t })); });
    return ul;
  }

  function card(title, extraCls) {
    const c = el("section", { cls: "card" + (extraCls ? " " + extraCls : "") });
    c.appendChild(el("h2", { text: title }));
    return c;
  }

  function overviewCard(plan) {
    const c = card("Project Overview", "span-2");
    c.appendChild(el("p", { text: plan.project_summary }));
    c.appendChild(el("div", { cls: "subhead", text: "Problem statement" }));
    c.appendChild(el("p", { text: plan.problem_statement }));
    [["Target users", plan.target_users], ["Objectives", plan.objectives],
     ["Requirements", plan.requirements], ["Assumptions", plan.assumptions],
     ["Missing information that may change the estimate", plan.missing_information]
    ].forEach(function (pair) {
      if (pair[1] && pair[1].length) {
        c.appendChild(el("div", { cls: "subhead", text: pair[0] }));
        c.appendChild(list(pair[1]));
      }
    });
    return c;
  }

  function featureItem(f) {
    const meta = el("span", { cls: "item-meta" }, [badge(f.priority, cap(f.priority) + " priority")]);
    if (f.hours !== null && f.hours !== undefined) meta.appendChild(el("span", { text: "~" + fmtNum(f.hours) + " h" }));
    return el("div", { cls: "item" }, [
      el("div", { cls: "item-head" }, [el("span", { cls: "item-title", text: f.name }), meta]),
      f.description ? el("p", { text: f.description }) : null,
    ]);
  }

  function featuresCard(plan) {
    const c = card("Feature Breakdown");
    const mvp = plan.features.filter(function (f) { return f.category === "mvp"; });
    const future = plan.features.filter(function (f) { return f.category !== "mvp"; });
    c.appendChild(el("div", { cls: "subhead", text: "MVP features" }));
    if (!mvp.length) c.appendChild(el("p", { cls: "muted", text: "None listed." }));
    mvp.forEach(function (f) { c.appendChild(featureItem(f)); });
    c.appendChild(el("div", { cls: "subhead", text: "Future / advanced features" }));
    if (!future.length) c.appendChild(el("p", { cls: "muted", text: "None listed." }));
    future.forEach(function (f) { c.appendChild(featureItem(f)); });
    c.appendChild(el("p", { cls: "hint", text: "Feature hours are indicative only. Totals come from the task breakdown." }));
    return c;
  }

  function stackCard(plan) {
    const c = card("Recommended Tech Stack");
    plan.technology_stack.forEach(function (t) {
      c.appendChild(el("div", { cls: "item" }, [
        el("div", { cls: "item-head" }, [el("span", { cls: "item-title", text: t.name }), el("span", { cls: "badge badge-neutral", text: t.category })]),
        t.reason ? el("p", { text: t.reason }) : null,
      ]));
    });
    return c;
  }

  function stat(label, value, cls) {
    return el("div", { cls: "stat" + (cls ? " " + cls : "") }, [el("span", { cls: "k", text: value }), el("span", { cls: "l", text: label })]);
  }

  function estimateCard(plan, est) {
    const c = card("Estimation Summary (approximate)", "span-2");
    const cur = est.currency;
    c.appendChild(el("div", { cls: "stats" }, [
      stat("Total development hours", fmtNum(est.total_hours) + " h"),
      stat("Estimated duration (" + fmtNum(est.duration_weeks_exact) + " weeks exact)", est.duration_weeks + " week" + (est.duration_weeks === 1 ? "" : "s")),
      stat("Hourly rate", money(est.hourly_rate, cur)),
      stat("Base development cost", money(est.base_cost, cur)),
      stat("Contingency (" + fmtNum(est.contingency_percent) + "%)", money(est.contingency_amount, cur)),
      stat("Estimated total budget", money(est.total_budget, cur), "total"),
    ]));
    const conf = el("p", {}, [el("strong", { text: "Confidence: " }), badge(plan.confidence === "high" ? "low" : plan.confidence === "low" ? "high" : "medium", cap(plan.confidence))]);
    c.appendChild(conf);
    c.appendChild(el("p", { cls: "hint", text: "Confidence reflects how clear the requirements are. It is not a statistical probability of accuracy." }));
    c.appendChild(el("p", { cls: "hint", text: "Team: " + est.team_size + " developer(s) × " + fmtNum(est.weekly_hours) + " h/week. " + est.duration_caveat }));
    c.appendChild(el("p", { cls: "hint", text: est.budget_note }));

    const table = el("table");
    const thead = el("thead", {}, [el("tr", {}, [el("th", { text: "Task" }), el("th", { cls: "num", text: "Hours" })])]);
    const tbody = el("tbody");
    plan.task_estimates.forEach(function (t) {
      const name = el("td", {}, [el("div", { cls: "item-title", text: t.name }), t.description ? el("div", { cls: "hint", text: t.description }) : null]);
      tbody.appendChild(el("tr", {}, [name, el("td", { cls: "num", text: fmtNum(t.hours) })]));
    });
    tbody.appendChild(el("tr", {}, [el("td", {}, [el("strong", { text: "Total" })]), el("td", { cls: "num" }, [el("strong", { text: fmtNum(est.total_hours) })])]));
    table.appendChild(thead); table.appendChild(tbody);
    c.appendChild(el("div", { cls: "subhead", text: "Task estimates" }));
    c.appendChild(table);
    return c;
  }

  function roadmapCard(plan) {
    const c = card("Development Roadmap");
    plan.roadmap.forEach(function (r) {
      const head = el("div", { cls: "item-head" }, [
        el("span", { cls: "item-title" }, [el("span", { cls: "step-num", text: r.sequence }), document.createTextNode(r.title)]),
        badge(r.priority, cap(r.priority) + " priority"),
      ]);
      const item = el("div", { cls: "item" }, [head, r.description ? el("p", { text: r.description }) : null]);
      if (r.dependencies && r.dependencies.length) item.appendChild(el("p", { text: "Depends on: " + r.dependencies.join(", ") }));
      c.appendChild(item);
    });
    return c;
  }

  function risksCard(plan) {
    const c = card("Risk Analysis");
    plan.risks.forEach(function (r) {
      c.appendChild(el("div", { cls: "item" }, [
        el("div", { cls: "item-head" }, [el("span", { cls: "item-title", text: r.description }), badge(r.severity, cap(r.severity) + " severity")]),
        r.mitigation ? el("p", { text: "Mitigation: " + r.mitigation }) : null,
      ]));
    });
    return c;
  }

  function actionsCard(onNew, onPdf) {
    const c = card("Actions", "span-2 no-print");
    const again = el("button", { cls: "btn btn-primary", text: "Generate another estimate" });
    again.type = "button"; again.addEventListener("click", onNew);
    const print = el("button", { cls: "btn btn-secondary", text: "Print report" });
    print.type = "button"; print.addEventListener("click", function () { window.print(); });
    const row = el("div", { cls: "actions" }, [again, print]);
    const status = el("p", { cls: "hint", text: "" });
    status.setAttribute("aria-live", "polite");
    if (onPdf) {
      const pdf = el("button", { cls: "btn btn-secondary", text: "Download PDF" });
      pdf.type = "button";
      pdf.addEventListener("click", function () { onPdf(pdf, status); });
      row.appendChild(pdf);
    }
    c.appendChild(row);
    c.appendChild(status);
    return c;
  }

  function renderResults(container, data, onNew, onPdf) {
    const plan = data.plan, est = data.estimates;
    container.replaceChildren();
    if (data.mode === "demo") {
      container.appendChild(el("div", { cls: "notice notice-warn", text: "DEMO MODE: this is a fixed sample plan, not AI-generated output, and it does not reflect your idea. Your form values (team, rate, currency, contingency) are still applied to the Python calculations. Add AI_API_KEY to enable live AI plans." }));
    }
    const titleBlock = el("div", {}, [
      el("h1", { text: plan.user_title || plan.project_title }),
      el("p", { cls: "muted", text: plan.project_category + (data.mode === "demo" ? " · Demo sample" : " · AI-generated plan") }),
    ]);
    container.appendChild(el("div", { cls: "results-head" }, [titleBlock, badge("neutral", "Approximate estimate")]));
    container.appendChild(el("div", { cls: "dash" }, [
      overviewCard(plan), estimateCard(plan, est), featuresCard(plan), stackCard(plan),
      roadmapCard(plan), risksCard(plan), actionsCard(onNew, onPdf),
    ]));
  }

  window.PSRender = { renderResults: renderResults, el: el };
})();
