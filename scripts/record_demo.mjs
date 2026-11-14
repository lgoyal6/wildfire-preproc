import { mkdir, rm, writeFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const url = process.argv[2] || "http://127.0.0.1:4173/?demo=record&delay=0";
const outDir = process.argv[3] || "/private/tmp/agrishield-video-frames";
const seconds = Number(process.argv[4] || 21);
const fps = Number(process.argv[5] || 8);
const width = Number(process.argv[6] || 1440);
const height = Number(process.argv[7] || 900);
const mode = process.argv[8] || "auto";
const port = Number(process.env.CHROME_DEBUG_PORT || 9223);
const userDataDir = `/private/tmp/agrishield-chrome-profile-${process.pid}`;

function cdpCall(socket, method, params = {}) {
  const id = ++cdpCall.nextId;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    cdpCall.pending.set(id, { resolve, reject });
  });
}
cdpCall.nextId = 0;
cdpCall.pending = new Map();

async function fetchJsonWithRetry(endpoint, attempts = 80) {
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(endpoint);
      if (response.ok) return response.json();
    } catch {
      // Chrome may still be booting.
    }
    await sleep(125);
  }
  throw new Error(`Could not read ${endpoint}`);
}

async function connectToPage() {
  const targets = await fetchJsonWithRetry(`http://127.0.0.1:${port}/json/list`);
  const page = targets.find((target) => target.type === "page") || targets[0];
  if (!page?.webSocketDebuggerUrl) throw new Error("Chrome did not expose a page target");

  const socket = new WebSocket(page.webSocketDebuggerUrl);
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (!message.id) return;
    const pending = cdpCall.pending.get(message.id);
    if (!pending) return;
    cdpCall.pending.delete(message.id);
    if (message.error) pending.reject(new Error(message.error.message));
    else pending.resolve(message.result || {});
  });
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  return socket;
}

