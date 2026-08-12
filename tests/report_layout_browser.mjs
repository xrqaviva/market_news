import { access, mkdtemp, readFile, rm } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { execFile, spawn } from "node:child_process";
import { promisify } from "node:util";

const ROOT = resolve(dirname(new URL(import.meta.url).pathname), "..");
const execFileAsync = promisify(execFile);

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
const profile = join(scratch, "chrome-profile");
let chrome;
let cdp;

try {
  await execFileAsync("python3", [
    "-m",
    "web.build",
    "--project-root",
    ROOT,
    "--output",
    freshDist,
  ], { cwd: ROOT });

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
        borderTopWidth: style.borderTopWidth,
        borderBottomWidth: style.borderBottomWidth,
        columnGap: style.columnGap,
        gridTemplateColumns: style.gridTemplateColumns,
        alignItems: style.alignItems,
        fontFamily: style.fontFamily,
        fontSize: style.fontSize,
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
    const firstTheme = document.querySelector(".theme-group");
    const themeHeader = firstTheme.querySelector(".theme-header");
    const themeHeading = firstTheme.querySelector(".theme-heading-line");
    const themeTitle = themeHeading.querySelector("h2");
    const themeTotal = themeHeading.querySelector(".theme-total");
    const newsList = firstTheme.querySelector(".theme-news-list");
    const newsRow = newsList.querySelector(".news-row");
    const newsRank = newsRow.querySelector(".news-rank");
    const newsContent = newsRow.querySelector(".news-content");
    const newsTitle = newsContent.querySelector("h2");
    const newsSummary = newsContent.querySelector(".news-summary");
    const toggle = newsContent.querySelector(".news-toggle");
    toggle.click();
    await new Promise((resolvePromise) => requestAnimationFrame(resolvePromise));
    const firstDetail = newsContent.querySelector(".news-detail");
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
      themeHeader: metric(themeHeader),
      themeHeading: metric(themeHeading),
      themeTitle: metric(themeTitle),
      themeTotal: metric(themeTotal),
      newsList: metric(newsList),
      newsRow: metric(newsRow),
      newsRank: metric(newsRank),
      newsTitle: metric(newsTitle),
      newsSummary: metric(newsSummary),
      bodyFont: getComputedStyle(document.body).fontFamily,
      workspacePaddingLeft: getComputedStyle(reportMain).paddingLeft,
      reportTitleFontSize: getComputedStyle(reportTitle).fontSize,
      themeTitleFontSize: getComputedStyle(themeTitle).fontSize,
      newsTitleFontSize: getComputedStyle(newsTitle).fontSize,
      newsContentLeft: newsContent.getBoundingClientRect().left,
      firstDetailLeft: firstDetail.getBoundingClientRect().left,
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
    return {
      ...geometry,
      headerBottom: headerRect.bottom,
      headerPosition: getComputedStyle(header).position,
      scrollMarginTop: parseFloat(getComputedStyle(target).scrollMarginTop),
      targetTop: targetRect.top,
      anchorHash: location.hash,
      anchorTargetId: target.id,
    };
  })()`);

  const contrast = await evaluate(cdp, `(() => {
    const element = document.querySelector(".theme-total");
    const parse = (color) => color.match(/[\\d.]+/g).slice(0, 3).map(Number);
    const luminance = (rgb) => {
      const values = rgb.map((value) => {
        const channel = value / 255;
        return channel <= 0.04045
          ? channel / 12.92
          : Math.pow((channel + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
    };
    let backgroundNode = element;
    let background = "rgba(0, 0, 0, 0)";
    while (backgroundNode && /rgba\\([^)]*,\\s*0(?:\\.0+)?\\)$/.test(background)) {
      backgroundNode = backgroundNode.parentElement;
      background = backgroundNode ? getComputedStyle(backgroundNode).backgroundColor : "rgb(255, 255, 255)";
    }
    const foreground = getComputedStyle(element).color;
    const foregroundLuminance = luminance(parse(foreground));
    const backgroundLuminance = luminance(parse(background));
    return {
      foreground,
      background,
      fontSize: getComputedStyle(element).fontSize,
      ratio: (Math.max(foregroundLuminance, backgroundLuminance) + 0.05)
        / (Math.min(foregroundLuminance, backgroundLuminance) + 0.05),
    };
  })()`);

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
    const beforePrint = {
      mediaMatches: matchMedia("print").matches,
      detailsOpen: details.open,
      bodyDisplay: getComputedStyle(body).display,
      bodyHeight: body.getBoundingClientRect().height,
      visibleItemCount: items.filter((item) => item.getClientRects().length > 0).length,
      itemCount: items.length,
    };
    dispatchEvent(new Event("beforeprint"));
    const duringPrint = {
      detailsOpen: details.open,
      bodyDisplay: getComputedStyle(body).display,
      bodyHeight: body.getBoundingClientRect().height,
      visibleItemCount: items.filter((item) => item.getClientRects().length > 0).length,
    };
    dispatchEvent(new Event("afterprint"));
    return { beforePrint, duringPrint, restoredOpen: details.open };
  })()`);

  await cdp.send("Emulation.setEmulatedMedia", { media: "screen" });
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
    const themeTitle = document.querySelector(".theme-heading-line h2");
    const target = document.querySelectorAll(".theme-group")[4];
    const link = document.querySelector('.theme-navigation a[href="#' + target.id + '"]');
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
    };
  })()`);

  const failures = [];
  if (desktop.shell.maxWidth !== "980px" || desktop.shell.paddingTop !== "27px") failures.push("desktop shell geometry mismatch");
  if (Math.abs(desktop.card.width - 926) > 1) failures.push("desktop card width mismatch");
  if (Math.abs(desktop.sidebar.width - 76) > 1) failures.push("desktop sidebar width mismatch");
  if (desktop.workspacePaddingLeft !== "28px") failures.push("desktop workspace padding mismatch");
  if (desktop.card.borderRadius !== "16px") failures.push("desktop card radius mismatch");
  if (!desktop.bodyFont.includes("PingFang SC")) failures.push("body font stack mismatch");
  if (desktop.reportTitleFontSize !== "21px") failures.push("report title size mismatch");
  if (desktop.themeTitleFontSize !== "25px") failures.push("theme title size mismatch");
  if (desktop.newsTitleFontSize !== "12px") failures.push("news title size mismatch");
  if (Math.abs(desktop.newsContentLeft - desktop.firstDetailLeft) > 1) failures.push("news detail alignment mismatch");
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
  if (desktop.themeHeading.alignItems !== "baseline" || desktop.themeHeading.columnGap !== "7px") {
    failures.push("desktop theme heading baseline mismatch");
  }
  if (desktop.themeTotal.fontSize !== "8px") failures.push("desktop theme metadata size mismatch");
  if (desktop.newsList.borderTopWidth !== "2px") failures.push("desktop news list divider mismatch");
  if (
    desktop.newsRow.gridTemplateColumns.split(" ").length !== 2
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
  if (contrast.ratio < 4.5) {
    failures.push(`theme-total contrast ${contrast.ratio.toFixed(2)}:1 is below 4.5:1`);
  }
  if (
    !print.beforePrint.mediaMatches
    || !print.duringPrint.detailsOpen
    || print.duringPrint.bodyHeight <= 0
    || print.duringPrint.visibleItemCount !== print.beforePrint.itemCount
    || print.restoredOpen
  ) {
    failures.push(
      `print pending lifecycle is incomplete: ${JSON.stringify(print)}`,
    );
  }
  if (
    mobile.headerPosition !== "static"
    || mobile.scrollMarginTop !== 0
    || mobile.anchorHash !== `#${mobile.anchorTargetId}`
  ) {
    failures.push(
      `mobile anchor reset is wrong: header=${mobile.headerPosition}, scrollMargin=${mobile.scrollMarginTop}px, hash=${mobile.anchorHash}`,
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
  if (mobile.scrollWidth > mobile.clientWidth) {
    failures.push(`mobile page overflows: ${mobile.scrollWidth}px > ${mobile.clientWidth}px`);
  }
  if (browserProblems.length) failures.push(`browser console: ${browserProblems.join(" | ")}`);

  console.log(JSON.stringify({ desktop, contrast, print, mobile, browserProblems }, null, 2));
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
