// Real browser driver for LLMTier UI tests — CDP over the built-in WebSocket.
//
// No npm dependency is required: Node >= 22 ships a global `WebSocket`, and the
// Chrome DevTools Protocol is spoken directly. A browser is launched from an
// explicit executable path (env `LLMTIER_BROWSER`, else a cached Chrome /
// chrome-headless-shell), so nothing is downloaded at test time.
//
// Usage: node browser_driver.mjs --config <scenario.json>
//
// The scenario JSON describes one hermetic UI case:
//   { "baseUrl": "http://127.0.0.1:<port>", "path": "/ui/", "screenshot": "<abs>",
//     "networkLog": "<abs|optional>", "steps": [ ... ] }
//
// Every step is one of the primitives below; the driver prints a single JSON
// result object on stdout and exits non-zero on a driver/protocol failure.
// Assertions live in the scenario (`assert*` steps) so the Python side only has
// to read the JSON verdict — real DOM state, not source strings.

import { spawn } from "node:child_process";
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const DEFAULT_CHROME_CANDIDATES = [
  process.env.LLMTIER_BROWSER,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  path.join(os.homedir(), ".cache/puppeteer/chrome/mac-1108766/chrome-mac/Chromium.app/Contents/MacOS/Chromium"),
  path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell"),
].filter(Boolean);

function resolveBrowser() {
  for (const candidate of DEFAULT_CHROME_CANDIDATES) {
    try { if (fs.existsSync(candidate)) return candidate; } catch { /* ignore */ }
  }
  throw new Error(`no browser executable found; set LLMTIER_BROWSER (tried: ${DEFAULT_CHROME_CANDIDATES.join(", ")})`);
}

function arg(name, fallback = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback;
}

function httpGetJSON(port, p) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host: "127.0.0.1", port, path: p }, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => {
        try { resolve(JSON.parse(data)); } catch (e) { reject(new Error(`bad JSON from ${p}: ${data.slice(0, 120)}`)); }
      });
    });
    req.on("error", reject);
  });
}

async function freePort() {
  const net = await import("node:net");
  return await new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const p = srv.address().port;
      srv.close(() => resolve(p));
    });
  });
}

class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.listeners = []; }

  static async connect(url) {
    const ws = new WebSocket(url);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
    const cdp = new CDP(ws);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && cdp.pending.has(msg.id)) {
        const { resolve, reject } = cdp.pending.get(msg.id);
        cdp.pending.delete(msg.id);
        if (msg.error) reject(new Error(`${msg.error.message} (${msg.error.code})`));
        else resolve(msg.result);
      } else {
        for (const l of cdp.listeners) l(msg);
      }
    };
    return cdp;
  }

  send(method, params = {}, sessionId) {
    const id = ++this.id;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify(payload));
    });
  }

  on(fn) { this.listeners.push(fn); }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Read a JSON file produced by the Python test into the scenario if needed.
