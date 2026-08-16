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
    if (!select) return;
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

  function applyThemeNavigationCurrent(hash = window.location.hash) {
    const links = Array.from(document.querySelectorAll(".theme-navigation a[href^='#']"));
    const current = links.find((link) => link.getAttribute("href") === hash)
      ?? links[0];

    links.forEach((link) => {
      if (link === current) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
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

  function buildRankedList() {
    const container = document.querySelector("[data-component='ranked-list']");
    if (!container || container.dataset.built) return;
    const entries = [];
    document.querySelectorAll(".theme-group").forEach((group) => {
      const themeName = group.querySelector(".theme-heading-line h2")?.textContent.trim() ?? "";
      group.querySelectorAll(".news-row").forEach((row) => {
        entries.push({ row, themeName });
      });
    });
    document.querySelectorAll(".other-important-news .news-row").forEach((row) => {
      entries.push({ row, themeName: "其他" });
    });
    const scoreOf = (row) => {
      const match = row.querySelector(".news-score")?.textContent.match(/(\d+)/);
      return match ? Number(match[1]) : 0;
    };
    entries.sort((a, b) => scoreOf(b.row) - scoreOf(a.row));
    entries.forEach((entry, index) => {
      const row = entry.row;
      const title = row.querySelector(".news-content h2")?.textContent.trim() ?? "";
      const item = document.createElement("article");
      item.className = "ranked-item";
      item.dataset.eventId = row.dataset.eventId ?? "";
      const rank = document.createElement("span");
      rank.className = "ranked-rank";
      rank.textContent = String(index + 1).padStart(2, "0");
      const heading = document.createElement("h3");
      heading.textContent = title;
      const tag = document.createElement("span");
      tag.className = "ranked-theme";
      tag.textContent = entry.themeName;
      const score = document.createElement("span");
      score.className = "ranked-score";
      score.textContent = scoreOf(row);
      item.append(rank, heading, tag, score);
      container.appendChild(item);
    });
    container.dataset.built = "true";
  }

  function selectNewsMode(mode) {
    document.querySelectorAll(".news-mode-button").forEach((button) => {
      const active = button.dataset.newsMode === mode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    const themedView = document.querySelector("[data-component='themed-view']");
    const rankedList = document.querySelector("[data-component='ranked-list']");
    if (themedView) themedView.hidden = mode !== "themed";
    if (rankedList) rankedList.hidden = mode !== "ranked";
  }

  function selectNewsModeForHash() {
    if (!document.querySelector("[data-component='news-mode-switch']")) return;
    if (/^#theme-/.test(window.location.hash)) selectNewsMode("themed");
  }

  var paneButtons = document.querySelectorAll(".report-tab-button");
  var panes = document.querySelectorAll(".fusion-pane");
  function selectPane(target) {
    paneButtons.forEach(function (btn) {
      btn.setAttribute("aria-selected", String(btn.dataset.paneTarget === target));
    });
    panes.forEach(function (pane) {
      pane.hidden = pane.dataset.pane !== target;
    });
  }
  paneButtons.forEach(function (btn) {
    btn.addEventListener("click", function () { selectPane(btn.dataset.paneTarget); });
  });
  var initialHash = (window.location.hash || "").replace("#", "");
  if (initialHash === "brief" || initialHash === "news") selectPane(initialHash);
  window.addEventListener("hashchange", function () {
    var target = (window.location.hash || "").replace("#", "");
    if (target === "brief" || target === "news") selectPane(target);
  });

  document.querySelectorAll("[data-component='news-detail']").forEach(enhanceRow);
  populateReportSelect();
  applyArchiveState();
  applyThemeNavigationCurrent();
  buildRankedList();
  selectNewsModeForHash();
  window.addEventListener("hashchange", applyArchiveState);
  window.addEventListener("hashchange", () => applyThemeNavigationCurrent());
  window.addEventListener("hashchange", selectNewsModeForHash);

  document.querySelectorAll(".news-mode-button").forEach((button) => {
    button.addEventListener("click", () => selectNewsMode(button.dataset.newsMode));
  });
  document.querySelector("[data-component='ranked-list']")?.addEventListener("click", (event) => {
    const item = event.target.closest(".ranked-item");
    if (!item) return;
    selectNewsMode("themed");
    const target = document.querySelector(`.news-row[data-event-id="${item.dataset.eventId}"]`);
    if (target) {
      target.scrollIntoView({ block: "center" });
      target.classList.add("ranked-target-flash");
      setTimeout(() => target.classList.remove("ranked-target-flash"), 1200);
    }
  });

  const closedPendingDetailsForPrint = new Set();
  window.addEventListener("beforeprint", () => {
    document.querySelectorAll(".pending-details").forEach((details) => {
      if (details.open) return;
      closedPendingDetailsForPrint.add(details);
      details.open = true;
    });
  });
  window.addEventListener("afterprint", () => {
    closedPendingDetailsForPrint.forEach((details) => {
      details.open = false;
    });
    closedPendingDetailsForPrint.clear();
  });

  document.addEventListener("click", (event) => {
    const themeLink = event.target.closest(".theme-navigation a[href^='#']");
    if (
      themeLink
      && !event.defaultPrevented
      && event.button === 0
      && !event.ctrlKey
      && !event.metaKey
      && !event.shiftKey
      && !event.altKey
    ) {
      const themedView = document.querySelector("[data-component='themed-view']");
      if (themedView && themedView.hidden) selectNewsMode("themed");
      applyThemeNavigationCurrent(themeLink.getAttribute("href"));
    }

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
