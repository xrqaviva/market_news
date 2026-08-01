(function () {
  "use strict";

  const categoryRules = [
    ["政策", ["政策", "政治局", "央行", "利率", "监管", "国务院", "部委", "规划"]],
    ["财报", ["财报", "业绩", "营收", "收入", "利润", "eps", "季度"]],
    ["产业", ["芯片", "半导体", "人工智能", "ai", "储能", "能源", "汽车", "机器人", "订单"]],
    ["地缘", ["伊朗", "美国", "中东", "航运", "战争", "关税", "出口", "制裁"]]
  ];

  function categoryFor(row) {
    const text = row.textContent.toLowerCase();
    const match = categoryRules.find((rule) =>
      rule[1].some((keyword) => text.includes(keyword.toLowerCase()))
    );
    return match ? match[0] : "其他";
  }

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

    row.classList.add("news-row");
    row.dataset.category = categoryFor(row);
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
    paragraphs.forEach((paragraph) => detail.appendChild(paragraph));
    if (sources) detail.appendChild(sources);
    decoratePricingLabels(detail);

    content.append(heading, summary, toggle, detail);
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
