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
        !["synthetic_nonidentifying", "public_citation_metadata"].includes(event.data_class)) continue;
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
/* Public citation-only cache search: fixed localhost endpoint, zero external
 * requests, no HTML interpretation, and no patient or full-text upload.
 */
if (nodeName === "evidence") {
  const form = $("evidenceSearchForm");
  const button = $("evidenceSearchBtn");
  const status = $("evidenceSearchStatus");
  const root = $("evidenceSearchResults");
  if (form && button && status && root) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const term = $("evidenceSearchTerm").value.trim();
      const validDoi = term.startsWith("10.") && term.indexOf("/") > 3;
      if (term.length < 2 || term.length > 80 || term.includes("@") ||
          (term.includes("/") && !validDoi) || term.includes("\\\\") || term.includes("..")) {
        status.textContent = "Enter only a public biomedical topic or source identifier; no patient data.";
        return;
      }
      button.disabled = true;
      status.textContent = "Searching verified local citation pack without Internet…";
      root.replaceChildren();
      try {
        const result = await getLocalJson("/api/local/evidence-search", {
          method: "POST",
          headers: {"Content-Type": "application/json", "X-TMRDS-Local-Only": "public-citation-query"},
          body: JSON.stringify({term}),
        });
        if (result.search_executed_online !== false || !Array.isArray(result.matches) ||
            !Number.isInteger(result.match_count)) throw new Error("Unexpected local evidence contract");
        status.textContent = "Local source: " + result.status +
          (result.freshness ? " · " + result.freshness : "") +
          " · " + result.match_count + " citation matches (not independent clinical confirmation).";
        for (const record of result.matches.slice(0, 20)) {
          const card = document.createElement("article");
          card.className = "node-card";
          card.append(item("h3", String(record.title || "Untitled public citation").slice(0, 350)));
          card.append(item("p", String(record.source || "source") + " · " +
            String(record.pmid || record.doi || record.pmcid || record.nct_id || record.stable_id || "no public identifier")));
          root.append(card);
        }
        if (!result.matches.length) root.append(item("p", "No records in this limited local cache. This does not mean no research exists."));
      } catch (_) {
        status.textContent = "Verified offline citation lookup unavailable; no scientific result inferred.";
      } finally {
        button.disabled = false;
      }
    });
  }
}

void boot();
