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
    const heading = row.querySelector("h2");
    const paragraphs = Array.from(row.querySelectorAll(":scope > p"));
    const summary = paragraphs.shift();
    const scoreLine = paragraphs.shift();
    const sources = row.querySelector(":scope > [data-component='sources']");
    const content = document.createElement("div");
    const rankCell = document.createElement("div");
    const scoreCell = document.createElement("div");
    const detail = document.createElement("div");
    const toggleTemplate = document.querySelector("#news-toggle-template");
    const toggle = toggleTemplate.content.firstElementChild.cloneNode(true);
    const inlineSources = row.dataset.detailKind === "sources-inline";

    row.classList.add("news-row");
    content.className = "news-content";
    rankCell.className = "news-rank";
    rankCell.textContent = rank.padStart(2, "0");
    scoreCell.className = "news-score";
    detail.className = "news-detail";
    detail.id = `news-detail-${rank}`;
    detail.hidden = true;
    toggle.setAttribute("aria-controls", detail.id);

    heading.textContent = heading.textContent.replace(/^\d+\.\s*/, "");
    summary.className = "news-summary";
    const score = scoreLine.textContent.match(/(\d+)\/100/);
    scoreCell.innerHTML = `<strong>${score ? score[1] : "—"}</strong><span>热点权重</span>`;
    content.append(heading, summary);
    if (inlineSources) {
      if (sources) {
        sources.classList.add("news-inline-sources");
        content.appendChild(sources);
      }
    } else {
      if (sources) detail.appendChild(sources);
      paragraphs.forEach((paragraph) => detail.appendChild(paragraph));
      decoratePricingLabels(detail);
      content.append(toggle, detail);
    }
    row.replaceChildren(rankCell, content, scoreCell);
  }

  function populateReportSelect() {
    const select = document.querySelector(".mobile-report-select");
    document.querySelectorAll("[data-component='report-archive'] a").forEach((link) => {
      const option = document.createElement("option");
      option.value = link.getAttribute("href");
      option.textContent = link.textContent;
      option.selected = link.getAttribute("aria-current") === "page";
      select.appendChild(option);
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