async function main() {
  await rm(outDir, { recursive: true, force: true });
  await mkdir(outDir, { recursive: true });

  const chrome = spawn(chromePath, [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    `--window-size=${width},${height}`,
    "--hide-scrollbars",
    "--force-device-scale-factor=1",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-sync",
    "--no-first-run",
    url,
  ]);

  chrome.stderr.on("data", (chunk) => {
    const text = String(chunk);
    if (!text.includes("DevTools listening")) process.stderr.write(text);
  });

  try {
    const socket = await connectToPage();
    await cdpCall(socket, "Page.enable");
    await cdpCall(socket, "Runtime.enable");
    await cdpCall(socket, "Emulation.setDeviceMetricsOverride", {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await sleep(1200);
    if (mode === "showcase") {
      await cdpCall(socket, "Runtime.evaluate", {
        expression: `
          (() => {
            runDemoSimulation();
            setView("setup");
            window.__agrishieldShowcase = [
              [1800, () => setView("baseline")],
              [7400, () => setSpreadMode("protected")],
              [8200, () => setView("firebreak")],
              [14500, () => setView("report")],
              [20500, () => setView("compare")],
              [26500, () => setView("alerts")],
              [31500, () => setView("setup")]
            ];
            window.__agrishieldShowcase.forEach(([delay, fn]) => window.setTimeout(fn, delay));
          })();
        `,
      });
    }
    if (mode === "guided") {
      await cdpCall(socket, "Runtime.evaluate", {
        expression: `
          (() => {
            const origin = { lon: -116.945, lat: 33.035 };
            const parcel = [
              { lon: -116.9532, lat: 33.0392 },
              { lon: -116.9388, lat: 33.0384 },
              { lon: -116.9366, lat: 33.0286 },
              { lon: -116.9511, lat: 33.0269 },
            ];
            const assetPlan = [
              ["barn", 300, 260],
              ["high_value_crop", 80, 310],
              ["livestock", 170, 360],
              ["water", 325, 520],
              ["road", 250, 470],
            ];
            const updateSelect = (id, value) => {
              const el = document.querySelector("#" + id);
              if (!el) return;
              el.value = value;
              el.dispatchEvent(new Event("input", { bubbles: true }));
            };
            const updateRange = (id, value) => updateSelect(id, String(value));

            clearLocationWorkspace();
            setMapCenter(origin.lon, origin.lat);
            setView("setup");
            document.querySelector("#locationSearch").value = "Ramona, CA farm parcel";
            els.quickTask.textContent = "Select farm parcel";
            els.quickDetail.textContent = "Trace the parcel boundary, then add operational attributes.";
            els.mapHint.textContent = "Drawing parcel boundary";
            updatePanels();
            drawAll();

            parcel.forEach((point, index) => {
              window.setTimeout(() => {
                state.polygon.push(point);
                updatePanels();
                drawAll();
                els.mapHint.textContent = "Parcel point " + (index + 1) + " added";
              }, 1400 + index * 900);
            });

            window.setTimeout(() => {
              updateSelect("cropType", "grapes");
              updateSelect("harvestWindow", "week");
              updateSelect("livestockCount", "large");
              updateSelect("irrigationStatus", "available");
              updateRange("crewSize", 14);
              els.quickTask.textContent = "Set farm attributes";
              els.quickDetail.textContent = "Crop, harvest timing, livestock, irrigation, and crew size update the advisory.";
              updatePanels();
              drawAll();
            }, 5600);

            assetPlan.forEach(([type, bearing, distance], index) => {
              window.setTimeout(() => {
                state.assets.push({ type, point: pointAtBearing(polygonCentroid(state.polygon), bearing, distance) });
                els.quickTask.textContent = "Add key assets";
                els.quickDetail.textContent = "Barns, crops, livestock, roads, and water points affect the plan.";
                els.mapHint.textContent = "Added " + assetMeta(type).label;
                updatePanels();
                drawAll();
              }, 8200 + index * 900);
            });

            window.setTimeout(() => {
              runDemoSimulation();
              setView("baseline");
            }, 13400);
            window.setTimeout(() => setSpreadMode("protected"), 22500);
            window.setTimeout(() => setView("firebreak"), 24200);
            window.setTimeout(() => setView("report"), 33500);
            window.setTimeout(() => setView("compare"), 44500);
            window.setTimeout(() => setView("alerts"), 53500);
            window.setTimeout(() => setView("setup"), 61500);
          })();
        `,
      });
    }
    if (mode === "pitch") {
      await cdpCall(socket, "Runtime.evaluate", {
        expression: `
          (() => {
            const origin = { lon: -116.945, lat: 33.035 };
            const parcel = [
              { lon: -116.9532, lat: 33.0392 },
              { lon: -116.9388, lat: 33.0384 },
              { lon: -116.9366, lat: 33.0286 },
              { lon: -116.9511, lat: 33.0269 },
            ];
            const assets = [
              ["barn", 300, 260],
              ["high_value_crop", 80, 310],
              ["livestock", 170, 360],
              ["water", 325, 520],
              ["road", 250, 470],
            ];
            const updateSelect = (id, value) => {
              const el = document.querySelector("#" + id);
              if (!el) return;
              el.value = value;
              el.dispatchEvent(new Event("input", { bubbles: true }));
            };
            clearLocationWorkspace();
            setMapCenter(origin.lon, origin.lat);
            setView("setup");
            document.querySelector("#locationSearch").value = "Ramona, CA farm parcel";
            updateSelect("cropType", "grapes");
            updateSelect("harvestWindow", "week");
            updateSelect("livestockCount", "large");
            updateSelect("irrigationStatus", "available");
            updateSelect("crewSize", "14");
            els.quickTask.textContent = "AgriShield fire-safe farm planning";
            els.quickDetail.textContent = "Plan before wildfire season: parcel, assets, risk, buffers, and field actions.";
            updatePanels();
            drawAll();

            parcel.forEach((point, index) => {
              window.setTimeout(() => {
                state.polygon.push(point);
                els.quickTask.textContent = "Draw farm boundary";
                els.quickDetail.textContent = "The parcel boundary defines the simulation target.";
                updatePanels();
                drawAll();
              }, 5400 + index * 650);
            });

            assets.forEach(([type, bearing, distance], index) => {
              window.setTimeout(() => {
                state.assets.push({ type, point: pointAtBearing(polygonCentroid(state.polygon), bearing, distance) });
                els.quickTask.textContent = "Add farm assets";
                els.quickDetail.textContent = "Barns, water, roads, livestock, and crops change priorities.";
                updatePanels();
                drawAll();
              }, 8800 + index * 620);
            });

            window.setTimeout(() => {
              runDemoSimulation();
              setView("baseline");
            }, 12400);
            window.setTimeout(() => {
              state.overlays.fuel = true;
              state.overlays.edge = true;
              document.querySelector("#overlayFuel").checked = true;
              document.querySelector("#overlayEdge").checked = true;
              els.quickTask.textContent = "Show risk overlay";
              els.quickDetail.textContent = "Fuel, wildland edge, weather, and asset exposure rank fire paths.";
              updatePanels();
              drawAll();
            }, 17800);
            window.setTimeout(() => {
              setView("firebreak");
            }, 22500);
            window.setTimeout(() => {
              updateSelect("protectionMode", "low");
              state.optimization = null;
              setSpreadMode("protected");
              setView("firebreak");
              els.quickTask.textContent = "Low disruption plan";
              els.quickDetail.textContent = "Minimal changes preserve farm operations.";
              updatePanels();
              drawAll();
            }, 27000);
            window.setTimeout(() => {
              updateSelect("protectionMode", "maximum");
              state.optimization = null;
              setSpreadMode("protected");
              setView("firebreak");
              els.quickTask.textContent = "Maximum protection plan";
              els.quickDetail.textContent = "More buffers reduce risk where disruption is acceptable.";
              updatePanels();
              drawAll();
            }, 31500);
            window.setTimeout(() => {
              setView("setup");
              state.overlays.fuel = false;
              state.overlays.edge = false;
              document.querySelector("#overlayFuel").checked = false;
              document.querySelector("#overlayEdge").checked = false;
              updatePanels();
              drawAll();
            }, 36000);
            window.setTimeout(() => {
              setView("report");
              els.quickTask.textContent = "Plain-language recommendation";
              els.quickDetail.textContent = "The same model becomes a field-ready plan.";
              updatePanels();
              drawAll();
            }, 41000);
            window.setTimeout(() => {
              setView("alerts");
              els.quickTask.textContent = "City-planning use case";
              els.quickDetail.textContent = "The same workflow can prioritize buffers, water, and access near WUI parcels.";
              updatePanels();
              drawAll();
            }, 46500);
          })();
        `,
      });
    }

    const totalFrames = Math.round(seconds * fps);
    const intervalMs = 1000 / fps;
    const startedAt = performance.now();
    for (let i = 0; i < totalFrames; i += 1) {
      const targetTime = startedAt + i * intervalMs;
      const waitMs = targetTime - performance.now();
      if (waitMs > 0) await sleep(waitMs);
      const result = await cdpCall(socket, "Page.captureScreenshot", {
        format: "jpeg",
        quality: 84,
        fromSurface: true,
        captureBeyondViewport: false,
      });
      const frameName = `${String(i + 1).padStart(5, "0")}.jpg`;
      await writeFile(`${outDir}/${frameName}`, Buffer.from(result.data, "base64"));
      if ((i + 1) % fps === 0) {
        process.stdout.write(`captured ${Math.round((i + 1) / fps)}s / ${seconds}s\n`);
      }
    }
    socket.close();
  } finally {
    chrome.kill("SIGTERM");
    await sleep(1000);
    await rm(userDataDir, { recursive: true, force: true, maxRetries: 6, retryDelay: 250 });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
