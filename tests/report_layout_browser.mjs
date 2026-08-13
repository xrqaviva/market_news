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
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description ?? "browser evaluation failed");
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
const report = join(freshDist, "reports/2026-08-11-0800.html");
const sourceOnlyReport = join(freshDist, "reports/2026-08-10-0800.html");
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
  if (buildInputs.length !== 8) {
    throw new Error(
      `fresh browser build must consume exactly 8 tracked report Markdown files, got ${buildInputs.length}`,
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
  await navigate(cdp, pathToFileURL(report).href);

  const desktop = await evaluate(cdp, `(async () => {
    const metric = (element) => {
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
        marginRight: style.marginRight,
        marginLeft: style.marginLeft,
        borderRadius: style.borderRadius,
        borderTopColor: style.borderTopColor,
        borderRightColor: style.borderRightColor,
        borderBottomColor: style.borderBottomColor,
        borderLeftColor: style.borderLeftColor,
        borderTopStyle: style.borderTopStyle,
        borderRightStyle: style.borderRightStyle,
        borderBottomStyle: style.borderBottomStyle,
        borderLeftStyle: style.borderLeftStyle,
        borderTopWidth: style.borderTopWidth,
        borderRightWidth: style.borderRightWidth,
        borderBottomWidth: style.borderBottomWidth,
        borderLeftWidth: style.borderLeftWidth,
        backgroundColor: style.backgroundColor,
        boxShadow: style.boxShadow,
        color: style.color,
        columnGap: style.columnGap,
        gridTemplateColumns: style.gridTemplateColumns,
        alignItems: style.alignItems,
        overflowX: style.overflowX,
        fontFamily: style.fontFamily,
        fontSize: style.fontSize,
        fontWeight: style.fontWeight,
        lineHeight: style.lineHeight,
      };
    };
    const shell = document.querySelector(".page-shell");
    const card = document.querySelector(".report-card");
    const sidebar = document.querySelector(".report-sidebar");
    const workspace = document.querySelector(".report-workspace");
    const header = document.querySelector(".topbar");
    const reportMain = document.querySelector(".report-main");
    const reportTitle = document.querySelector(".report-heading h1");
    const cutoff = document.querySelector(".report-cutoff");
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
    const newsRow = newsList.querySelector(".news-row");
    const newsRank = newsRow.querySelector(".news-rank");
    const newsContent = newsRow.querySelector(".news-content");
    const newsTitle = newsContent.querySelector("h2");
    const newsSummary = newsContent.querySelector(".news-summary");
    const association = newsContent.querySelector(".news-associations");
    const toggle = newsContent.querySelector(".news-toggle");
    const firstDetail = newsContent.querySelector(".news-detail");
    const disclosure = {
      closed: {
        hidden: firstDetail.hidden,
        ariaExpanded: toggle.getAttribute("aria-expanded"),
        height: firstDetail.getBoundingClientRect().height,
      },
    };
    toggle.click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    disclosure.open = {
      hidden: firstDetail.hidden,
      ariaExpanded: toggle.getAttribute("aria-expanded"),
      height: firstDetail.getBoundingClientRect().height,
    };
    toggle.click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    disclosure.closedAgain = {
      hidden: firstDetail.hidden,
      ariaExpanded: toggle.getAttribute("aria-expanded"),
      height: firstDetail.getBoundingClientRect().height,
    };
    toggle.click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    Array.from(document.querySelectorAll(".news-toggle[aria-expanded='false']")).forEach(
      (candidate) => candidate.click(),
    );
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const sourceList = firstDetail.querySelector("[data-component='sources']");
    const reportNotes = document.querySelector("[data-component='report-notes']");
    const reportNoteTitle = reportNotes.querySelector("h2");
    const reportNoteSectionTitles = Array.from(reportNotes.querySelectorAll(".report-note-section h3"));
    const reportNoteBody = reportNotes.querySelector(".report-note-intro, .report-note-section p, .report-note-section li");
    const reportNoteLinks = Array.from(reportNotes.querySelectorAll("a"));
    const otherImportant = document.querySelector("[data-component='other-important-news']");
    const pendingList = document.querySelector("[data-component='pending-list']");
    const reportNoteContract = {
      visible: reportNotes.getClientRects().length > 0 && reportNotes.getBoundingClientRect().height > 0,
      title: reportNoteTitle.textContent.trim(),
      sectionCount: reportNoteSectionTitles.length,
      titleFontSize: parseFloat(getComputedStyle(reportNoteTitle).fontSize),
      sectionTitleMaximumFontSize: Math.max(
        ...reportNoteSectionTitles.map((title) => parseFloat(getComputedStyle(title).fontSize)),
      ),
      bodyFontSize: parseFloat(getComputedStyle(reportNoteBody).fontSize),
      afterOther: otherImportant.getBoundingClientRect().bottom <= reportNotes.getBoundingClientRect().top,
      beforePending: reportNotes.getBoundingClientRect().bottom <= pendingList.getBoundingClientRect().top,
      linkCount: reportNoteLinks.length,
      unsafeHrefCount: reportNoteLinks.filter(
        (link) => !["http:", "https:"].includes(new URL(link.href).protocol),
      ).length,
    };
    const commonLeftLine = {
      checkedCount: 0,
      violations: [],
      coverage: {
        detailRows: 0,
        sourceOnlyRows: 0,
        otherImportantRows: 0,
        associationPaths: 0,
        sourcePaths: 0,
      },
    };
    document.querySelectorAll(".news-row").forEach((row) => {
      const content = row.querySelector(".news-content");
      const contentLeft = content.getBoundingClientRect().left;
      if (row.dataset.detailKind === "analysis") commonLeftLine.coverage.detailRows += 1;
      if (row.dataset.detailKind === "sources-inline") commonLeftLine.coverage.sourceOnlyRows += 1;
      if (row.closest(".other-important-news")) commonLeftLine.coverage.otherImportantRows += 1;
      commonLeftLine.coverage.associationPaths += content.querySelectorAll(
        ":scope > .news-associations",
      ).length;
      commonLeftLine.coverage.sourcePaths += content.querySelectorAll(
        ":scope > [data-component='sources'], :scope > .news-detail > [data-component='sources']",
      ).length;

      const alignedElements = [
        ...content.querySelectorAll(
          ":scope > h2, :scope > .news-summary, :scope > .news-associations, "
          + ":scope > .news-detail, :scope > [data-component='sources'], "
          + ":scope > .news-detail > [data-component='sources']",
        ),
        row.querySelector(".news-score"),
      ].filter(Boolean);
      alignedElements.forEach((element) => {
        const left = element.getBoundingClientRect().left;
        commonLeftLine.checkedCount += 1;
        if (Math.abs(left - contentLeft) > 1) {
          commonLeftLine.violations.push({
            row: row.id,
            element: element.className || element.tagName,
            contentLeft,
            left,
          });
        }
      });
    });
    const navState = () => ({
      currentCount: navigationLinks.filter(
        (candidate) => candidate.getAttribute("aria-current") === "location",
      ).length,
      currentHref: navigationLinks.find(
        (candidate) => candidate.getAttribute("aria-current") === "location",
      )?.getAttribute("href") ?? null,
    });
    const initialNavigationCurrent = navState();
    const geometry = {
      shell: metric(shell),
      card: metric(card),
      sidebar: metric(sidebar),
      workspace: metric(workspace),
      topbar: metric(header),
      reportMain: metric(reportMain),
      reportTitle: metric(reportTitle),
      cutoff: metric(cutoff),
      navigation: metric(navigation),
      theme: metric(firstTheme),
      secondTheme: metric(secondTheme),
      themeHeader: metric(themeHeader),
      themeKicker: metric(themeKicker),
      themeHeading: metric(themeHeading),
      themeTitle: metric(themeTitle),
      themeTotal: metric(themeTotal),
      newsList: metric(newsList),
      newsRow: metric(newsRow),
      newsRank: metric(newsRank),
      newsTitle: metric(newsTitle),
      newsSummary: metric(newsSummary),
      reportEyebrow: metric(document.querySelector(".report-eyebrow")),
      bodyFont: getComputedStyle(document.body).fontFamily,
      bodyBackground: getComputedStyle(document.body).backgroundColor,
      workspacePaddingLeft: getComputedStyle(reportMain).paddingLeft,
      reportTitleFontSize: getComputedStyle(reportTitle).fontSize,
      themeTitleFontSize: getComputedStyle(themeTitle).fontSize,
      newsTitleFontSize: getComputedStyle(newsTitle).fontSize,
      newsContentLeft: newsContent.getBoundingClientRect().left,
      newsTitleLeft: newsTitle.getBoundingClientRect().left,
      newsSummaryLeft: newsSummary.getBoundingClientRect().left,
      associationLeft: association.getBoundingClientRect().left,
      firstDetailLeft: firstDetail.getBoundingClientRect().left,
      firstSourceLeft: sourceList.getBoundingClientRect().left,
      reportNoteContract,
      commonLeftLine,
      disclosure,
      initialNavigationCurrent,
      firstNavigationHref: navigationLinks[0].getAttribute("href"),
      titleCutoffBottomDelta: Math.abs(
        reportTitle.getBoundingClientRect().bottom - cutoff.getBoundingClientRect().bottom
      ),
    };
    const target = document.querySelectorAll(".theme-group")[2];
    const link = document.querySelector('.theme-navigation a[href="#' + target.id + '"]');
    scrollTo(0, 0);
    link.click();
    await new Promise((resolvePromise) => requestAnimationFrame(() => requestAnimationFrame(resolvePromise)));
    const headerRect = header.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const clickedNavigationCurrent = navState();
    const currentLink = navigationLinks.find(
      (candidate) => candidate.getAttribute("aria-current") === "location",
    );
    const inactiveLink = navigationLinks.find((candidate) => candidate !== currentLink);
    return {
      ...geometry,
      headerBottom: headerRect.bottom,
      headerPosition: getComputedStyle(header).position,
      scrollMarginTop: parseFloat(getComputedStyle(target).scrollMarginTop),
      targetTop: targetRect.top,
      anchorHash: location.hash,
      anchorTargetId: target.id,
      directTargetId: document.querySelectorAll(".theme-group")[4].id,
      clickedNavigationCurrent,
      currentNavigationLink: currentLink ? metric(currentLink) : null,
      inactiveNavigationLink: inactiveLink ? metric(inactiveLink) : null,
    };
  })()`);

  await navigate(cdp, pathToFileURL(sourceOnlyReport).href);
  const sourceOnlyAlignment = await evaluate(cdp, `(() => {
    const rows = Array.from(document.querySelectorAll(
      ".news-row[data-detail-kind='sources-inline']",
    ));
    const violations = [];
    let checkedCount = 0;
    rows.forEach((row) => {
      const content = row.querySelector(".news-content");
      const contentLeft = content.getBoundingClientRect().left;
      content.querySelectorAll(
        ":scope > h2, :scope > .news-summary, :scope > [data-component='sources']",
      ).forEach((element) => {
        const left = element.getBoundingClientRect().left;
        checkedCount += 1;
        if (Math.abs(left - contentLeft) > 1) {
          violations.push({ row: row.id, element: element.className, contentLeft, left });
        }
      });
    });
    const reportNoteLinks = Array.from(
      document.querySelectorAll("[data-component='report-notes'] a"),
    );
    return {
      rowCount: rows.length,
      checkedCount,
      violations,
      reportNoteLinkSafety: {
        linkCount: reportNoteLinks.length,
        unsafeHrefCount: reportNoteLinks.filter(
          (link) => !["http:", "https:"].includes(new URL(link.href).protocol),
        ).length,
      },
    };
  })()`);

  await navigate(cdp, "about:blank");
  await navigate(cdp, `${pathToFileURL(report).href}#${desktop.directTargetId}`);
  const directHashNavigation = await evaluate(cdp, `(() => {
    const links = Array.from(document.querySelectorAll(".theme-navigation a"));
    const current = links.filter((link) => link.getAttribute("aria-current") === "location");
    return {
      hash: location.hash,
      currentCount: current.length,
      currentHref: current[0]?.getAttribute("href") ?? null,
    };
  })()`);

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

  await evaluate(cdp, `(async () => {
    const archiveLink = document.querySelector(
      ".archive-date-group[data-report-date='2026-08-11'] .archive-date-link",
    );
    const changed = new Promise((resolvePromise) =>
      addEventListener("hashchange", resolvePromise, { once: true })
    );
    archiveLink.click();
    await changed;
    document.querySelectorAll(".news-toggle[aria-expanded='false']").forEach(
      (toggle) => toggle.click(),
    );
    document.querySelector(".pending-details").open = true;
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
  })()`);

  const contrast = await evaluate(cdp, `(() => {
    const parse = (color) => {
      const channels = color.match(/[\\d.]+/g)?.map(Number) ?? [];
      return {
        red: channels[0] ?? 0,
        green: channels[1] ?? 0,
        blue: channels[2] ?? 0,
        alpha: channels[3] ?? 1,
      };
    };
    const composite = (foreground, background) => {
      const alpha = foreground.alpha + background.alpha * (1 - foreground.alpha);
      if (alpha === 0) return { red: 0, green: 0, blue: 0, alpha: 0 };
      return {
        red: (
          foreground.red * foreground.alpha
          + background.red * background.alpha * (1 - foreground.alpha)
        ) / alpha,
        green: (
          foreground.green * foreground.alpha
          + background.green * background.alpha * (1 - foreground.alpha)
        ) / alpha,
        blue: (
          foreground.blue * foreground.alpha
          + background.blue * background.alpha * (1 - foreground.alpha)
        ) / alpha,
        alpha,
      };
    };
    const luminance = (rgb) => {
      const values = [rgb.red, rgb.green, rgb.blue].map((value) => {
        const channel = value / 255;
        return channel <= 0.04045
          ? channel / 12.92
          : Math.pow((channel + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
    };
    const path = (element) => {
      const parts = [];
      let node = element;
      while (node && node.nodeType === Node.ELEMENT_NODE) {
        let part = node.tagName.toLowerCase();
        if (node.id) {
          part += '#' + node.id;
          parts.unshift(part);
          break;
        }
        const classes = Array.from(node.classList).slice(0, 2);
        if (classes.length) part += '.' + classes.join('.');
        const siblings = node.parentElement
          ? Array.from(node.parentElement.children).filter(
            (sibling) => sibling.tagName === node.tagName,
          )
          : [];
        if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
        parts.unshift(part);
        node = node.parentElement;
      }
      return parts.join(' > ');
    };
    const effectiveBackground = (element) => {
      const ancestors = [];
      for (let node = element; node; node = node.parentElement) ancestors.unshift(node);
      return ancestors.reduce(
        (background, node) => composite(parse(getComputedStyle(node).backgroundColor), background),
        { red: 255, green: 255, blue: 255, alpha: 1 },
      );
    };
    const scan = () => {
      const seen = new Set();
      const results = [];
      document.querySelectorAll("*").forEach((element) => {
        if (seen.has(element)) return;
        seen.add(element);
        const directText = Array.from(element.childNodes)
          .filter((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim())
          .map((node) => node.textContent.trim())
          .join(" ");
        if (!directText) return;
        const style = getComputedStyle(element);
        if (
          parseFloat(style.fontSize) >= 18
          || style.display === "none"
          || style.visibility === "hidden"
          || parseFloat(style.opacity) === 0
          || element.getClientRects().length === 0
        ) return;
        const background = effectiveBackground(element);
        const color = parse(style.color);
        const foreground = composite(color, background);
        const foregroundLuminance = luminance(foreground);
        const backgroundLuminance = luminance(background);
        results.push({
          path: path(element),
          text: directText.slice(0, 60),
          foreground: style.color,
          background: [background.red, background.green, background.blue, background.alpha],
          fontSize: style.fontSize,
          ratio: (Math.max(foregroundLuminance, backgroundLuminance) + 0.05)
            / (Math.min(foregroundLuminance, backgroundLuminance) + 0.05),
        });
      });
      return results;
    };

    const mutationTarget = document.querySelector(".news-content h2");
    const originalStyle = mutationTarget.getAttribute("style");
    const mutationRow = mutationTarget.closest(".news-row");
    const originalRowStyle = mutationRow.getAttribute("style");
    mutationRow.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
    mutationTarget.style.color = "rgb(146, 156, 171)";
    const mutationResults = scan();
    const mutationPath = path(mutationTarget);
    if (originalStyle === null) mutationTarget.removeAttribute("style");
    else mutationTarget.setAttribute("style", originalStyle);
    if (originalRowStyle === null) mutationRow.removeAttribute("style");
    else mutationRow.setAttribute("style", originalRowStyle);
    const results = scan();
    return {
      count: results.length,
      results,
      minimum: Math.min(...results.map((result) => result.ratio)),
      reportNoteCount: results.filter((result) => result.path.includes("report-note")).length,
      mutation: {
        path: mutationPath,
        result: mutationResults.find((result) => result.path === mutationPath),
      },
    };
  })()`);

  await navigate(cdp, pathToFileURL(report).href);

  await evaluate(cdp, `(() => {
    const conservativeDetailsUa = document.createElement("style");
    conservativeDetailsUa.media = "print";
    conservativeDetailsUa.textContent = "details:not([open]) > :not(summary) { display: none; }";
    document.head.append(conservativeDetailsUa);
  })()`);
  await cdp.send("Emulation.setEmulatedMedia", { media: "print" });
  const print = await evaluate(cdp, `(() => {
    const details = document.querySelector(".pending-details");
    const body = document.querySelector(".pending-body");
    const items = Array.from(document.querySelectorAll(".pending-item"));
    const newsDetails = Array.from(document.querySelectorAll(".news-detail"));
    const reportNotes = document.querySelector("[data-component='report-notes']");
    const reportNoteSections = Array.from(reportNotes.querySelectorAll("[data-component='report-note-section']"));
    const beforePrint = {
      mediaMatches: matchMedia("print").matches,
      detailsOpen: details.open,
      bodyDisplay: getComputedStyle(body).display,
      bodyHeight: body.getBoundingClientRect().height,
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
      bodyHeight: body.getBoundingClientRect().height,
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
  await navigate(cdp, pathToFileURL(report).href);
  const archiveFirstClick = await evaluate(cdp, `(async () => {
    const group = document.querySelector(".archive-date-group[data-report-date='2026-08-11']");
    const link = group.querySelector(".archive-date-link");
    const slots = document.getElementById(link.getAttribute("aria-controls"));
    const themeLinks = Array.from(document.querySelectorAll(".theme-navigation a"));
    const themeCurrent = () => {
      const current = themeLinks.filter(
        (candidate) => candidate.getAttribute("aria-current") === "location",
      );
      return {
        count: current.length,
        href: current[0]?.getAttribute("href") ?? null,
        firstHref: themeLinks[0].getAttribute("href"),
      };
    };
    const initial = {
      expanded: link.getAttribute("aria-expanded"),
      slotsHidden: slots.hidden,
    };
    const changed = new Promise((resolvePromise) => addEventListener("hashchange", resolvePromise, { once: true }));
    link.click();
    await changed;
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    return {
      initial,
      afterClick: {
        hash: location.hash,
        expanded: link.getAttribute("aria-expanded"),
        slotsHidden: slots.hidden,
        themeCurrent: themeCurrent(),
      },
    };
  })()`);
  const secondArchiveHref = await evaluate(cdp, `(() => {
    const link = document.querySelector(".archive-date-group[data-report-date='2026-08-10'] .archive-date-link");
    const href = link.href;
    link.click();
    return href;
  })()`);
  await poll(async () => {
    const href = await evaluate(cdp, "location.href");
    return href === secondArchiveHref ? true : undefined;
  });
  await poll(async () => {
    const state = await evaluate(cdp, "document.readyState");
    return state === "complete" ? true : undefined;
  });
  const archiveSecondClick = await evaluate(cdp, `(() => {
    const state = (date) => {
      const group = document.querySelector('.archive-date-group[data-report-date="' + date + '"]');
      const link = group.querySelector(".archive-date-link");
      const slots = document.getElementById(link.getAttribute("aria-controls"));
      return {
        expanded: link.getAttribute("aria-expanded"),
        slotsHidden: slots.hidden,
      };
    };
    return {
      hash: location.hash,
      firstDate: state("2026-08-11"),
      secondDate: state("2026-08-10"),
    };
  })()`);

  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await navigate(cdp, pathToFileURL(report).href);
  const mobile = await evaluate(cdp, `(async () => {
    const shell = document.querySelector(".page-shell");
    const card = document.querySelector(".report-card");
    const sidebar = document.querySelector(".report-sidebar");
    const header = document.querySelector(".topbar");
    const reportMain = document.querySelector(".report-main");
    const mobileControl = document.querySelector(".mobile-report-control");
    const navigation = document.querySelector(".theme-navigation");
    const navigationLinks = Array.from(navigation.querySelectorAll("a"));
    const themeTitle = document.querySelector(".theme-heading-line h2");
    const reportNotes = document.querySelector("[data-component='report-notes']");
    const reportNotesRect = reportNotes.getBoundingClientRect();
    const target = document.querySelectorAll(".theme-group")[4];
    const link = document.querySelector('.theme-navigation a[href="#' + target.id + '"]');
    const initialCurrentLinks = navigationLinks.filter(
      (candidate) => candidate.getAttribute("aria-current") === "location",
    );
    scrollTo(0, 0);
    link.click();
    await new Promise((resolvePromise) => requestAnimationFrame(() => requestAnimationFrame(resolvePromise)));
    return {
      headerPosition: getComputedStyle(header).position,
      scrollMarginTop: parseFloat(getComputedStyle(target).scrollMarginTop),
      targetTop: target.getBoundingClientRect().top,
      anchorHash: location.hash,
      anchorTargetId: target.id,
      shellPaddingLeft: getComputedStyle(shell).paddingLeft,
      cardBorderRadius: getComputedStyle(card).borderRadius,
      sidebarDisplay: getComputedStyle(sidebar).display,
      topbarMarginLeft: getComputedStyle(header).marginLeft,
      mainPaddingLeft: getComputedStyle(reportMain).paddingLeft,
      mobileControlDisplay: getComputedStyle(mobileControl).display,
      navigationOverflowX: getComputedStyle(navigation).overflowX,
      navigationClientWidth: navigation.clientWidth,
      navigationScrollWidth: navigation.scrollWidth,
      themeTitleFontSize: getComputedStyle(themeTitle).fontSize,
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      initialNavigationCurrentCount: initialCurrentLinks.length,
      initialNavigationCurrentHref: initialCurrentLinks[0]?.getAttribute("href") ?? null,
      firstNavigationHref: navigationLinks[0].getAttribute("href"),
      clickedNavigationCurrentCount: navigationLinks.filter(
        (candidate) => candidate.getAttribute("aria-current") === "location",
      ).length,
      clickedNavigationCurrentHref: navigationLinks.find(
        (candidate) => candidate.getAttribute("aria-current") === "location",
      )?.getAttribute("href") ?? null,
      reportNotesClientWidth: reportNotes.clientWidth,
      reportNotesScrollWidth: reportNotes.scrollWidth,
      reportNotesLeft: reportNotesRect.left,
      reportNotesRight: reportNotesRect.right,
    };
  })()`);

  const failures = [];
  if (desktop.shell.maxWidth !== "980px" || desktop.shell.paddingTop !== "27px") failures.push("desktop shell geometry mismatch");
  if (Math.abs(desktop.card.width - 926) > 1) failures.push("desktop card width mismatch");
  if (Math.abs(desktop.sidebar.width - 76) > 1) failures.push("desktop sidebar width mismatch");
  if (desktop.workspacePaddingLeft !== "28px") failures.push("desktop workspace padding mismatch");
  if (desktop.card.borderRadius !== "16px") failures.push("desktop card radius mismatch");
  if (
    desktop.bodyBackground !== "rgb(237, 241, 246)"
    || desktop.card.backgroundColor !== "rgb(248, 249, 251)"
  ) {
    failures.push("desktop canvas/card background mismatch");
  }
  if (
    [
      desktop.card.borderTopStyle,
      desktop.card.borderRightStyle,
      desktop.card.borderBottomStyle,
      desktop.card.borderLeftStyle,
    ].some((value) => value !== "solid")
    || [
      desktop.card.borderTopWidth,
      desktop.card.borderRightWidth,
      desktop.card.borderBottomWidth,
      desktop.card.borderLeftWidth,
    ].some((value) => value !== "2px")
    || [
      desktop.card.borderTopColor,
      desktop.card.borderRightColor,
      desktop.card.borderBottomColor,
      desktop.card.borderLeftColor,
    ].some((value) => value !== "rgb(202, 211, 225)")
  ) {
    failures.push("desktop card border must be exactly 2px solid #cad3e1");
  }
  if (desktop.card.boxShadow !== "rgba(30, 40, 60, 0.1) 0px 16px 40px 0px") {
    failures.push(`desktop card shadow mismatch: ${desktop.card.boxShadow}`);
  }
  if (
    desktop.sidebar.paddingTop !== "17px"
    || desktop.sidebar.paddingRight !== "9px"
    || desktop.sidebar.paddingBottom !== "17px"
    || desktop.sidebar.paddingLeft !== "9px"
    || desktop.sidebar.backgroundColor !== "rgb(28, 41, 64)"
  ) {
    failures.push("desktop sidebar padding/background mismatch");
  }
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
  const contentLeftEdges = {
    title: desktop.newsTitleLeft,
    summary: desktop.newsSummaryLeft,
    association: desktop.associationLeft,
    detail: desktop.firstDetailLeft,
    source: desktop.firstSourceLeft,
  };
  if (Object.values(contentLeftEdges).some((left) => Math.abs(desktop.newsContentLeft - left) > 1)) {
    failures.push(`news content/detail/source/association alignment mismatch: ${JSON.stringify(contentLeftEdges)}`);
  }
  if (desktop.topbar.position !== "static" || desktop.topbar.marginLeft !== "28px") {
    failures.push("desktop topbar geometry mismatch");
  }
  if (desktop.titleCutoffBottomDelta > 1) failures.push("desktop report title baseline mismatch");
  if (desktop.navigation.columnGap !== "16px" || desktop.navigation.paddingTop !== "12px") {
    failures.push("desktop theme navigation rhythm mismatch");
  }
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
  if (
    desktop.reportTitle.color !== "rgb(24, 32, 51)"
    || desktop.reportTitle.fontWeight !== "800"
    || desktop.themeKicker.color !== "rgb(36, 87, 210)"
    || desktop.themeKicker.fontWeight !== "800"
    || desktop.themeTitle.fontWeight !== "700"
    || desktop.newsTitle.fontWeight !== "700"
    || desktop.newsRank.fontWeight !== "400"
    || desktop.themeTotal.fontWeight !== "400"
  ) {
    failures.push("desktop key color/font-weight hierarchy mismatch");
  }
  if (desktop.themeTotal.fontSize !== "8px") failures.push("desktop theme metadata size mismatch");
  if (desktop.newsList.borderTopWidth !== "2px") failures.push("desktop news list divider mismatch");
  if (
    desktop.newsRow.gridTemplateColumns.trim().split(/\s+/).length !== 2
    || desktop.newsRow.gridTemplateColumns.trim().split(/\s+/)[0] !== "30px"
    || Math.abs(desktop.newsRank.width - 30) > 1
    || desktop.newsRow.columnGap !== "9px"
    || desktop.newsRow.paddingTop !== "12px"
  ) {
    failures.push("desktop news grid mismatch");
  }
  if (!desktop.newsRank.fontFamily.includes("Georgia") || desktop.newsRank.fontSize !== "12px") {
    failures.push("desktop news rank typography mismatch");
  }
  if (desktop.newsSummary.fontSize !== "9px") failures.push("desktop news summary size mismatch");
  if (
    desktop.commonLeftLine.violations.length
    || desktop.commonLeftLine.checkedCount < 1
    || desktop.commonLeftLine.coverage.detailRows < 1
    || desktop.commonLeftLine.coverage.otherImportantRows < 1
    || desktop.commonLeftLine.coverage.associationPaths < 1
    || desktop.commonLeftLine.coverage.sourcePaths < 1
  ) {
    failures.push(`news common left-line coverage/alignment mismatch: ${JSON.stringify(desktop.commonLeftLine)}`);
  }
  if (
    sourceOnlyAlignment.rowCount < 1
    || sourceOnlyAlignment.checkedCount < 1
    || sourceOnlyAlignment.violations.length
  ) {
    failures.push(`source-only news common left-line mismatch: ${JSON.stringify(sourceOnlyAlignment)}`);
  }
  if (
    !desktop.disclosure.closed.hidden
    || desktop.disclosure.closed.ariaExpanded !== "false"
    || desktop.disclosure.closed.height !== 0
    || desktop.disclosure.open.hidden
    || desktop.disclosure.open.ariaExpanded !== "true"
    || desktop.disclosure.open.height <= 0
    || !desktop.disclosure.closedAgain.hidden
    || desktop.disclosure.closedAgain.ariaExpanded !== "false"
    || desktop.disclosure.closedAgain.height !== 0
  ) {
    failures.push(`news disclosure lifecycle is incomplete: ${JSON.stringify(desktop.disclosure)}`);
  }
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
    directHashNavigation.hash !== `#${desktop.directTargetId}`
    || directHashNavigation.currentCount !== 1
    || directHashNavigation.currentHref !== `#${desktop.directTargetId}`
  ) {
    failures.push(`direct-hash theme current state is wrong: ${JSON.stringify(directHashNavigation)}`);
  }
  if (guardedClickNavigation.some((state) => (
    state.hash !== `#${desktop.directTargetId}`
    || state.currentCount !== 1
    || state.currentHref !== `#${desktop.directTargetId}`
  ))) {
    failures.push(`guarded theme clicks polluted current state: ${JSON.stringify(guardedClickNavigation)}`);
  }
  if (!contrast.mutation.result || contrast.mutation.result.ratio >= 4.5) {
    failures.push(`all-visible contrast scanner missed its controlled mutant: ${JSON.stringify(contrast.mutation)}`);
  }
  const expectedMutationBackground = [124, 124.5, 125.5, 1];
  if (
    !contrast.mutation.result
    || contrast.mutation.result.background.some(
      (channel, index) => Math.abs(channel - expectedMutationBackground[index]) > 0.01,
    )
  ) {
    failures.push(`contrast scanner alpha composition is wrong: ${JSON.stringify({
      actual: contrast.mutation.result?.background,
      expected: expectedMutationBackground,
    })}`);
  }
  const lowContrast = contrast.results
    .filter((result) => result.ratio < 4.5)
    .map(({ path, text, foreground, background, fontSize, ratio }) => ({
      path,
      text,
      foreground,
      background,
      fontSize,
      ratio,
    }));
  if (lowContrast.length) {
    failures.push(`visible direct-text contrast below 4.5:1: ${JSON.stringify(lowContrast)}`);
  }
  if (
    !desktop.reportNoteContract.visible
    || desktop.reportNoteContract.title !== "报告说明"
    || desktop.reportNoteContract.sectionCount < 1
    || desktop.reportNoteContract.titleFontSize > 14
    || desktop.reportNoteContract.sectionTitleMaximumFontSize > 10
    || desktop.reportNoteContract.bodyFontSize > 10
    || !desktop.reportNoteContract.afterOther
    || !desktop.reportNoteContract.beforePending
    || desktop.reportNoteContract.unsafeHrefCount !== 0
  ) {
    failures.push(`report-note contract mismatch: ${JSON.stringify(desktop.reportNoteContract)}`);
  }
  if (
    sourceOnlyAlignment.reportNoteLinkSafety.linkCount < 1
    || sourceOnlyAlignment.reportNoteLinkSafety.unsafeHrefCount !== 0
  ) {
    failures.push(
      `report-note link safety mismatch: ${JSON.stringify(sourceOnlyAlignment.reportNoteLinkSafety)}`,
    );
  }
  if (
    !print.beforePrint.mediaMatches
    || !print.duringPrint.detailsOpen
    || print.duringPrint.bodyHeight <= 0
    || print.duringPrint.visibleItemCount !== print.beforePrint.itemCount
    || print.beforePrint.visibleNewsDetailCount !== print.beforePrint.newsDetailCount
    || print.duringPrint.visibleNewsDetailCount !== print.beforePrint.newsDetailCount
    || !print.beforePrint.reportNotesVisible
    || !print.duringPrint.reportNotesVisible
    || print.beforePrint.visibleReportNoteSectionCount !== print.beforePrint.reportNoteSectionCount
    || print.duringPrint.visibleReportNoteSectionCount !== print.beforePrint.reportNoteSectionCount
    || print.restoredOpen
  ) {
    failures.push(
      `print pending lifecycle is incomplete: ${JSON.stringify(print)}`,
    );
  }
  if (
    archiveFirstClick.initial.expanded !== "false"
    || !archiveFirstClick.initial.slotsHidden
    || archiveFirstClick.afterClick.hash !== "#archive-2026-08-11"
    || archiveFirstClick.afterClick.expanded !== "true"
    || archiveFirstClick.afterClick.slotsHidden
    || archiveFirstClick.afterClick.themeCurrent.count !== 1
    || archiveFirstClick.afterClick.themeCurrent.href
      !== archiveFirstClick.afterClick.themeCurrent.firstHref
    || archiveSecondClick.hash !== "#archive-2026-08-10"
    || archiveSecondClick.firstDate.expanded !== "false"
    || !archiveSecondClick.firstDate.slotsHidden
    || archiveSecondClick.secondDate.expanded !== "true"
    || archiveSecondClick.secondDate.slotsHidden
  ) {
    failures.push(`archive date expand/collapse lifecycle is wrong: ${JSON.stringify({
      archiveFirstClick,
      archiveSecondClick,
    })}`);
  }
  if (
    mobile.headerPosition !== "static"
    || mobile.scrollMarginTop !== 0
    || mobile.anchorHash !== `#${mobile.anchorTargetId}`
    || Math.abs(mobile.targetTop) > 1
  ) {
    failures.push(
      `mobile anchor reset is wrong: header=${mobile.headerPosition}, scrollMargin=${mobile.scrollMarginTop}px, hash=${mobile.anchorHash}, top=${mobile.targetTop}px`,
    );
  }
  if (mobile.shellPaddingLeft !== "12px") failures.push("mobile outer padding mismatch");
  if (mobile.topbarMarginLeft !== "18px" || mobile.mainPaddingLeft !== "18px") {
    failures.push("mobile workspace padding mismatch");
  }
  if (mobile.sidebarDisplay !== "none") failures.push("mobile sidebar remains visible");
  if (mobile.mobileControlDisplay === "none") failures.push("mobile report selector is hidden");
  if (mobile.themeTitleFontSize !== "21px") failures.push("mobile theme title size mismatch");
  if (mobile.cardBorderRadius !== "16px") failures.push("mobile card radius mismatch");
  if (mobile.navigationOverflowX !== "auto") failures.push("mobile theme navigation does not scroll");
  if (mobile.navigationScrollWidth <= mobile.navigationClientWidth) {
    failures.push(
      `mobile theme navigation does not have real horizontal overflow: ${mobile.navigationScrollWidth}px <= ${mobile.navigationClientWidth}px`,
    );
  }
  if (
    mobile.initialNavigationCurrentCount !== 1
    || mobile.initialNavigationCurrentHref !== mobile.firstNavigationHref
    || mobile.clickedNavigationCurrentCount !== 1
    || mobile.clickedNavigationCurrentHref !== `#${mobile.anchorTargetId}`
  ) {
    failures.push(`mobile theme navigation current lifecycle is wrong: ${JSON.stringify(mobile)}`);
  }
  if (mobile.scrollWidth > mobile.clientWidth) {
    failures.push(`mobile page overflows: ${mobile.scrollWidth}px > ${mobile.clientWidth}px`);
  }
  if (
    mobile.reportNotesScrollWidth > mobile.reportNotesClientWidth
    || mobile.reportNotesLeft < 0
    || mobile.reportNotesRight > mobile.clientWidth
  ) {
    failures.push(`mobile report notes overflow: ${JSON.stringify({
      clientWidth: mobile.clientWidth,
      noteClientWidth: mobile.reportNotesClientWidth,
      noteScrollWidth: mobile.reportNotesScrollWidth,
      noteLeft: mobile.reportNotesLeft,
      noteRight: mobile.reportNotesRight,
    })}`);
  }
  if (contrast.reportNoteCount < 1) {
    failures.push(`contrast scan missed report-note text: ${contrast.reportNoteCount}`);
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
      reportMain: desktop.reportMain,
      reportTitle: desktop.reportTitle,
      cutoff: desktop.cutoff,
      navigation: desktop.navigation,
      theme: desktop.theme,
      secondTheme: desktop.secondTheme,
      themeKicker: desktop.themeKicker,
      themeTitle: desktop.themeTitle,
      themeTotal: desktop.themeTotal,
      newsList: desktop.newsList,
      newsRow: desktop.newsRow,
      newsRank: desktop.newsRank,
      newsTitle: desktop.newsTitle,
      newsSummary: desktop.newsSummary,
      bodyFont: desktop.bodyFont,
      bodyBackground: desktop.bodyBackground,
      contentLeftEdges: { newsContent: desktop.newsContentLeft, ...contentLeftEdges },
      commonLeftLine: desktop.commonLeftLine,
      sourceOnlyAlignment,
      disclosure: desktop.disclosure,
      initialNavigationCurrent: desktop.initialNavigationCurrent,
      clickedNavigationCurrent: desktop.clickedNavigationCurrent,
      currentNavigationLink: desktop.currentNavigationLink,
      inactiveNavigationLink: desktop.inactiveNavigationLink,
      reportNoteContract: desktop.reportNoteContract,
      targetTop: desktop.targetTop,
    },
    directHashNavigation,
    guardedClickNavigation,
    contrast: {
      count: contrast.count,
      minimum: contrast.minimum,
      mutation: contrast.mutation,
      reportNoteCount: contrast.reportNoteCount,
      lowContrast,
    },
    print,
    archiveFirstClick,
    archiveSecondClick,
    mobile,
    browserProblems,
  }, null, 2));
  if (failures.length) throw new Error(failures.join("\n"));
  console.log("PASS: reference geometry, typography, anchors, print appendix, contrast, and mobile layout");
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
