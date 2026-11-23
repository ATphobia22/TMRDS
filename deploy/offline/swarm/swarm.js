"use strict";
/* All messages remain on loopback. No file uploads, model prompts or PHI fields. */
const node = document.body.dataset.node || "overview";
const $ = id => document.getElementById(id);
let requestId = 0;
const actions = Object.freeze({
  overview: ["swarm.run"],
  lab: ["lab.synthetic_demo"],
  imaging: ["imaging.synthetic_demo"],
  molecular: ["molecular.descriptors"],
  quantum: ["quantum.grover"],
  evidence: ["evidence.offline_status"],
  review: ["governance.review"]
});
const allow = new Set(actions[node] || []);
async function rpc(method, params = {}) {
  if (!(allow.has(method) || method === "swarm.capabilities")) throw Error("Node action forbidden");
  const data = {jsonrpc:"2.0", id:++requestId, method, params};
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 16000);
  try {
    const response = await fetch("/rpc", {
      method:"POST", headers:{"Content-Type":"application/json"},
      credentials:"omit", mode:"same-origin", cache:"no-store",
      body:JSON.stringify(data), signal:controller.signal
    });
    if (!response.ok) throw Error("Local coordinator refused this request");
    const result = await response.json();
    if (result.jsonrpc !== "2.0" || result.id !== data.id ||
        (!!result.error === !!result.result)) throw Error("Invalid JSON-RPC contract");
    if (result.error) throw Error(String(result.error.message || "Local scientific adapter unavailable").slice(0,150));
    return result.result;
  } finally { clearTimeout(timeout); }
}
function render(out) {
  $("output").textContent = JSON.stringify(out, null, 2);
  $("status").textContent = "Local operation completed; review evidence limitations below.";
}
async function operate(button) {
  const method = button.dataset.action;
  const params = {};
  if (method === "molecular.descriptors") params.smiles = $("smiles").value.trim();
  if (method === "quantum.grover") params.scenario = $("scenario").value;
  button.disabled = true;
  $("status").textContent = "Running real local adapter or bounded mathematical model…";
  try { render(await rpc(method, params)); }
  catch (_e) { $("status").textContent = "Local adapter unavailable or request refused; no clinical result inferred."; $("output").textContent = ""; }
  finally { button.disabled = false; }
}
document.querySelectorAll("button[data-action]").forEach(button =>
  button.addEventListener("click", () => void operate(button)));
const check = $("capabilities");
if (check) check.addEventListener("click", async () => {
  check.disabled = true;
  $("status").textContent = "Checking actually installed local packages…";
  try { render(await rpc("swarm.capabilities")); }
  catch (_e) { $("status").textContent = "Local workstation unavailable."; }
  finally {check.disabled=false;}
});
