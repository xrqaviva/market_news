/* Browser layout acceptance for the current report design (2026-08):

 * - themed reports render a theme-navigation + theme-group list inside the
 *   "news" pane; app.js converts each news-detail article into a .news-row
 *   (rank / content / score) at runtime.
 * - non-themed reports render a filter-bar with category buttons instead.
 * - the sidebar is sticky (position: sticky; top: 13px) with its own
 *   overflow-y and a pinned "回到最上" link at the bottom.
 * - anchor jumps use CSS scroll-behavior: smooth, so assertions must wait
 *   for the scroll to settle instead of reading one frame after the click.
 *
 * Run with: node tests/report_layout_browser.mjs
 */
import { access, mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { execFile, spawn } from "node:child_process";
import { promisify } from "node:util";

const ROOT = resolve(dirname(new URL(import.meta.url).pathname), "..");
const execFileAsync = promisify(execFile);
const EXPECTED_REPORT_OUTPUT_BY_INPUT = new Map([
  ["reports/2026-07-29-pure-news-hot-ranking-v4.md", "reports/2026-07-29-1800.html"],
  ["reports/2026-07-30-1500-next-trading-day-news-baseline.md", "reports/2026-07-30-1500.html"],
  ["reports/2026-07-30-premarket-news-ranking-v6-depth-test.md", "reports/2026-07-30-0800.html"],
  ["reports/2026-07-31-0800-premarket-news-ranking.md", "reports/2026-07-31-0800.html"],
  ["reports/2026-08-03-0800-premarket-news-ranking.md", "reports/2026-08-03-0800.html"],
  ["reports/2026-08-10-0800-premarket-news-ranking.md", "reports/2026-08-10-0800.html"],
  ["reports/2026-08-11-0800-premarket-news-ranking.md", "reports/2026-08-11-0800.html"],
  ["reports/2026-08-13-1500-news-ranking-test.md", "reports/2026-08-13-1500.html"],
  ["reports/2026-08-14-0800-news-ranking-preview.md", "reports/2026-08-14-0800.html"],
  ["reports/2026-08-16-0800-news-ranking-preview.md", "reports/2026-08-16-0800.html"],
  ["reports/2026-08-17-0800-news-ranking-preview.md", "reports/2026-08-17-0800.html"],
  ["reports/2026-08-18-0800-news-ranking-preview.md", "reports/2026-08-18-0800.html"],
  ["reports/2026-08-19-0800-news-ranking-preview.md", "reports/2026-08-19-0800.html"],
]);

function assertSameStringSet(label, actual, expected) {
  const actualSorted = [...actual].sort();
  const expectedSorted = [...expected].sort();
  if (JSON.stringify(actualSorted) !== JSON.stringify(expectedSorted)) {
    throw new Error(
      `${label} mismatch: ${JSON.stringify({ actual: actualSorted, expected: expectedSorted })}`,
    );
  }
}

async function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      await access(candidate, fsConstants.X_OK);
      return candidate;
    } catch {
      // Try the next supported Chrome/Chromium location.
    }
  }
  throw new Error("Chrome/Chromium not found; set CHROME_PATH to run layout checks");
}

async function poll(read, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const value = await read();
    if (value !== undefined) return value;
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 50));
  }
  throw new Error(`timed out after ${timeoutMs}ms`);
}

async function connectCdp(url) {
  const socket = new WebSocket(url);
  const pending = new Map();
  const listeners = new Map();
  let sequence = 0;

  socket.addEventListener("message", ({ data }) => {
    const message = JSON.parse(data);
    if (message.id) {
      const request = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) request.reject(new Error(message.error.message));
      else request.resolve(message.result);
      return;
    }
    for (const listener of listeners.get(message.method) ?? []) listener(message.params);
  });

  await new Promise((resolvePromise, reject) => {
    socket.addEventListener("open", resolvePromise, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });

  return {
    close: () => socket.close(),
    on(method, listener) {
      const methodListeners = listeners.get(method) ?? [];
      methodListeners.push(listener);
      listeners.set(method, methodListeners);
    },
    send(method, params = {}) {
      sequence += 1;
      return new Promise((resolvePromise, reject) => {
        pending.set(sequence, { resolve: resolvePromise, reject });
        socket.send(JSON.stringify({ id: sequence, method, params }));
      });
    },
  };
}

async function evaluate(cdp, expression) {
  const label = expression.replace(/\s+/g, " ").slice(0, 60);
  let result;
  try {
    result = await cdp.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });
  } catch (error) {
    throw new Error(`evaluate "${label}": ${error.message}`);
  }
  if (result.exceptionDetails) {
    throw new Error(`${label}: ${result.exceptionDetails.exception?.description ?? "browser evaluation failed"}`);
  }
  return result.result.value;
}

async function navigate(cdp, url) {
  await cdp.send("Page.navigate", { url });
  await poll(async () => {
    const state = await evaluate(cdp, "document.readyState");
    return state === "complete" ? true : undefined;
  });
}

const scratch = await mkdtemp(join(tmpdir(), "news-radar-layout-"));
const freshDist = join(scratch, "dist");
const themedReport = join(freshDist, "reports/2026-08-11-0800.html");
const plainReport = join(freshDist, "reports/2026-08-10-0800.html");
const longReport = join(freshDist, "reports/2026-08-16-0800.html");
const profile = join(scratch, "chrome-profile");
let chrome;
let cdp;

