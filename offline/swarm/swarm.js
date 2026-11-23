"use strict";
/* TMRDS offline specialist-app communication: local HTTP JSON plus in-page
 * CustomEvents; no WebSocket, remote LLM, cloud storage, or patient input.
 */
const $ = (id) => document.getElementById(id);
const nodeName = document.body.dataset.node || "all";
const bus = new EventTarget();
const nodes = new Set(["labs","imaging","genomics","evidence","drug_discovery","quantum","knowledge","supervisor"]);
const scenarios = new Set(["synthetic_all","synthetic_lab","synthetic_genomics"]);

function item(tag, text, cls) {
  const el = document.createElement(tag);
  el.textContent = text;
  if (cls) el.className = cls;
  return el;
}

async function getLocalJson(path, options = {}) {
  if (!path.startsWith("/api/local/")) throw new Error("Local path only");
  const response = await fetch(path, {
    credentials: "omit", cache: "no-store", redirect: "error",
    ...options,
  });
  if (!response.ok || !response.headers.get("Content-Type")?.includes("application/json")) {
    throw new Error("Offline specialist API unavailable");
  }
  const body = await response.json();
  if (!body || body.schema_version !== "1.0") {
    throw new Error("Unexpected offline specialist contract");
  }
  return body;
}

function renderCapability(capability) {
  $("capabilities").replaceChildren();
  const list = document.createElement("dl");
  const rows = [
    ["Network", capability.offline === true ? "Air-gapped / no online calls" : "NOT VERIFIED"],
    ["Data boundary", capability.patient_data_accepted === false ? "Built-in synthetic fixtures only" : "NOT VERIFIED"],
    ["Clinical recommendation", capability.automated_diagnosis === false ? "Disabled" : "NOT VERIFIED"],
    ["Quantum device", capability.quantum_hardware_enabled === false ? "Not connected" : "NOT VERIFIED"],
    ["Model weights", capability.clinical_model_weights_bundled === false ? "Not bundled" : "NOT VERIFIED"],
  ];
  for (const [key,value] of rows) {
    list.append(item("dt",key),item("dd",value));
  }
  $("capabilities").append(list);
}

function renderResult(msg) {
  if (!msg || msg.schema_version !== "1.0" || msg.offline !== true ||
      msg.patient_data_accepted !== false || !Array.isArray(msg.events) ||
      !msg.nodes || typeof msg.receipt_sha256 !== "string") {
    throw new Error("Untrusted local swarm result");
  }
  const root = $("results");
  root.replaceChildren();
  const show = nodeName === "all" ? [...nodes] : [nodeName];
  for (const name of show) {
    const value = msg.nodes[name];
    if (!value || typeof value.status !== "string") continue;
    const card = document.createElement("article");
    card.className = "node-card";
    card.append(item("h3",name.replaceAll("_"," ")), item("p","State: " + value.status));
    const meta = document.createElement("pre");
    meta.textContent = JSON.stringify(value, null, 2);
    card.append(meta);root.append(card);
  }
  root.append(item("p","Receipt SHA-256 of synthetic result: " + msg.receipt_sha256, "receipt"));
  for (const event of msg.events) {
    if (event.channel !== "tmrds.offline.node.v1" || !nodes.has(event.node) ||
        event.data_class !== "synthetic_nonidentifying") continue;
    bus.dispatchEvent(new CustomEvent("tmrds:node", {detail:event}));
  }
}

bus.addEventListener("tmrds:node", (event) => {
  const current = event.detail;
  if (current.node === "supervisor") {
    $("execution").textContent = "All local specialist messages processed. Human review required. No diagnosis or treatment generated.";
  }
});

async function boot() {
  const connection = $("connection");
  try {
    const caps = await getLocalJson("/api/local/capabilities");
    if (caps.mode !== "loopback_only" || caps.offline !== true ||
        caps.public_patient_upload_enabled !== false || caps.human_authority_final !== true) {
      throw new Error("Local offline boundary not verified");
    }
    if (nodeName !== "all" && !nodes.has(nodeName)) throw new Error("Unknown specialist node");
    renderCapability(caps);
    connection.textContent = "Local-only Python coordinator ready · no external provider or clinical record connected";
    $("run").disabled = false;
  } catch (_) {
    $("run").disabled = true;
    connection.textContent = "Coordinator unavailable. Start the local server using the repository runbook; do not enter patient data.";
  }
}

$("run").disabled = true;
$("run").addEventListener("click", async () => {
  const selected = $("scenario").value;
  if (!scenarios.has(selected)) {
    $("execution").textContent = "Invalid synthetic scenario";
    return;
  }
  $("run").disabled = true;
  $("execution").textContent = "Running local synthetic specialist modules…";
  try {
    const body = await getLocalJson("/api/local/run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-TMRDS-Local-Only": "synthetic-demo",
      },
      body: JSON.stringify({scenario: selected}),
    });
    renderResult(body);
  } catch (_) {
    $("execution").textContent = "Local runtime or result contract unavailable; no inference performed.";
  } finally {
    $("run").disabled = false;
  }
});
void boot();