async function main() {
  const configPath = arg("--config");
  if (!configPath) throw new Error("--config <scenario.json> is required");
  const scenario = JSON.parse(fs.readFileSync(configPath, "utf8"));
  const browser = resolveBrowser();
  const port = await freePort();
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "llmtier-ui-chrome-"));

  const proc = spawn(browser, [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--disable-extensions",
    "--mute-audio",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  const result = { ok: false, browser, steps: [], failures: [], network: [], consoleErrors: [], screenshots: [], _screenshotPath: scenario.screenshot || null };
  let cdp = null;
  let sessionId = null;
  let browserWs = null;
  try {
    let version = null;
    for (let i = 0; i < 80; i++) {
      try { version = await httpGetJSON(port, "/json/version"); break; } catch { await sleep(150); }
    }
    if (!version) throw new Error(`browser did not expose CDP on port ${port}`);
    result.browser = version.Browser;

    browserWs = await CDP.connect(version.webSocketDebuggerUrl);
    const target = await browserWs.send("Target.createTarget", { url: "about:blank" });
    const attached = await browserWs.send("Target.attachToTarget", { targetId: target.targetId, flatten: true });
    sessionId = attached.sessionId;

    await browserWs.send("Page.enable", {}, sessionId);
    await browserWs.send("Runtime.enable", {}, sessionId);
    await browserWs.send("Network.enable", {}, sessionId);

    // Record every API request/response so the Python side can assert that a UI
    // action actually produced the expected API call.
    const requestMeta = new Map();
    browserWs.on((msg) => {
      if (msg.sessionId !== sessionId) return;
      if (msg.method === "Network.requestWillBeSent") {
        const r = msg.params.request;
        requestMeta.set(msg.params.requestId, { url: r.url, method: r.method, type: msg.params.type, headers: r.headers });
      } else if (msg.method === "Network.responseReceived") {
        const meta = requestMeta.get(msg.params.requestId) || {};
        result.network.push({ url: msg.params.response.url, method: meta.method, status: msg.params.response.status, type: meta.type, headers: meta.headers });
      } else if (msg.method === "Runtime.consoleAPICalled") {
        if (msg.params.type === "error") result.consoleErrors.push(msg.params.args.map((a) => a.value ?? a.description ?? "").join(" "));
      } else if (msg.method === "Runtime.exceptionThrown") {
        result.consoleErrors.push(msg.params.exceptionDetails?.exception?.description || "uncaught exception");
      }
    });

    const pageUrl = scenario.baseUrl.replace(/\/$/, "") + (scenario.path || "/ui/");
    await browserWs.send("Page.navigate", { url: pageUrl }, sessionId);

    // Wait for the app's initial render to settle (network idle-ish + a tick).
    await waitForReady(browserWs, sessionId, scenario.readyExpression);

    const shots = [];
    for (const step of scenario.steps || []) {
      const record = { action: step.action };
      try {
        const value = await runStep(browserWs, sessionId, step, result, shots);
        record.ok = true;
        if (value !== undefined) record.value = value;
      } catch (e) {
        record.ok = false;
        record.error = String(e.message || e);
        result.failures.push({ action: step.action, error: record.error });
      }
      result.steps.push(record);
    }

    if (scenario.screenshot) {
      const shot = await browserWs.send("Page.captureScreenshot", { format: "png" }, sessionId);
      fs.mkdirSync(path.dirname(scenario.screenshot), { recursive: true });
      fs.writeFileSync(scenario.screenshot, Buffer.from(shot.data, "base64"));
      result.screenshot = scenario.screenshot;
    }
    result.screenshots = shots;
    if (scenario.networkLog) {
      fs.mkdirSync(path.dirname(scenario.networkLog), { recursive: true });
      fs.writeFileSync(scenario.networkLog, JSON.stringify(result.network, null, 2));
    }
    result.ok = result.failures.length === 0;
  } catch (e) {
    result.failures.push({ action: "driver", error: String(e.message || e) });
    result.ok = false;
  } finally {
    try { if (browserWs) browserWs.ws.close(); } catch { /* ignore */ }
    try { proc.kill("SIGKILL"); } catch { /* ignore */ }
    try { fs.rmSync(userDataDir, { recursive: true, force: true }); } catch { /* ignore */ }
  }

  process.stdout.write(JSON.stringify(result));
  process.exit(result.ok ? 0 : 0); // always exit 0; the JSON carries the verdict
}

async function waitForReady(cdp, sessionId, readyExpression) {
  const expr = readyExpression || "document.readyState === 'complete'";
  for (let i = 0; i < 100; i++) {
    const r = await cdp.send("Runtime.evaluate", { expression: expr, returnByValue: true }, sessionId);
    if (r.result && r.result.value === true) { await sleep(200); return; }
    await sleep(100);
  }
  throw new Error(`page not ready (waited for: ${expr})`);
}

async function evaluate(cdp, sessionId, expression) {
  const r = await cdp.send("Runtime.evaluate", {
    expression, returnByValue: true, awaitPromise: true,
  }, sessionId);
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || "evaluate threw");
  return r.result?.value;
}