try {
  const { stdout: gitRootOutput } = await execFileAsync(
    "git",
    ["rev-parse", "--show-toplevel"],
    { cwd: ROOT },
  );
  const gitRoot = resolve(gitRootOutput.trim());
  if (gitRoot !== ROOT) {
    throw new Error(`browser build root is not the isolated worktree: ${gitRoot}`);
  }

  const [{ stdout: gitDirOutput }, { stdout: gitCommonDirOutput }, { stdout: superprojectOutput }] =
    await Promise.all([
      execFileAsync("git", ["rev-parse", "--git-dir"], { cwd: ROOT }),
      execFileAsync("git", ["rev-parse", "--git-common-dir"], { cwd: ROOT }),
      execFileAsync("git", ["rev-parse", "--show-superproject-working-tree"], { cwd: ROOT }),
    ]);
  const gitDir = resolve(gitRoot, gitDirOutput.trim());
  const gitCommonDir = resolve(gitRoot, gitCommonDirOutput.trim());
  if (superprojectOutput.trim()) {
    throw new Error(`browser build root must not be a submodule: ${JSON.stringify({
      gitDir,
      gitCommonDir,
      superproject: superprojectOutput.trim(),
    })}`);
  }

  const { stdout: trackedReportOutput } = await execFileAsync(
    "git",
    ["ls-files", "reports/*.md"],
    { cwd: ROOT },
  );
  const trackedReports = new Set(trackedReportOutput.trim().split("\n").filter(Boolean));
  // Main-branch reality: reports/ also tracks historical reference files that the
  // catalog deliberately does not build. The browser guard therefore verifies that
  // every build input is tracked in git, not that tracked == build inputs.
  const buildInputs = [...EXPECTED_REPORT_OUTPUT_BY_INPUT.keys()];
  if (buildInputs.length !== 13) {
    throw new Error(
      `fresh browser build must consume exactly 12 tracked report Markdown files, got ${buildInputs.length}`,
    );
  }
  for (const relativePath of buildInputs) {
    if (!trackedReports.has(relativePath)) {
      throw new Error(`fresh browser build input is not tracked in git: ${relativePath}`);
    }
  }
  await Promise.all(buildInputs.map((relativePath) => access(join(gitRoot, relativePath))));

  const explicitLegacyReports = new Set(
    [...EXPECTED_REPORT_OUTPUT_BY_INPUT.keys()].filter(
      (relativePath) => !/^reports\/\d{4}-\d{2}-\d{2}-\d{4}-.+\.md$/.test(relativePath),
    ),
  );
  const diskReports = (await readdir(join(gitRoot, "reports")))
    .map((name) => `reports/${name}`)
    .filter(
      (relativePath) => /^reports\/\d{4}-\d{2}-\d{2}-\d{4}-.+\.md$/.test(relativePath)
        || explicitLegacyReports.has(relativePath),
    );
  assertSameStringSet("on-disk standard report inputs", diskReports, buildInputs);
  let untrackedMutationRejected = false;
  try {
    assertSameStringSet(
      "controlled untracked standard report mutation",
      [...diskReports, "reports/2099-12-31-untracked-mutation.md"],
      buildInputs,
    );
  } catch {
    untrackedMutationRejected = true;
  }
  if (!untrackedMutationRejected) {
    throw new Error("report input guard accepted a controlled untracked standard report mutation");
  }

  await execFileAsync("python3", [
    "-m",
    "web.build",
    "--project-root",
    gitRoot,
    "--output",
    freshDist,
  ], { cwd: gitRoot });

  const manifest = JSON.parse(await readFile(join(freshDist, "reports.json"), "utf8"));
  const manifestReports = manifest.reports.map((entry) => entry.url);
  const builtReportPages = (await readdir(join(freshDist, "reports")))
    .filter((name) => name.endsWith(".html"))
    .map((name) => `reports/${name}`);
  const expectedReportPages = [...EXPECTED_REPORT_OUTPUT_BY_INPUT.values()];
  assertSameStringSet("fresh manifest report outputs", manifestReports, expectedReportPages);
  assertSameStringSet("fresh HTML report outputs", builtReportPages, expectedReportPages);

  const chromePath = await findChrome();
  chrome = spawn(chromePath, [
    "--headless=new",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-sync",
    "--metrics-recording-only",
    "--no-default-browser-check",
    "--no-first-run",
    "--remote-debugging-port=0",
    `--user-data-dir=${profile}`,
    "about:blank",
  ], { stdio: "ignore" });

  const port = await poll(async () => {
    try {
      return (await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0];
    } catch {
      if (chrome.exitCode !== null) throw new Error(`Chrome exited with ${chrome.exitCode}`);
      return undefined;
    }
  });
  const target = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {
    method: "PUT",
  }).then((response) => response.json());
  cdp = await connectCdp(target.webSocketDebuggerUrl);
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Log.enable");

  const browserProblems = [];
  cdp.on("Runtime.exceptionThrown", ({ exceptionDetails }) => {
    browserProblems.push(exceptionDetails.exception?.description ?? "uncaught exception");
  });
  cdp.on("Runtime.consoleAPICalled", ({ type, args }) => {
    if (["error", "warning"].includes(type)) {
      browserProblems.push(`${type}: ${args.map((arg) => arg.value ?? arg.description).join(" ")}`);
    }
  });
  cdp.on("Log.entryAdded", ({ entry }) => {
    if (["error", "warning"].includes(entry.level)) browserProblems.push(entry.text);
  });

  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await cdp.send("Emulation.setEmulatedMedia", { media: "screen" });
  await navigate(cdp, pathToFileURL(themedReport).href);

  // Desktop: themed report, measured with the "news" pane visible.
  const desktop = await evaluate(cdp, `(async () => {
    const metric = (element) => {
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return {
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        left: rect.left,
        width: rect.width,
        height: rect.height,
        display: style.display,
        position: style.position,
        maxWidth: style.maxWidth,
        paddingTop: style.paddingTop,
        paddingRight: style.paddingRight,
        paddingBottom: style.paddingBottom,
        paddingLeft: style.paddingLeft,
        marginLeft: style.marginLeft,
        borderRadius: style.borderRadius,
        overflowY: style.overflowY,
        topPos: style.top,
        borderTopWidth: style.borderTopWidth,
        borderTopColor: style.borderTopColor,
        borderTopStyle: style.borderTopStyle,
        backgroundColor: style.backgroundColor,
        boxShadow: style.boxShadow,
        color: style.color,
        columnGap: style.columnGap,
        gridTemplateColumns: style.gridTemplateColumns,
        alignItems: style.alignItems,
        fontSize: style.fontSize,
        fontWeight: style.fontWeight,
        fontFamily: style.fontFamily,
      };
    };
    document.querySelector('.report-tab-button[data-pane-target="news"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));

    const shell = document.querySelector(".page-shell");
    const card = document.querySelector(".report-card");
    const sidebar = document.querySelector(".report-sidebar");
    const sidebarTopLink = document.querySelector(".sidebar-top-link");
    const header = document.querySelector(".topbar");
    const reportMain = document.querySelector(".report-main");
    const reportTitle = document.querySelector(".report-heading h1");
    const navigation = document.querySelector(".theme-navigation");
    const navigationLinks = Array.from(navigation.querySelectorAll("a"));
    const firstTheme = document.querySelector(".theme-group");
    const secondTheme = document.querySelectorAll(".theme-group")[1];
    const themeHeader = firstTheme.querySelector(".theme-header");
    const themeKicker = themeHeader.querySelector(".theme-kicker");
    const themeHeading = firstTheme.querySelector(".theme-heading-line");
    const themeTitle = themeHeading.querySelector("h2");
    const themeTotal = themeHeading.querySelector(".theme-total");
    const newsList = firstTheme.querySelector(".theme-news-list");
    const rows = Array.from(document.querySelectorAll(".news-row"));
    const firstRow = rows[0];
    const newsContent = firstRow.querySelector(".news-content");
    const newsTitle = firstRow.querySelector(".news-content h2");
    const newsSummary = firstRow.querySelector(".news-summary");
    const newsScore = firstRow.querySelector(".news-score");
    const newsRank = firstRow.querySelector(".news-rank");
    const newsToggle = firstRow.querySelector(".news-toggle");
    const firstDetail = firstRow.querySelector(".news-detail");
    const firstSources = firstRow.querySelector("[data-component='sources']");

    // Disclosure lifecycle on the first analysis row.
    async function disclosureProbe() {
      if (!newsToggle) return null;
      const detail = document.getElementById(newsToggle.getAttribute("aria-controls"));
      const state = () => ({
        hidden: detail.hidden,
        ariaExpanded: newsToggle.getAttribute("aria-expanded"),
        label: newsToggle.textContent,
        height: detail.getBoundingClientRect().height,
      });
      const closed = state();
      newsToggle.click();
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const open = state();
      newsToggle.click();
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const closedAgain = state();
      return { closed, open, closedAgain };
    }
    const disclosure = await disclosureProbe();

    const reportNotes = document.querySelector("[data-component='report-notes']");
    const reportNoteSummaryH2 = reportNotes.querySelector("summary h2");
    const reportNoteSections = Array.from(
      reportNotes.querySelectorAll("[data-component='report-note-section']"),
    );
    const reportNoteSectionH3s = reportNoteSections.map(
      (section) => section.querySelector("h3"),
    );
    const reportNoteBodyParts = Array.from(
      reportNotes.querySelectorAll(".report-note-intro p, .report-note-section p, .report-note-section li"),
    );
    const otherImportant = document.querySelector("[data-component='other-important-news']");
    const pendingList = document.querySelector("[data-component='pending-list']");
    const reportNoteLinks = Array.from(reportNotes.querySelectorAll("a"));
    const reportNoteContract = {
      visible: reportNotes.getClientRects().length > 0,
      title: reportNoteSummaryH2.textContent.trim(),
      sectionCount: reportNoteSections.length,
      summaryTitleFontSize: parseFloat(getComputedStyle(reportNoteSummaryH2).fontSize),
      summaryTitleFontWeight: getComputedStyle(reportNoteSummaryH2).fontWeight,
      sectionTitleMaximumFontSize: Math.max(
        ...reportNoteSectionH3s.map((title) => parseFloat(getComputedStyle(title).fontSize)),
      ),
      bodyMaximumFontSize: Math.max(
        ...reportNoteBodyParts.map((part) => parseFloat(getComputedStyle(part).fontSize)),
      ),
      afterOther: otherImportant.getBoundingClientRect().bottom <= reportNotes.getBoundingClientRect().top,
      beforePending: reportNotes.getBoundingClientRect().bottom <= pendingList.getBoundingClientRect().top,
      unsafeHrefCount: reportNoteLinks.filter(
        (link) => !["http:", "https:"].includes(new URL(link.href).protocol),
      ).length,
    };

    const navState = () => ({
      currentCount: navigationLinks.filter(
        (candidate) => candidate.getAttribute("aria-current") === "location",
      ).length,
      currentHref: navigationLinks.find(
        (candidate) => candidate.getAttribute("aria-current") === "location",
      )?.getAttribute("href") ?? null,
    });
    const initialNavigationCurrent = navState();

    const archiveGroup = document.querySelector(".archive-date-group[data-report-date='2026-08-11']");
    const archiveLink = archiveGroup.querySelector(".archive-date-link");
    const archiveSlots = document.getElementById(archiveLink.getAttribute("aria-controls"));

    return {
      shell: metric(shell),
      card: metric(card),
      sidebar: metric(sidebar),
      brand: metric(sidebar.querySelector(".brand")),
      dateLinkFontSize: getComputedStyle(sidebar.querySelector(".archive-date-link")).fontSize,
      sidebarTopLink: metric(sidebarTopLink),
      sidebarTopHref: sidebarTopLink.getAttribute("href"),
      workspace: metric(document.querySelector(".report-workspace")),
      topbar: metric(header),
      reportMain: metric(reportMain),
      reportTitle: metric(reportTitle),
      navigation: metric(navigation),
      navLinkCount: navigationLinks.length,
      navHrefs: navigationLinks.map((candidate) => candidate.getAttribute("href")),
      theme: metric(firstTheme),
      secondTheme: metric(secondTheme),
      themeCount: document.querySelectorAll(".theme-group").length,
      themeHeader: metric(themeHeader),
      themeKicker: metric(themeKicker),
      themeHeading: metric(themeHeading),
      themeTitle: metric(themeTitle),
      themeTotal: metric(themeTotal),
      newsList: metric(newsList),
      rowCount: rows.length,
      detailRowCount: rows.filter((row) => row.dataset.detailKind === "analysis").length,
      firstRow: metric(firstRow),
      newsRank: metric(newsRank),
      newsTitle: metric(newsTitle),
      newsSummary: metric(newsSummary),
      newsScore: metric(newsScore),
      newsToggle: metric(newsToggle),
      newsDetail: metric(firstDetail),
      newsSources: metric(firstSources),
      bodyFont: getComputedStyle(document.body).fontFamily,
      bodyBackground: getComputedStyle(document.body).backgroundColor,
      workspacePaddingLeft: getComputedStyle(reportMain).paddingLeft,
      reportTitleFontSize: getComputedStyle(reportTitle).fontSize,
      themeTitleFontSize: getComputedStyle(themeTitle).fontSize,
      newsTitleFontSize: getComputedStyle(newsTitle).fontSize,
      reportNoteContract,
      disclosure,
      initialNavigationCurrent,
      firstNavigationHref: navigationLinks[0]?.getAttribute("href") ?? null,
      archive: {
        groupCount: document.querySelectorAll(".archive-date-group").length,
        linkHref: archiveLink.getAttribute("href"),
        ariaExpanded: archiveLink.getAttribute("aria-expanded"),
        slotsHidden: archiveSlots.hidden,
      },
    };
  })()`);

  // Expand every row, then verify the common left line across all rows.
  const expandedAlignment = await evaluate(cdp, `(async () => {
    document.querySelector('.report-tab-button[data-pane-target="news"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    document.querySelectorAll(".news-toggle[aria-expanded='false']").forEach(
      (candidate) => candidate.click(),
    );
    await new Promise((resolvePromise) => requestAnimationFrame(() => requestAnimationFrame(resolvePromise)));
    const rows = Array.from(document.querySelectorAll(".news-row"));
    const firstRow = rows[0];
    const newsContent = firstRow.querySelector(".news-content");
    const contentLeft = newsContent.getBoundingClientRect().left;
    const alignedElements = [
      newsContent.querySelector("h2"),
      newsContent.querySelector(".news-summary"),
      newsContent.querySelector(".news-toggle"),
      newsContent.querySelector("[data-component='sources']"),
      newsContent.querySelector(".news-detail"),
    ].filter(Boolean);
    const alignment = {
      contentLeft,
      mismatches: alignedElements
        .filter((element) => Math.abs(element.getBoundingClientRect().left - contentLeft) > 1)
        .map((element) => ({ element: element.className || element.tagName, left: element.getBoundingClientRect().left })),
    };
    const commonLeftLine = { checkedCount: 0, violations: [], coverage: { detailRows: 0, sourceOnlyRows: 0 } };
    rows.forEach((row) => {
      const content = row.querySelector(".news-content");
      const left = content.getBoundingClientRect().left;
      if (row.dataset.detailKind === "analysis") commonLeftLine.coverage.detailRows += 1;
      else commonLeftLine.coverage.sourceOnlyRows += 1;
      const candidates = [
        ...content.querySelectorAll(
          ":scope > h2, :scope > .news-summary, :scope > .news-toggle, :scope > .news-detail",
        ),
        ...content.querySelectorAll(":scope > .news-detail [data-component='sources']"),
        row.querySelector(".news-score"),
      ].filter(Boolean);
      candidates.forEach((element) => {
        commonLeftLine.checkedCount += 1;
        if (Math.abs(element.getBoundingClientRect().left - left) > 1) {
          commonLeftLine.violations.push({
            row: row.id,
            element: element.className || element.tagName,
            contentLeft: left,
            left: element.getBoundingClientRect().left,
          });
        }
      });
    });
    return { alignment, commonLeftLine, expandedRowCount: rows.filter((row) => !row.querySelector(".news-detail").hidden).length };
  })()`);
  Object.assign(desktop, expandedAlignment);

  // News view mode switch: themed (default) vs ranked list. Ranked mode reuses
  // the full news rows (moved, not re-rendered) so no information is lost.
  const rankedMode = await evaluate(cdp, `(async () => {
    document.querySelector('.report-tab-button[data-pane-target="news"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const switchEl = document.querySelector("[data-component='news-mode-switch']");
    const themedView = document.querySelector("[data-component='themed-view']");
    const rankedList = document.querySelector("[data-component='ranked-list']");
    const initial = {
      hasSwitch: !!switchEl,
      buttons: Array.from(document.querySelectorAll(".news-mode-button")).map((button) => ({
        label: button.textContent.trim(),
        mode: button.dataset.newsMode,
        active: button.classList.contains("is-active"),
        pressed: button.getAttribute("aria-pressed"),
      })),
      themedVisible: themedView && !themedView.hidden,
      rankedHidden: rankedList && rankedList.hidden,
      totalRowCount: document.querySelectorAll(".news-row").length,
      firstThemeFirstRank: document.querySelector(".theme-group .news-row .news-rank")?.textContent ?? null,
    };
    document.querySelector('.news-mode-button[data-news-mode="ranked"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const rankedRows = Array.from(rankedList.querySelectorAll(".news-row"));
    const scores = rankedRows.map((row) => Number(row.querySelector(".news-score").textContent.match(/\d+/)?.[0] ?? 0));
    const firstRow = rankedRows[0];
    const afterSwitch = {
      themedHidden: themedView.hidden,
      rankedVisible: !rankedList.hidden,
      activeButton: document.querySelector(".news-mode-button.is-active")?.dataset.newsMode,
      rowCount: rankedRows.length,
      firstRank: firstRow?.querySelector(".news-rank").textContent ?? null,
      firstTitle: firstRow?.querySelector(".news-content h2")?.textContent.trim().slice(0, 30) ?? null,
      firstTag: firstRow?.querySelector(".news-row-theme-tag")?.textContent.trim() ?? null,
      firstSummary: firstRow?.querySelector(".news-summary")?.textContent.trim().slice(0, 30) ?? null,
      firstHasToggle: !!firstRow?.querySelector(".news-toggle"),
      firstHasDetail: !!firstRow?.querySelector(".news-detail"),
      firstHasSources: !!firstRow?.querySelector("[data-component='sources']"),
      tagOnEveryRow: rankedRows.every((row) => (row.querySelector(".news-row-theme-tag")?.textContent.trim().length ?? 0) > 0),
      sortedByScore: scores.every((score, index) => index === 0 || scores[index - 1] >= score),
      navigationHidden: document.querySelector(".theme-navigation").getClientRects().length === 0,
      themedGroupRowCounts: Array.from(document.querySelectorAll(".theme-group"))
        .map((g) => g.querySelectorAll(".news-row").length),
    };
    // toggle detail inside ranked mode: information must still be interactive
    const toggle = firstRow?.querySelector(".news-toggle");
    let detailExpandedInRanked = null;
    if (toggle) {
      const detail = document.getElementById(toggle.getAttribute("aria-controls"));
      const before = detail.hidden;
      toggle.click();
      await new Promise((resolvePromise) => requestAnimationFrame(() => requestAnimationFrame(resolvePromise)));
      detailExpandedInRanked = detail.hidden !== before;
      toggle.click();
      await new Promise((resolvePromise) => requestAnimationFrame(() => requestAnimationFrame(resolvePromise)));
    }
    // switch back: rows must return to their original theme groups with rank restored
    document.querySelector('.news-mode-button[data-news-mode="themed"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const afterJump = {
      themedVisible: !themedView.hidden,
      rankedHidden: rankedList.hidden,
      activeMode: document.querySelector(".news-mode-button.is-active")?.dataset.newsMode,
      restoredRowCount: document.querySelectorAll(".news-row").length,
      themedGroupRowCounts: Array.from(document.querySelectorAll(".theme-group"))
        .map((g) => g.querySelectorAll(".news-row").length),
      firstRowRankRestored: document.querySelector(".theme-group .news-row .news-rank")?.textContent ?? null,
      tagsRemoved: document.querySelectorAll(".news-row-theme-tag").length,
    };
    return { initial, afterSwitch, detailExpandedInRanked, afterJump };
  })()`);

  // Interaction probe: theme-navigation click with smooth-scroll settlement.
  const navClick = await evaluate(cdp, `(async () => {
    document.querySelector('.report-tab-button[data-pane-target="news"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const navigationLinks = Array.from(document.querySelectorAll(".theme-navigation a"));
    const header = document.querySelector(".topbar");
    const navState = () => ({
      currentCount: navigationLinks.filter(
        (candidate) => candidate.getAttribute("aria-current") === "location",
      ).length,
      currentHref: navigationLinks.find(
        (candidate) => candidate.getAttribute("aria-current") === "location",
      )?.getAttribute("href") ?? null,
    });
    const initial = navState();
    scrollTo(0, 0);
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 300));
    const target = document.querySelectorAll(".theme-group")[2];
    const link = navigationLinks.find((candidate) => candidate.getAttribute("href") === ("#" + target.id));
    link.click();
    for (let attempt = 0; attempt < 30; attempt += 1) {
      if (Math.abs(target.getBoundingClientRect().top) <= 1) break;
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 100));
    }
    const clicked = navState();
    const currentLink = navigationLinks.find(
      (candidate) => candidate.getAttribute("aria-current") === "location",
    );
    const inactiveLink = navigationLinks.find((candidate) => candidate !== currentLink);
    const metric = (element) => {
      if (!element) return null;
      const style = getComputedStyle(element);
      return { color: style.color, fontWeight: style.fontWeight };
    };
    return {
      initialNavigationCurrent: initial,
      firstNavigationHref: navigationLinks[0]?.getAttribute("href") ?? null,
      headerPosition: getComputedStyle(header).position,
      scrollMarginTop: parseFloat(getComputedStyle(target).scrollMarginTop),
      targetTop: target.getBoundingClientRect().top,
      anchorHash: location.hash,
      anchorTargetId: target.id,
      clickedNavigationCurrent: clicked,
      currentNavigationLink: metric(currentLink),
      inactiveNavigationLink: metric(inactiveLink),
    };
  })()`);
  Object.assign(desktop, navClick);

  // Direct-hash navigation: app.js must mark the matching theme link current.
  await navigate(cdp, "about:blank");
  await navigate(cdp, `${pathToFileURL(themedReport).href}#${desktop.anchorTargetId}`);
  const directHashNavigation = await evaluate(cdp, `(() => {
    const links = Array.from(document.querySelectorAll(".theme-navigation a"));
    const current = links.filter((link) => link.getAttribute("aria-current") === "location");
    return {
      hash: location.hash,
      currentCount: current.length,
      currentHref: current[0]?.getAttribute("href") ?? null,
    };
  })()`);

  // Guarded clicks (modified keys / prevented) must not pollute current state.
  const guardedClickNavigation = await evaluate(cdp, `(() => {
    const links = Array.from(document.querySelectorAll(".theme-navigation a"));
    const target = links[0];
    const state = (label) => {
      const current = links.filter((link) => link.getAttribute("aria-current") === "location");
      return {
        label,
        hash: location.hash,
        currentCount: current.length,
        currentHref: current[0]?.getAttribute("href") ?? null,
      };
    };
    const dispatchGuarded = (label, init, preventAtTarget = false) => {
      const cancel = (event) => event.preventDefault();
      (preventAtTarget ? target : document).addEventListener("click", cancel, { once: true });
      target.dispatchEvent(new MouseEvent("click", {
        bubbles: true,
        cancelable: true,
        button: 0,
        ...init,
      }));
      return state(label);
    };
    return [
      state("initial"),
      dispatchGuarded("defaultPrevented", {}, true),
      dispatchGuarded("non-primary", { button: 1 }),
      dispatchGuarded("ctrl", { ctrlKey: true }),
      dispatchGuarded("meta", { metaKey: true }),
      dispatchGuarded("shift", { shiftKey: true }),
      dispatchGuarded("alt", { altKey: true }),
    ];
  })()`);

  // Plain (non-themed) report: filter-bar contract and sources-inline alignment.
  await navigate(cdp, pathToFileURL(plainReport).href);
  const plain = await evaluate(cdp, `(async () => {
    document.querySelector('.report-tab-button[data-pane-target="news"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const filterBar = document.querySelector(".filter-bar");
    const filterButtons = Array.from(document.querySelectorAll(".filter-button"));
    const rows = Array.from(document.querySelectorAll(".news-row"));
    document.querySelectorAll(".news-toggle[aria-expanded='false']").forEach(
      (candidate) => candidate.click(),
    );
    await new Promise((resolvePromise) => requestAnimationFrame(() => requestAnimationFrame(resolvePromise)));
    const violations = [];
    let checkedCount = 0;
    rows.forEach((row) => {
      const content = row.querySelector(".news-content");
      const contentLeft = content.getBoundingClientRect().left;
      content.querySelectorAll(
        ":scope > h2, :scope > .news-summary, :scope > .news-toggle, :scope > .news-detail",
      ).forEach((element) => {
        const left = element.getBoundingClientRect().left;
        checkedCount += 1;
        if (Math.abs(left - contentLeft) > 1) {
          violations.push({ row: row.id, element: element.className, contentLeft, left });
        }
      });
    });
    // Category filter interaction: click a non-all button then restore.
    const firstButton = filterButtons[1];
    firstButton.click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const filtered = {
      activeLabel: document.querySelector(".filter-button.is-active")?.textContent.trim(),
      pressed: document.querySelector(".filter-button.is-active")?.getAttribute("aria-pressed"),
      visibleRows: Array.from(document.querySelectorAll(".news-row"))
        .filter((row) => !row.hidden).length,
      totalRows: rows.length,
    };
    document.querySelector('.filter-button[data-category="all"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const restoredVisible = Array.from(document.querySelectorAll(".news-row"))
      .filter((row) => !row.hidden).length;
    const notesLinks = Array.from(
      document.querySelectorAll("[data-component='report-notes'] a"),
    );
    return {
      hasFilterBar: !!filterBar,
      filterMetaText: filterBar?.querySelector(".filter-meta")?.textContent.replace(/\\s+/g, " ").trim() ?? null,
      filterButtonLabels: filterButtons.map((button) => button.textContent.trim()),
      filterButtonCount: filterButtons.length,
      sourcesInlineRows: rows.filter((row) => row.dataset.detailKind === "sources-inline").length,
      rowCount: rows.length,
      checkedCount,
      violations,
      filtered,
      restoredVisible,
      reportNoteLinks: {
        linkCount: notesLinks.length,
        unsafeHrefCount: notesLinks.filter(
          (link) => !["http:", "https:"].includes(new URL(link.href).protocol),
        ).length,
      },
    };
  })()`);

  // Print lifecycle for the pending details (beforeprint expands, afterprint restores).
  await navigate(cdp, pathToFileURL(themedReport).href);
  await evaluate(cdp, `(async () => {
    document.querySelector('.report-tab-button[data-pane-target="news"]').click();
    const conservativeDetailsUa = document.createElement("style");
    conservativeDetailsUa.media = "print";
    conservativeDetailsUa.textContent = "details:not([open]) > :not(summary) { display: none; }";
    document.head.append(conservativeDetailsUa);
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
  })()`);
  await cdp.send("Emulation.setEmulatedMedia", { media: "print" });
  const print = await evaluate(cdp, `(() => {
    const details = document.querySelector(".pending-details");
    const body = document.querySelector(".pending-body");
    const items = Array.from(document.querySelectorAll(".pending-item"));
    const newsDetails = Array.from(document.querySelectorAll(".news-detail"));
    const reportNotes = document.querySelector("[data-component='report-notes']");
    const reportNoteSections = Array.from(document.querySelectorAll("[data-component='report-note-section']"));
    const beforePrint = {
      mediaMatches: matchMedia("print").matches,
      detailsOpen: details.open,
      bodyDisplay: getComputedStyle(body).display,
      visibleItemCount: items.filter((item) => item.getClientRects().length > 0).length,
      itemCount: items.length,
      visibleNewsDetailCount: newsDetails.filter(
        (detail) => detail.getClientRects().length > 0 && detail.getBoundingClientRect().height > 0,
      ).length,
      newsDetailCount: newsDetails.length,
      reportNotesVisible: reportNotes.getClientRects().length > 0,
      visibleReportNoteSectionCount: reportNoteSections.filter(
        (section) => section.getClientRects().length > 0,
      ).length,
      reportNoteSectionCount: reportNoteSections.length,
    };
    dispatchEvent(new Event("beforeprint"));
    const duringPrint = {
      detailsOpen: details.open,
      bodyDisplay: getComputedStyle(body).display,
      visibleItemCount: items.filter((item) => item.getClientRects().length > 0).length,
      visibleNewsDetailCount: newsDetails.filter(
        (detail) => detail.getClientRects().length > 0 && detail.getBoundingClientRect().height > 0,
      ).length,
      reportNotesVisible: reportNotes.getClientRects().length > 0,
      visibleReportNoteSectionCount: reportNoteSections.filter(
        (section) => section.getClientRects().length > 0,
      ).length,
    };
    dispatchEvent(new Event("afterprint"));
    return { beforePrint, duringPrint, restoredOpen: details.open };
  })()`);
  await cdp.send("Emulation.setEmulatedMedia", { media: "screen" });

  // Sticky sidebar + 回到最上 pinned at the bottom, across scroll positions.
  await navigate(cdp, pathToFileURL(longReport).href);
  const sticky = await evaluate(cdp, `(async () => {
    document.querySelector('.report-tab-button[data-pane-target="news"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const sidebar = document.querySelector(".report-sidebar");
    const topLink = document.querySelector(".sidebar-top-link");
    const read = () => {
      const rect = sidebar.getBoundingClientRect();
      const linkRect = topLink.getBoundingClientRect();
      return {
        scrollY: window.scrollY,
        sidebarTop: rect.top,
        sidebarBottom: rect.bottom,
        linkTop: linkRect.top,
        linkBottom: linkRect.bottom,
        linkFullyVisible: linkRect.top >= 0 && linkRect.bottom <= window.innerHeight,
        sidebarInViewport: rect.top >= 0 && rect.bottom <= window.innerHeight,
      };
    };
    const initial = read();
    window.scrollTo({ top: 1500, behavior: "instant" });
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (window.scrollY >= 1490) break;
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 50));
    }
    const mid = read();
    window.scrollTo({ top: 999999, behavior: "instant" });
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (window.scrollY >= document.documentElement.scrollHeight - window.innerHeight - 10) break;
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 50));
    }
    const bottom = read();
    return { initial, mid, bottom };
  })()`);

  // Mobile: sidebar hidden, workspace paddings, navigation scrollable.
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await navigate(cdp, pathToFileURL(themedReport).href);
  const mobile = await evaluate(cdp, `(async () => {
    const shell = document.querySelector(".page-shell");
    const card = document.querySelector(".report-card");
    const sidebar = document.querySelector(".report-sidebar");
    const header = document.querySelector(".topbar");
    const reportMain = document.querySelector(".report-main");
    const mobileControl = document.querySelector(".mobile-report-control");
    const navigation = document.querySelector(".theme-navigation");
    const themeTitle = document.querySelector(".theme-heading-line h2");
    const reportNotes = document.querySelector("[data-component='report-notes']");
    document.querySelector('.report-tab-button[data-pane-target="news"]').click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const notesRect = reportNotes.getBoundingClientRect();
    const target = document.querySelectorAll(".theme-group")[4];
    const link = document.querySelector('.theme-navigation a[href="#' + target.id + '"]');
    scrollTo(0, 0);
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 300));
    link.click();
    for (let attempt = 0; attempt < 30; attempt += 1) {
      if (Math.abs(target.getBoundingClientRect().top) <= 1) break;
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 100));
    }
    return {
      shellPaddingLeft: getComputedStyle(shell).paddingLeft,
      cardBorderRadius: getComputedStyle(card).borderRadius,
      sidebarDisplay: getComputedStyle(sidebar).display,
      topbarMarginLeft: getComputedStyle(header).marginLeft,
      mainPaddingLeft: getComputedStyle(reportMain).paddingLeft,
      mobileControlDisplay: getComputedStyle(mobileControl).display,
      navigationOverflowX: getComputedStyle(navigation).overflowX,
      navigationClientWidth: navigation.clientWidth,
      themeTitleFontSize: getComputedStyle(themeTitle).fontSize,
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      notesClientWidth: reportNotes.clientWidth,
      notesScrollWidth: reportNotes.scrollWidth,
      notesLeft: notesRect.left,
      notesRight: notesRect.right,
      anchorHash: location.hash,
      anchorTargetId: target.id,
      targetTop: target.getBoundingClientRect().top,
    };
  })()`);

  const failures = [];
  // Shell / card / canvas
  if (desktop.shell.maxWidth !== "none" || desktop.shell.paddingTop !== "27px") {
    failures.push(`desktop shell geometry mismatch: ${JSON.stringify(desktop.shell)}`);
  }
  if (Math.abs(desktop.card.width - 1197) > 1) failures.push("desktop card width mismatch");
  if (desktop.card.borderRadius !== "16px") failures.push("desktop card radius mismatch");
  if (
    desktop.bodyBackground !== "rgb(237, 241, 246)"
    || desktop.card.backgroundColor !== "rgb(248, 249, 251)"
  ) {
    failures.push("desktop canvas/card background mismatch");
  }
  if (
    [desktop.card.borderTopStyle].some((value) => value !== "solid")
    || desktop.card.borderTopWidth !== "2px"
    || desktop.card.borderTopColor !== "rgb(202, 211, 225)"
  ) {
    failures.push("desktop card border must be exactly 2px solid #cad3e1");
  }
  if (desktop.card.boxShadow !== "rgba(30, 40, 60, 0.1) 0px 16px 40px 0px") {
    failures.push(`desktop card shadow mismatch: ${desktop.card.boxShadow}`);
  }
  // Fixed sidebar contract (2026-08 redesign, 15vw edge-to-edge)
  if (
    desktop.sidebar.position !== "fixed"
    || desktop.sidebar.topPos !== "0px"
    || Math.abs(desktop.sidebar.height - 900) > 1
    || desktop.sidebar.overflowY !== "auto"
    || desktop.sidebar.borderRadius !== "0px"
  ) {
    failures.push(`desktop sidebar contract mismatch: ${JSON.stringify(desktop.sidebar)}`);
  }
  if (
    Math.abs(desktop.sidebar.width - 216) > 1
    || desktop.sidebar.paddingTop !== "50px"
    || desktop.sidebar.paddingRight !== "18px"
    || desktop.sidebar.paddingBottom !== "14px"
    || desktop.sidebar.paddingLeft !== "18px"
    || desktop.sidebar.backgroundColor !== "rgb(28, 41, 64)"
  ) {
    failures.push("desktop sidebar padding/background mismatch");
  }
  // Brand + date list font sizing
  if (desktop.brand.fontSize !== "18px" || desktop.brand.fontWeight !== "800") {
    failures.push(`desktop brand font mismatch: ${JSON.stringify(desktop.brand)}`);
  }
  if (desktop.dateLinkFontSize !== "12px") {
    failures.push(`desktop date list font mismatch: ${desktop.dateLinkFontSize}`);
  }
  // 回到最上 pinned at the sidebar bottom
  if (
    !desktop.sidebarTopLink
    || desktop.sidebarTopHref !== "#top"
    || desktop.sidebarTopLink.top < desktop.sidebar.bottom - 50
    || desktop.sidebarTopLink.bottom > desktop.sidebar.bottom - 8
  ) {
    failures.push(`sidebar back-to-top is not pinned at the sidebar bottom: ${JSON.stringify({
      link: desktop.sidebarTopLink,
      href: desktop.sidebarTopHref,
      sidebarBottom: desktop.sidebar.bottom,
    })}`);
  }
  // Typography
  const normalizedBodyFont = desktop.bodyFont.split(",").map(
    (font) => font.trim().replace(/^['\"]|['\"]$/g, ""),
  );
  if (JSON.stringify(normalizedBodyFont) !== JSON.stringify([
    "-apple-system",
    "system-ui",
    "Segoe UI",
    "PingFang SC",
    "sans-serif",
  ])) {
    failures.push(`body font stack order mismatch: ${JSON.stringify(normalizedBodyFont)}`);
  }
  if (desktop.reportTitleFontSize !== "21px") failures.push("report title size mismatch");
  if (desktop.themeTitleFontSize !== "25px") failures.push("theme title size mismatch");
  if (desktop.newsTitleFontSize !== "12px") failures.push("news title size mismatch");
  if (
    desktop.reportTitle.color !== "rgb(24, 32, 51)"
    || desktop.reportTitle.fontWeight !== "800"
    || desktop.themeKicker.color !== "rgb(36, 87, 210)"
    || desktop.themeKicker.fontWeight !== "800"
    || desktop.themeKicker.fontSize !== "9px"
    || desktop.themeTitle.fontWeight !== "700"
    || desktop.newsTitle.fontWeight !== "700"
    || desktop.newsRank.fontWeight !== "400"
    || desktop.themeTotal.fontWeight !== "400"
  ) {
    failures.push("desktop key color/font-weight hierarchy mismatch");
  }
  if (desktop.themeTotal.fontSize !== "8px") failures.push("desktop theme metadata size mismatch");
  // Topbar / workspace
  if (desktop.topbar.position !== "static" || desktop.topbar.marginLeft !== "28px") {
    failures.push("desktop topbar geometry mismatch");
  }
  if (desktop.workspacePaddingLeft !== "28px") failures.push("desktop workspace padding mismatch");
  // Theme navigation
  if (desktop.navigation.paddingTop !== "12px" || desktop.navigation.columnGap !== "14px") {
    failures.push("desktop theme navigation rhythm mismatch");
  }
  if (
    desktop.navLinkCount < 5
    || !desktop.navHrefs.some((href) => href.startsWith("#theme-"))
    || !desktop.navHrefs.includes("#other-important-news")
    || !desktop.navHrefs.includes("#pending-notes")
    || desktop.navHrefs.includes("#top")
  ) {
    failures.push(`desktop theme navigation link contract mismatch: ${JSON.stringify(desktop.navHrefs)}`);
  }
  // Theme groups
  if (desktop.themeCount < 2) failures.push("desktop theme group count too small");
  if (desktop.theme.paddingTop !== "23px" || desktop.theme.paddingBottom !== "15px") {
    failures.push("desktop theme section rhythm mismatch");
  }
  if (
    desktop.secondTheme.borderTopWidth !== "6px"
    || desktop.secondTheme.borderTopColor !== "rgb(237, 240, 244)"
    || desktop.secondTheme.borderTopStyle !== "solid"
  ) {
    failures.push("desktop adjacent themes need a 6px #edf0f4 separator");
  }
  if (desktop.themeHeading.alignItems !== "baseline" || desktop.themeHeading.columnGap !== "7px") {
    failures.push("desktop theme heading baseline mismatch");
  }
  if (desktop.newsList.borderTopWidth !== "2px") failures.push("desktop news list divider mismatch");
  // News rows
  if (desktop.rowCount < 1 || desktop.detailRowCount < 1) failures.push("desktop news rows missing");
  if (
    desktop.firstRow.gridTemplateColumns.trim().split(/\s+/).length !== 2
    || desktop.firstRow.gridTemplateColumns.trim().split(/\s+/)[0] !== "30px"
    || Math.abs(desktop.newsRank.width - 30) > 1
    || desktop.firstRow.columnGap !== "9px"
    || desktop.firstRow.paddingTop !== "12px"
  ) {
    failures.push("desktop news grid mismatch");
  }
  if (!desktop.newsRank.fontFamily.includes("Georgia") || desktop.newsRank.fontSize !== "12px") {
    failures.push("desktop news rank typography mismatch");
  }
  if (desktop.newsSummary.fontSize !== "9px") failures.push("desktop news summary size mismatch");
  if (desktop.newsScore.fontSize !== "8px") failures.push("desktop news score size mismatch");
  // Alignment
  if (
    desktop.alignment.mismatches.length
    || desktop.commonLeftLine.violations.length
    || desktop.commonLeftLine.checkedCount < 1
  ) {
    failures.push(`news common left-line coverage/alignment mismatch: ${JSON.stringify({
      alignment: desktop.alignment,
      commonLeftLine: desktop.commonLeftLine,
    })}`);
  }
  // Disclosure lifecycle
  if (
    !desktop.disclosure
    || desktop.disclosure.closed.hidden !== true
    || desktop.disclosure.closed.ariaExpanded !== "false"
    || desktop.disclosure.closed.height !== 0
    || desktop.disclosure.open.hidden !== false
    || desktop.disclosure.open.ariaExpanded !== "true"
    || desktop.disclosure.open.height <= 0
    || desktop.disclosure.closedAgain.hidden !== true
    || desktop.disclosure.closedAgain.ariaExpanded !== "false"
    || desktop.disclosure.closedAgain.height !== 0
  ) {
    failures.push(`news disclosure lifecycle is incomplete: ${JSON.stringify(desktop.disclosure)}`);
  }
  // Navigation current state
  if (
    desktop.initialNavigationCurrent.currentCount !== 1
    || desktop.initialNavigationCurrent.currentHref !== desktop.firstNavigationHref
  ) {
    failures.push(`default theme navigation current state is wrong: ${JSON.stringify(desktop.initialNavigationCurrent)}`);
  }
  if (
    desktop.headerPosition !== "static"
    || desktop.scrollMarginTop !== 0
    || desktop.anchorHash !== `#${desktop.anchorTargetId}`
    || Math.abs(desktop.targetTop) > 1
  ) {
    failures.push(`desktop theme anchor is wrong: ${JSON.stringify({
      position: desktop.headerPosition,
      scrollMarginTop: desktop.scrollMarginTop,
      hash: desktop.anchorHash,
      target: desktop.anchorTargetId,
      top: desktop.targetTop,
    })}`);
  }
  if (
    desktop.clickedNavigationCurrent.currentCount !== 1
    || desktop.clickedNavigationCurrent.currentHref !== `#${desktop.anchorTargetId}`
    || desktop.currentNavigationLink?.color !== "rgb(31, 82, 204)"
    || desktop.currentNavigationLink?.fontWeight !== "800"
    || desktop.inactiveNavigationLink?.color !== "rgb(102, 114, 133)"
    || desktop.inactiveNavigationLink?.fontWeight !== "500"
  ) {
    failures.push(`clicked theme navigation current/style state is wrong: ${JSON.stringify({
      state: desktop.clickedNavigationCurrent,
      current: desktop.currentNavigationLink,
      inactive: desktop.inactiveNavigationLink,
    })}`);
  }
  if (
    directHashNavigation.hash !== `#${desktop.anchorTargetId}`
    || directHashNavigation.currentCount !== 1
    || directHashNavigation.currentHref !== `#${desktop.anchorTargetId}`
  ) {
    failures.push(`direct-hash theme current state is wrong: ${JSON.stringify(directHashNavigation)}`);
  }
  if (guardedClickNavigation.some((state) => (
    state.hash !== `#${desktop.anchorTargetId}`
    || state.currentCount !== 1
    || state.currentHref !== `#${desktop.anchorTargetId}`
  ))) {
    failures.push(`guarded theme clicks polluted current state: ${JSON.stringify(guardedClickNavigation)}`);
  }
  // Archive sidebar
  if (
    desktop.archive.groupCount < 2
    || desktop.archive.ariaExpanded !== "false"
    || !desktop.archive.slotsHidden
    || !/\.html$/.test(desktop.archive.linkHref)
  ) {
    failures.push(`sidebar archive initial state is wrong: ${JSON.stringify(desktop.archive)}`);
  }
  // Report notes
  if (
    !desktop.reportNoteContract.visible
    || desktop.reportNoteContract.title !== "报告说明"
    || desktop.reportNoteContract.sectionCount < 1
    || desktop.reportNoteContract.summaryTitleFontSize > 14
    || desktop.reportNoteContract.summaryTitleFontWeight !== "700"
    || desktop.reportNoteContract.sectionTitleMaximumFontSize > 10
    || desktop.reportNoteContract.bodyMaximumFontSize > 10
    || !desktop.reportNoteContract.afterOther
    || !desktop.reportNoteContract.beforePending
    || desktop.reportNoteContract.unsafeHrefCount !== 0
  ) {
    failures.push(`report-note contract mismatch: ${JSON.stringify(desktop.reportNoteContract)}`);
  }
  // Plain (filter-bar) report contract
  if (
    !plain.hasFilterBar
    || plain.filterButtonCount !== 6
    || JSON.stringify(plain.filterButtonLabels) !== JSON.stringify(["全部", "政策", "财报", "产业", "地缘", "其他"])
    || !plain.filterMetaText?.includes("数据截止")
    || plain.sourcesInlineRows < 1
    || plain.rowCount < 1
    || plain.checkedCount < 1
    || plain.violations.length
    || plain.filtered.activeLabel !== "政策"
    || plain.filtered.pressed !== "true"
    || plain.filtered.visibleRows < 1
    || plain.restoredVisible !== plain.rowCount
    || plain.reportNoteLinks.linkCount < 1
    || plain.reportNoteLinks.unsafeHrefCount !== 0
  ) {
    failures.push(`plain-report filter-bar/alignment contract mismatch: ${JSON.stringify(plain)}`);
  }
  // Print lifecycle
  if (
    !print.beforePrint.mediaMatches
    || print.beforePrint.detailsOpen
    || !print.duringPrint.detailsOpen
    || print.duringPrint.visibleItemCount !== print.beforePrint.itemCount
    || print.beforePrint.visibleNewsDetailCount !== print.beforePrint.newsDetailCount
    || print.duringPrint.visibleNewsDetailCount !== print.beforePrint.newsDetailCount
    || !print.beforePrint.reportNotesVisible
    || !print.duringPrint.reportNotesVisible
    || print.restoredOpen
  ) {
    failures.push(
      `print pending lifecycle is incomplete: ${JSON.stringify(print)}`,
    );
  }
  // Fixed sidebar across scroll positions (anchored to viewport 0)
  if (
    Math.abs(sticky.initial.sidebarTop) > 1
    || !sticky.initial.sidebarInViewport
    || !sticky.initial.linkFullyVisible
    || Math.abs(sticky.mid.sidebarTop) > 1
    || !sticky.mid.sidebarInViewport
    || !sticky.mid.linkFullyVisible
    || !sticky.bottom.sidebarInViewport
    || !sticky.bottom.linkFullyVisible
  ) {
    failures.push(`sidebar scroll contract is wrong: ${JSON.stringify(sticky)}`);
  }
  // Mobile layout
  if (mobile.shellPaddingLeft !== "12px") failures.push("mobile outer padding mismatch");
  if (mobile.cardBorderRadius !== "16px") failures.push("mobile card radius mismatch");
  if (mobile.sidebarDisplay !== "none") failures.push("mobile sidebar remains visible");
  if (mobile.topbarMarginLeft !== "18px" || mobile.mainPaddingLeft !== "18px") {
    failures.push("mobile workspace padding mismatch");
  }
  if (mobile.mobileControlDisplay === "none") failures.push("mobile report selector is hidden");
  if (mobile.themeTitleFontSize !== "21px") failures.push("mobile theme title size mismatch");
  if (mobile.navigationOverflowX !== "auto") failures.push("mobile theme navigation does not scroll");
  if (mobile.navigationClientWidth <= 0) failures.push("mobile theme navigation is not visible");
  if (mobile.scrollWidth > mobile.clientWidth) {
    failures.push(`mobile page overflows: ${mobile.scrollWidth}px > ${mobile.clientWidth}px`);
  }
  if (
    mobile.notesScrollWidth > mobile.notesClientWidth
    || mobile.notesLeft < 0
    || mobile.notesRight > mobile.clientWidth
  ) {
    failures.push(`mobile report notes overflow: ${JSON.stringify(mobile)}`);
  }
  if (
    mobile.anchorHash !== `#${mobile.anchorTargetId}`
    || Math.abs(mobile.targetTop) > 1
  ) {
    failures.push(
      `mobile anchor reset is wrong: hash=${mobile.anchorHash}, top=${mobile.targetTop}px`,
    );
  }
  // News view mode switch contract (ranked = full rows moved, no info loss)
  if (
    !rankedMode.initial.hasSwitch
    || rankedMode.initial.buttons.length !== 2
    || rankedMode.initial.buttons[0].mode !== "themed"
    || !rankedMode.initial.buttons[0].active
    || rankedMode.initial.buttons[0].pressed !== "true"
    || rankedMode.initial.buttons[1].mode !== "ranked"
    || rankedMode.initial.buttons[1].active
    || rankedMode.initial.buttons[1].pressed !== "false"
    || !rankedMode.initial.themedVisible
    || !rankedMode.initial.rankedHidden
    || rankedMode.initial.totalRowCount < 10
  ) {
    failures.push(`news mode switch initial state is wrong: ${JSON.stringify(rankedMode.initial)}`);
  }
  if (
    !rankedMode.afterSwitch.themedHidden
    || !rankedMode.afterSwitch.rankedVisible
    || rankedMode.afterSwitch.activeButton !== "ranked"
    || rankedMode.afterSwitch.rowCount !== rankedMode.initial.totalRowCount
    || rankedMode.afterSwitch.firstRank !== "01"
    || !rankedMode.afterSwitch.firstSummary
    || !rankedMode.afterSwitch.firstHasToggle
    || !rankedMode.afterSwitch.firstHasDetail
    || !rankedMode.afterSwitch.firstHasSources
    || !rankedMode.afterSwitch.tagOnEveryRow
    || !rankedMode.afterSwitch.sortedByScore
    || !rankedMode.afterSwitch.navigationHidden
    || rankedMode.afterSwitch.themedGroupRowCounts.some((count) => count !== 0)
    || !rankedMode.detailExpandedInRanked
  ) {
    failures.push(`ranked news mode is wrong: ${JSON.stringify(rankedMode)}`);
  }
  if (
    !rankedMode.afterJump.themedVisible
    || !rankedMode.afterJump.rankedHidden
    || rankedMode.afterJump.activeMode !== "themed"
    || rankedMode.afterJump.restoredRowCount !== rankedMode.initial.totalRowCount
    || rankedMode.afterJump.themedGroupRowCounts.some((count) => count === 0)
    || rankedMode.afterJump.firstRowRankRestored !== rankedMode.initial.firstThemeFirstRank
    || rankedMode.afterJump.tagsRemoved !== 0
  ) {
    failures.push(`ranked mode restore to themed view is wrong: ${JSON.stringify(rankedMode.afterJump)}`);
  }
  if (browserProblems.length) failures.push(`browser console: ${browserProblems.join(" | ")}`);

  console.log(JSON.stringify({
    buildScope: {
      gitRoot,
      gitDir,
      gitCommonDir,
      superproject: superprojectOutput.trim(),
      trackedReports,
      diskReports,
      manifestReports,
      builtReportPages,
      untrackedMutationRejected,
    },
    desktop: {
      shell: desktop.shell,
      card: desktop.card,
      sidebar: desktop.sidebar,
      sidebarTopLink: desktop.sidebarTopLink,
      topbar: desktop.topbar,
      reportTitle: desktop.reportTitle,
      navigation: desktop.navigation,
      navHrefs: desktop.navHrefs,
      theme: desktop.theme,
      secondTheme: desktop.secondTheme,
      themeKicker: desktop.themeKicker,
      themeTitle: desktop.themeTitle,
      themeTotal: desktop.themeTotal,
      newsList: desktop.newsList,
      firstRow: desktop.firstRow,
      newsRank: desktop.newsRank,
      newsTitle: desktop.newsTitle,
      newsSummary: desktop.newsSummary,
      newsScore: desktop.newsScore,
      alignment: desktop.alignment,
      commonLeftLine: desktop.commonLeftLine,
      disclosure: desktop.disclosure,
      initialNavigationCurrent: desktop.initialNavigationCurrent,
      clickedNavigationCurrent: desktop.clickedNavigationCurrent,
      currentNavigationLink: desktop.currentNavigationLink,
      inactiveNavigationLink: desktop.inactiveNavigationLink,
      reportNoteContract: desktop.reportNoteContract,
      archive: desktop.archive,
      targetTop: desktop.targetTop,
    },
    directHashNavigation,
    guardedClickNavigation,
    plain,
    rankedMode,
    print,
    sticky,
    mobile,
    browserProblems,
  }, null, 2));
  if (failures.length) throw new Error(failures.join("\n"));
  console.log("PASS: shell, sticky sidebar, typography, anchors, filter-bar, print, and mobile layout");
} finally {
  cdp?.close();
  if (chrome && chrome.exitCode === null) {
    chrome.kill("SIGTERM");
    await Promise.race([
      new Promise((resolvePromise) => chrome.once("exit", resolvePromise)),
      new Promise((resolvePromise) => setTimeout(resolvePromise, 2000)),
    ]);
  }
  await rm(scratch, { recursive: true, force: true });
}
