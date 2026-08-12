(function () {
  "use strict";

  function decoratePricingLabels(detail) {
    detail.querySelectorAll("strong").forEach((label) => {
      if (label.textContent !== "即时市场定价") return;
      const text = label.parentElement.textContent;
      label.classList.add("pricing-label");
      if (text.includes("正向")) label.classList.add("pricing-positive");
      else if (text.includes("负向")) label.classList.add("pricing-negative");
      else label.classList.add("pricing-mixed");
    });
  }

  function enhanceRow(row) {
    const rank = row.dataset.rank;
    const instanceId = row.dataset.instanceId;
    const heading = row.querySelector("h2");
    const paragraphs = Array.from(row.querySelectorAll(":scope > p"));
    const summary = paragraphs.shift();
    const scoreLine = paragraphs.shift();
    const associations = row.querySelector(":scope > .news-associations");
    const sources = row.querySelector(":scope > [data-component='sources']");
    const content = document.createElement("div");
    const rankCell = document.createElement("div");
    const scoreCell = document.createElement("div");
    const detail = document.createElement("div");
    const toggleTemplate = document.querySelector("#news-toggle-template");
    const inlineSources = row.dataset.detailKind === "sources-inline";

    row.classList.add("news-row");
    content.className = "news-content";
    rankCell.className = "news-rank";
    rankCell.textContent = rank.padStart(2, "0");
    scoreCell.className = "news-score";
    detail.className = "news-detail";
    detail.id = `news-detail-${instanceId}`;
    detail.hidden = true;

    heading.textContent = heading.textContent.replace(/^\d+\.\s*/, "");
    summary.className = "news-summary";
    const score = scoreLine.textContent.match(/(\d+)\/100/);
    scoreCell.innerHTML = `<span>热度 ${score ? score[1] : "—"}</span>`;
    content.append(heading, summary);
    if (associations) {
      const associationIndex = paragraphs.indexOf(associations);
      if (associationIndex >= 0) paragraphs.splice(associationIndex, 1);
      content.appendChild(associations);
    }
    if (inlineSources) {
      if (sources) {
        sources.classList.add("news-inline-sources");
        content.appendChild(sources);
      }
    } else {
      const toggle = toggleTemplate.content.firstElementChild.cloneNode(true);
      toggle.setAttribute("aria-controls", detail.id);
      if (sources) detail.appendChild(sources);
      paragraphs.forEach((paragraph) => detail.appendChild(paragraph));
      decoratePricingLabels(detail);
      content.append(toggle, detail);
    }
    row.replaceChildren(rankCell, content, scoreCell);
  }

  function populateReportSelect() {
    const select = document.querySelector(".mobile-report-select");
    document.querySelectorAll("[data-component='report-archive'] a[data-report-link]").forEach((link) => {
      const option = document.createElement("option");
      option.value = link.getAttribute("href");
      option.textContent = link.dataset.reportLabel;
      option.selected = link.getAttribute("aria-current") === "page";
      select.appendChild(option);
    });
  }

  function applyArchiveState() {
    const hashMatch = /^#archive-(\d{4}-\d{2}-\d{2})$/.exec(window.location.hash);
    const expandedDate = hashMatch ? hashMatch[1] : null;

    document.querySelectorAll(".archive-date-group[data-report-date]").forEach((group) => {
      const dateLink = group.querySelector(".archive-date-link[aria-controls]");
      const slots = document.getElementById(dateLink?.getAttribute("aria-controls"));
      const expanded = group.dataset.reportDate === expandedDate;

      if (slots) slots.hidden = !expanded;
      if (dateLink) dateLink.setAttribute("aria-expanded", String(expanded));
    });
  }

  function applyCategoryFilter(category) {
    document.querySelectorAll(".news-row").forEach((row) => {
      row.hidden = category !== "all" && row.dataset.category !== category;
    });
    document.querySelectorAll(".filter-button").forEach((button) => {
      const active = button.dataset.category === category;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  document.querySelectorAll("[data-component='news-detail']").forEach(enhanceRow);
  populateReportSelect();
  applyArchiveState();
  window.addEventListener("hashchange", applyArchiveState);

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest(".news-toggle");
    if (toggle) {
      const detail = document.getElementById(toggle.getAttribute("aria-controls"));
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      toggle.textContent = expanded ? "展开详情" : "收起详情";
      detail.hidden = expanded;
      return;
    }
    const filter = event.target.closest(".filter-button");
    if (filter) applyCategoryFilter(filter.dataset.category);
  });

  document.querySelector(".mobile-report-select")?.addEventListener("change", (event) => {
    window.location.assign(event.target.value);
  });
}());