async function runStep(cdp, sessionId, step, result, shots = []) {
  switch (step.action) {
    case "wait": await sleep(step.ms || 100); return;
    case "waitFor": {
      for (let i = 0; i < (step.timeoutMs ? step.timeoutMs / 100 : 100); i++) {
        if (await evaluate(cdp, sessionId, step.expression)) return true;
        await sleep(100);
      }
      throw new Error(`waitFor timed out: ${step.expression}`);
    }
    case "screenshot": {
      if (!result._screenshotPath) throw new Error("screenshot step requires a scenario screenshot path");
      const base = path.basename(result._screenshotPath, path.extname(result._screenshotPath));
      const dir = path.dirname(result._screenshotPath);
      const labeled = `${base}.${step.name || "step"}.png`;
      const out = path.join(dir, labeled);
      const shot = await cdp.send("Page.captureScreenshot", { format: "png" }, sessionId);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(out, Buffer.from(shot.data, "base64"));
      shots.push(out);
      return out;
    }
    case "click": {
      const ok = await evaluate(cdp, sessionId, `(()=>{const el=document.querySelector(${JSON.stringify(step.selector)});if(!el)return false;el.click();return true;})()`);
      if (!ok) throw new Error(`click: selector not found: ${step.selector}`);
      await sleep(step.settleMs || 250);
      return true;
    }
    case "submit": {
      const ok = await evaluate(cdp, sessionId, `(()=>{const f=document.querySelector(${JSON.stringify(step.selector)});if(!f)return false;f.requestSubmit?f.requestSubmit():f.dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}));return true;})()`);
      if (!ok) throw new Error(`submit: form not found: ${step.selector}`);
      await sleep(step.settleMs || 250);
      return true;
    }
    case "fill": {
      const ok = await evaluate(cdp, sessionId, `(()=>{const el=document.querySelector(${JSON.stringify(step.selector)});if(!el)return false;el.value=${JSON.stringify(step.value)};el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));return true;})()`);
      if (!ok) throw new Error(`fill: field not found: ${step.selector}`);
      await sleep(step.settleMs || 100);
      return true;
    }
    case "setCheckbox": {
      const ok = await evaluate(cdp, sessionId, `(()=>{const el=document.querySelector(${JSON.stringify(step.selector)});if(!el)return false;el.checked=${step.checked ? "true" : "false"};el.dispatchEvent(new Event('change',{bubbles:true}));return true;})()`);
      if (!ok) throw new Error(`setCheckbox: field not found: ${step.selector}`);
      await sleep(step.settleMs || 250);
      return true;
    }
    case "eval": return await evaluate(cdp, sessionId, step.expression);
    case "assert": {
      const value = await evaluate(cdp, sessionId, step.expression);
      const pass = compare(value, step.op || "equals", step.expected);
      if (!pass) throw new Error(`assert failed: ${step.expression} => ${JSON.stringify(value)} ${step.op || "equals"} ${JSON.stringify(step.expected)}`);
      return value;
    }
    case "assertText": {
      const text = await evaluate(cdp, sessionId, `(document.querySelector(${JSON.stringify(step.selector)})?.textContent||"")`);
      if (!text.includes(step.contains)) throw new Error(`assertText failed: ${step.selector} missing ${JSON.stringify(step.contains)} (got ${JSON.stringify(text.slice(0, 160))})`);
      return text;
    }
    case "assertVisibleSection": {
      const active = await evaluate(cdp, sessionId, `(document.querySelector('.page.active')?.id||"")`);
      if (active !== step.expected) throw new Error(`active page is ${JSON.stringify(active)}, expected ${JSON.stringify(step.expected)}`);
      return active;
    }
    case "assertNetwork": {
      const matches = result.network.filter((n) => n.url.includes(step.urlContains) && (!step.method || n.method === step.method));
      const ok = step.status ? matches.some((n) => n.status === step.status) : matches.length > 0;
      if (!ok) throw new Error(`assertNetwork failed: no ${step.method || "*"} ${step.urlContains}${step.status ? ` -> ${step.status}` : ""}; saw ${JSON.stringify(result.network.map((n) => `${n.method} ${n.url} ${n.status}`))}`);
      return matches.length;
    }
    case "waitForNetwork": {
      // Deterministic replacement for a fixed sleep: poll the CDP network log
      // until the expected request/response is observed (or time out).
      const deadline = Date.now() + (step.timeoutMs || 10000);
      for (;;) {
        const matches = result.network.filter((n) => n.url.includes(step.urlContains) && (!step.method || n.method === step.method) && (!step.status || n.status === step.status));
        if (matches.length >= (step.atLeast || 1)) return matches.length;
        if (Date.now() >= deadline) {
          throw new Error(`waitForNetwork timed out: ${step.method || "*"} ${step.urlContains}${step.status ? ` -> ${step.status}` : ""}; saw ${JSON.stringify(result.network.map((n) => `${n.method} ${n.url} ${n.status}`))}`);
        }
        await sleep(100);
      }
    }
    case "assertNetworkCount": {
      const matches = result.network.filter((n) => n.url.includes(step.urlContains) && (!step.method || n.method === step.method));
      if (matches.length !== step.count) throw new Error(`assertNetworkCount failed: ${step.method || "*"} ${step.urlContains} seen ${matches.length}, expected ${step.count}; saw ${JSON.stringify(matches.map((n) => `${n.method} ${n.url}`))}`);
      return matches.length;
    }
    case "assertNoNetwork": {
      const matches = result.network.filter((n) => n.url.includes(step.urlContains) && (!step.method || n.method === step.method));
      if (matches.length) throw new Error(`assertNoNetwork failed: saw ${JSON.stringify(matches.map((n) => `${n.method} ${n.url}`))}`);
      return 0;
    }
    case "assertRequestHeader": {
      const matches = result.network.filter((n) => n.url.includes(step.urlContains) && (!step.method || n.method === step.method));
      const headerName = step.header.toLowerCase();
      const seen = matches.map((n) => Object.entries(n.headers || {}).find(([k]) => k.toLowerCase() === headerName)?.[1]).filter(Boolean);
      if (!seen.some((v) => (step.matches ? new RegExp(step.matches).test(v) : v === step.value))) {
        throw new Error(`assertRequestHeader failed: ${step.method || "*"} ${step.urlContains} header ${step.header} not ${step.matches ? `matching ${step.matches}` : `== ${step.value}`} (saw ${JSON.stringify(seen)})`);
      }
      return seen.length;
    }
    default: throw new Error(`unknown step action: ${step.action}`);
  }
}

function compare(value, op, expected) {
  if (op === "equals") return JSON.stringify(value) === JSON.stringify(expected);
  if (op === "notEquals") return JSON.stringify(value) !== JSON.stringify(expected);
  if (op === "includes") return Array.isArray(value) ? value.includes(expected) : String(value).includes(String(expected));
  if (op === "truthy") return !!value;
  if (op === "falsy") return !value;
  if (op === "gte") return Number(value) >= Number(expected);
  if (op === "matches") return new RegExp(expected).test(String(value));
  throw new Error(`unknown op: ${op}`);
}

main().catch((e) => {
  process.stdout.write(JSON.stringify({ ok: false, failures: [{ action: "driver", error: String(e.message || e) }] }));
  process.exit(0);
});
