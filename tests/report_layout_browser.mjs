import { access, mkdtemp, readFile, rm } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { spawn } from "node:child_process";

const ROOT = resolve(dirname(new URL(import.meta.url).pathname), "..");
const REPORT = resolve(ROOT, "web/dist/reports/2026-08-11-0800.html");

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

const profile = await mkdtemp(join(tmpdir(), "news-radar-layout-"));
let chrome;
let cdp;

try {
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
  await navigate(cdp, pathToFileURL(REPORT).href);

  const desktop = await evaluate(cdp, `(async () => {
    const header = document.querySelector(".topbar");
    const target = document.querySelectorAll(".theme-group")[2];
    const link = document.querySelector('.theme-navigation a[href="#' + target.id + '"]');
    scrollTo(0, 0);
    link.click();
    await new Promise((resolvePromise) => requestAnimationFrame(() => requestAnimationFrame(resolvePromise)));
    const headerRect = header.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    return {
      headerBottom: headerRect.bottom,
      headerPosition: getComputedStyle(header).position,
      scrollMarginTop: parseFloat(getComputedStyle(target).scrollMarginTop),
      targetTop: targetRect.top,
      visibleBelowHeader: targetRect.top >= headerRect.bottom,
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
  await navigate(cdp, pathToFileURL(REPORT).href);
  const mobile = await evaluate(cdp, `(async () => {
    const header = document.querySelector(".topbar");
    const target = document.querySelectorAll(".theme-group")[4];
    const link = document.querySelector('.theme-navigation a[href="#' + target.id + '"]');
    scrollTo(0, 0);
    link.click();
    await new Promise((resolvePromise) => requestAnimationFrame(() => requestAnimationFrame(resolvePromise)));
    return {
      headerPosition: getComputedStyle(header).position,
      scrollMarginTop: parseFloat(getComputedStyle(target).scrollMarginTop),
      targetTop: target.getBoundingClientRect().top,
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    };
  })()`);

  const failures = [];
  if (desktop.headerPosition !== "sticky") failures.push("desktop header is not sticky");
  if (desktop.scrollMarginTop < 72 || desktop.scrollMarginTop > 80) {
    failures.push(`desktop theme scroll margin ${desktop.scrollMarginTop}px is outside 72-80px`);
  }
  if (!desktop.visibleBelowHeader) {
    failures.push(`desktop anchor top ${desktop.targetTop}px is hidden by header bottom ${desktop.headerBottom}px`);
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
  if (mobile.headerPosition !== "static" || mobile.scrollMarginTop !== 0) {
    failures.push(
      `mobile reset is wrong: header=${mobile.headerPosition}, scrollMargin=${mobile.scrollMarginTop}px`,
    );
  }
  if (mobile.scrollWidth > mobile.clientWidth) {
    failures.push(`mobile page overflows: ${mobile.scrollWidth}px > ${mobile.clientWidth}px`);
  }
  if (browserProblems.length) failures.push(`browser console: ${browserProblems.join(" | ")}`);

  console.log(JSON.stringify({ desktop, contrast, print, mobile, browserProblems }, null, 2));
  if (failures.length) throw new Error(failures.join("\n"));
  console.log("PASS: desktop anchors, print appendix, contrast, and mobile reset");
} finally {
  cdp?.close();
  if (chrome && chrome.exitCode === null) {
    chrome.kill("SIGTERM");
    await Promise.race([
      new Promise((resolvePromise) => chrome.once("exit", resolvePromise)),
      new Promise((resolvePromise) => setTimeout(resolvePromise, 2000)),
    ]);
  }
  await rm(profile, { recursive: true, force: true });
}
