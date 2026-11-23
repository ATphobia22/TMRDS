"use strict";
/* Public-only, read-only source queries. Do not accept PHI or use returned data for clinical decisions. */
const $ = (id) => document.getElementById(id);
const FORM = $("searchForm");
const BUTTON = $("searchBtn");
let requestSequence = 0;

function node(tag, cls, value) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (value !== undefined && value !== null) n.textContent = String(value);
  return n;
}
function setStatus(prefix, state, message) {
  $(prefix + "Dot").className = "status-mark " + state;
  $(prefix + "Status").textContent = message;
}
function clearResults(target, message) {
  $(target).replaceChildren(node("p", "empty", message));
}
async function sha256(value) {
  if (!globalThis.crypto || !crypto.subtle) return "unavailable (SubtleCrypto unsupported)";
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}
async function getJson(url, timeoutMs = 12000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      method: "GET", mode: "cors", credentials: "omit",
      cache: "no-store", referrerPolicy: "no-referrer", signal: controller.signal,
      headers: { "Accept": "application/json" }
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    return { data: data, retrievedAt: new Date().toISOString() };
  } finally {
    clearTimeout(timeout);
  }
}
function validPmId(v) { return /^\d{1,10}$/.test(String(v || "")); }
function validNct(v) { return /^NCT\d{8}$/.test(String(v || "")); }
function textLimited(v, max) { return String(v || "Not supplied").slice(0, max); }

function literatureRecord(item) {
  const pmid = validPmId(item.pmid) ? String(item.pmid) : null;
  const source = /^(MED|PMC|PPR)$/.test(String(item.source)) ? String(item.source) : null;
  const articleId = /^[a-zA-Z0-9._-]{1,80}$/.test(String(item.id || "")) ? String(item.id) : null;
  const href = pmid ? "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/" :
    source && articleId ? "https://europepmc.org/article/" + source + "/" + articleId : null;
  if (!href) return null;
  return {
    provider: "Europe PMC", identifier: pmid ? "PMID:" + pmid : source + ":" + articleId,
    title: textLimited(item.title, 350), date: textLimited(item.firstPublicationDate || item.firstIndexDate || item.pubYear, 30),
    note: item.isOpenAccess === "Y" ? "Open-access flag in source record; article license still applies" : "Access license not verified",
    href: href, type: source === "PPR" ? "Preprint record; not peer-reviewed by default" : "Literature record; peer review not independently verified"
  };
}
function trialRecord(item) {
  const mod = item && item.protocolSection ? item.protocolSection : {};
  const ident = mod.identificationModule || {};
  const status = mod.statusModule || {};
  if (!validNct(ident.nctId)) return null;
  return {
    provider: "ClinicalTrials.gov", identifier: String(ident.nctId),
    title: textLimited(ident.briefTitle || ident.officialTitle, 350),
    date: textLimited(status.studyFirstSubmitDate || status.lastUpdateSubmitDate, 30),
    note: "Current registry status: " + textLimited(status.overallStatus, 60),
    href: "https://clinicaltrials.gov/study/" + ident.nctId,
    type: "Registry entry, not a clinical efficacy conclusion"
  };
}
async function appendRecord(root, record, seq) {
  const elem = node("article", "result");
  const link = node("a", "", record.title);
  link.href = record.href; link.target = "_blank"; link.rel = "noopener noreferrer";
  elem.append(link, node("p", "identifier", record.identifier + " · " + record.provider),
    node("p", "", record.type),
    node("p", "", "Source date: " + record.date + " · " + record.note));
  const digestNode = node("p", "digest", "Normalized SHA-256: calculating...");
  elem.append(digestNode);
  root.append(elem);
  try {
    const digest = await sha256({
      provider: record.provider, identifier: record.identifier,
      title: record.title, source_date: record.date, source_url: record.href
    });
    if (seq === requestSequence) digestNode.textContent = "Normalized SHA-256: " + digest;
  } catch (_err) {
    if (seq === requestSequence) digestNode.textContent = "Normalized SHA-256 unavailable on this browser";
  }
}
async function showRecords(target, records, seq) {
  if (seq !== requestSequence) return;
  const root = $(target);
  root.replaceChildren();
  if (records.length === 0) {
    root.append(node("p", "empty", "Source returned no usable identifiers for this query."));
    return;
  }
  for (const record of records) {
    if (seq !== requestSequence) return;
    await appendRecord(root, record, seq);
  }
}
function errorLabel(error) {
  return error && error.name === "AbortError" ? "Upstream timed out" :
    error && /^HTTP \d{3}$/.test(error.message) ? error.message :
    "Unavailable or blocked by network/CORS";
}
async function loadLiterature(query, seq) {
  setStatus("literature", "wait", "Checking source…");
  try {
    const url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=lite&pageSize=6&query=" + encodeURIComponent(query);
    const out = await getJson(url, 25000);
    if (seq !== requestSequence) return;
    const entries = (((out.data || {}).resultList || {}).result || []);
    if (!Array.isArray(entries)) throw new Error("Unexpected schema");
    const records = entries.map(literatureRecord).filter(Boolean);
    $("litCount").textContent = records.length + " records";
    setStatus("literature", "ok", "Fetched " + out.retrievedAt);
    await showRecords("literature", records, seq);
    return out.retrievedAt;
  } catch (err) {
    if (seq !== requestSequence) return null;
    setStatus("literature", "bad", errorLabel(err));
    $("litCount").textContent = "unavailable";
    clearResults("literature", "No verified live response. Use the official Europe PMC site to search directly.");
    return null;
  }
}
async function loadTrials(query, seq) {
  setStatus("trial", "wait", "Checking source…");
  try {
    const url = "https://clinicaltrials.gov/api/v2/studies?pageSize=6&format=json&query.term=" + encodeURIComponent(query);
    const out = await getJson(url);
    if (seq !== requestSequence) return;
    if (!Array.isArray(out.data.studies)) throw new Error("Unexpected schema");
    const records = out.data.studies.map(trialRecord).filter(Boolean);
    $("trialCount").textContent = records.length + " records";
    setStatus("trial", "ok", "Fetched " + out.retrievedAt);
    await showRecords("trials", records, seq);
    return out.retrievedAt;
  } catch (err) {
    if (seq !== requestSequence) return null;
    setStatus("trial", "bad", errorLabel(err));
    $("trialCount").textContent = "unavailable";
    clearResults("trials", "No verified live response. Use ClinicalTrials.gov directly to search.");
    return null;
  }
}
FORM.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = $("query").value.trim();
  if (query.length < 2 || query.length > 120) {
    $("fetchMeta").textContent = "Enter a public research topic between 2 and 120 characters.";
    return;
  }
  const seq = ++requestSequence;
  BUTTON.disabled = true;
  BUTTON.textContent = "Fetching…";
  $("litCount").textContent = "—"; $("trialCount").textContent = "—";
  clearResults("literature", "Fetching source…");
  clearResults("trials", "Fetching source…");
  $("fetchMeta").textContent = "Querying two public services independently. Failure of one does not suppress the other.";
  try {
    const results = await Promise.allSettled([loadLiterature(query, seq), loadTrials(query, seq)]);
    if (seq !== requestSequence) return;
    const successes = results.filter((x) => x.status === "fulfilled" && x.value).length;
    $("fetchMeta").textContent = "Search completed " + new Date().toISOString() +
      " · " + successes + "/2 upstream services returned usable JSON. Source dates and fingerprint scope appear on records; access and evidentiary quality are not implied.";
  } finally {
    if (seq === requestSequence) {
      BUTTON.disabled = false; BUTTON.textContent = "Search sources";
    }
  }
});