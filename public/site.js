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

/* Search visualization: 26 cubies with six outward-facing sticker colors.
 * Quarter turns preserve each piece's spatial coordinates and face colors.
 * Animation is NOT scientific computation or a quantum hardware job.
 */
const CUBE = $("rubiksCube");
const cubePieces = [];
const faceVectors = {
  front: [0, 0, 1], back: [0, 0, -1],
  right: [1, 0, 0], left: [-1, 0, 0],
  top: [0, -1, 0], bottom: [0, 1, 0]
};
const turnOptions = [
  ["x", 1, 1], ["y", -1, 1], ["z", 1, 1],
  ["x", -1, -1], ["y", 1, -1], ["z", -1, -1]
];
let cubeTimer = null;
let cubeTurnBusy = false;
let cubeTurnIndex = 0;
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function cubePosition(piece) {
  return "translate3d(" + (piece.x * 55) + "px," + (piece.y * 55) + "px," + (piece.z * 55) + "px)";
}
function rotateVector(vector, axis, direction) {
  const [x, y, z] = vector;
  if (axis === "x") return [x, -direction * z, direction * y];
  if (axis === "y") return [direction * z, y, -direction * x];
  return [-direction * y, direction * x, z];
}
function faceFor(normal) {
  for (const [name, vector] of Object.entries(faceVectors)) {
    if (vector.every((value, index) => value === normal[index])) return name;
  }
  throw new Error("Invalid cube rotation");
}
function drawCubie(piece) {
  piece.element.style.transform = cubePosition(piece);
  const stickers = piece.stickers.map((sticker) => {
    const side = faceFor(sticker.normal);
    return node("span", "sticker face-" + side + " color-" + sticker.color);
  });
  piece.element.replaceChildren(...stickers);
}
function initCube() {
  if (!CUBE) return;
  for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) {
    if (x === 0 && y === 0 && z === 0) continue;
    const stickers = [];
    if (z === 1) stickers.push({normal: [0, 0, 1], color: "front"});
    if (z === -1) stickers.push({normal: [0, 0, -1], color: "back"});
    if (x === 1) stickers.push({normal: [1, 0, 0], color: "right"});
    if (x === -1) stickers.push({normal: [-1, 0, 0], color: "left"});
    if (y === -1) stickers.push({normal: [0, -1, 0], color: "top"});
    if (y === 1) stickers.push({normal: [0, 1, 0], color: "bottom"});
    const piece = {x, y, z, stickers, element: node("div", "cubie")};
    drawCubie(piece);
    cubePieces.push(piece);
    CUBE.append(piece.element);
  }
}
async function turnCubeLayer() {
  if (cubeTurnBusy || !CUBE || cubePieces.length !== 26) return;
  cubeTurnBusy = true;
  const [axis, layer, direction] = turnOptions[cubeTurnIndex++ % turnOptions.length];
  const chosen = cubePieces.filter((piece) => piece[axis] === layer);
  try {
    if (!reduceMotion.matches && chosen.every((p) => typeof p.element.animate === "function")) {
      const animations = chosen.map((piece) => piece.element.animate(
        [{transform: cubePosition(piece)},
         {transform: "rotate" + axis.toUpperCase() + "(" + (direction * 90) + "deg) " + cubePosition(piece)}],
        {duration: 470, easing: "ease-in-out", fill: "forwards"}
      ));
      await Promise.all(animations.map((animation) => animation.finished.catch(() => undefined)));
      animations.forEach((animation) => animation.cancel());
    }
    for (const piece of chosen) {
      const next = rotateVector([piece.x, piece.y, piece.z], axis, direction);
      [piece.x, piece.y, piece.z] = next;
      piece.stickers.forEach((sticker) => {
        sticker.normal = rotateVector(sticker.normal, axis, direction);
      });
      drawCubie(piece);
    }
  } finally {
    cubeTurnBusy = false;
  }
}
function startCubeSearch() {
  if (!CUBE) return;
  CUBE.classList.add("is-searching");
  $("cubeActivity").textContent = reduceMotion.matches ?
    "Research sources are being queried. Motion has been reduced." :
    "Searching: cube faces are turning through the six evidence planes.";
  if (cubeTimer !== null) clearInterval(cubeTimer);
  cubeTimer = reduceMotion.matches ? null : setInterval(() => { void turnCubeLayer(); }, 650);
  if (!reduceMotion.matches) void turnCubeLayer();
}
function stopCubeSearch() {
  if (cubeTimer !== null) clearInterval(cubeTimer);
  cubeTimer = null;
  if (CUBE) CUBE.classList.remove("is-searching");
  $("cubeActivity").textContent = "Search finished. Cube is ready for another turn.";
}
initCube();
$("cubeMoveBtn").addEventListener("click", () => {
  void turnCubeLayer();
});

/* Backend is only enabled when this page is hosted with the actual API on
 * the SAME origin. GitHub Pages has a disabled config and never claims
 * that repository-backed adapters are publicly deployed.
 */
let backendEnabled = false;
const backendConfiguration = (async () => {
  try {
    const response = await getJson("./backend-config.json", 6000);
    const config = response.data;
    backendEnabled = Boolean(config && config.api_mode === "same-origin");
  } catch (_error) {
    backendEnabled = false;
  }
  $("backendState").textContent = backendEnabled ?
    "Same-origin research API configured · connectivity pending" :
    "Backend not deployed on this site · two public live sources remain available";
  return backendEnabled;
})();
async function loadGovernedPathway(query, seq) {
  if (!(await backendConfiguration) || seq !== requestSequence) return null;
  $("backendState").textContent = "Querying governed research API…";
  const root = $("pathwayRecords");
  root.replaceChildren(node("p", "empty", "Checking source-reported, exact-ID evidence links…"));
  try {
    const url = "/api/v1/research/evidence-pathway?limit=8&disease=" + encodeURIComponent(query);
    const out = await getJson(url, 24000);
    if (seq !== requestSequence) return null;
    const payload = out.data;
    if (!payload || typeof payload.status !== "string" || !Array.isArray(payload.links)) throw new Error("Invalid schema");
    root.replaceChildren();
    const known = payload.status === "links_retrieved";
    if (known) {
      for (const link of payload.links.slice(0, 8)) {
        const tid = link && link.target && link.target.id;
        const cid = link && link.compound && link.compound.id;
        if (!/^ENSG[0-9]{11}$/.test(tid || "") || !/^CHEMBL[0-9]{1,12}$/.test(cid || "")) continue;
        const item = node("article", "pathway-entry");
        item.append(node("strong", "", String(link.target.symbol || tid) + " → " + String(link.compound.name || cid)),
          node("p", "", "Disease " + String(payload.disease && payload.disease.id) +
            " · Target " + tid + " · Compound " + cid),
          node("p", "", "Source-reported mechanism · no clinical efficacy assessment."));
        const sourceLink = node("a", "", "Verify ChEMBL identifier in Open Targets");
        sourceLink.href = "https://platform.opentargets.org/drug/" + cid;
        sourceLink.target = "_blank";
        sourceLink.rel = "noopener noreferrer";
        item.append(sourceLink);
        root.append(item);
      }
    }
    if (!root.children.length) {
      root.append(node("p", "empty", payload.status === "source_unavailable" ?
        "Backend upstream unavailable, invalid or exceeded bounds. Not a negative scientific finding." :
        payload.status === "disease_not_unambiguously_resolved" ?
        "Disease identifier ambiguous or unmatched; use an exact MONDO identifier or official source." :
        "No exact, source-reported links in this bounded sample. This does not establish absence."));
    }
    $("backendState").textContent = "Research API " + payload.status + " · " + out.retrievedAt;
    const coverage = payload.coverage || {};
    $("pathwayFootnote").textContent =
      "Source report: " + String(payload.source_freshness && payload.source_freshness.source_release || "release unverified") +
      " · Partial dataset: " + (coverage.truncated ? "yes" : "unverified if source count absent") +
      " · Metadata display only; third-party license review and independent clinical review required.";
    return known ? out.retrievedAt : null;
  } catch (_error) {
    if (seq === requestSequence) {
      $("backendState").textContent = "Research API unavailable or blocked";
      root.replaceChildren(node("p", "empty", "No backend response available; scientific conclusions are not inferred."));
    }
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
  startCubeSearch();
  $("litCount").textContent = "—"; $("trialCount").textContent = "—";
  clearResults("literature", "Fetching source…");
  clearResults("trials", "Fetching source…");
  $("fetchMeta").textContent = "Querying two public services independently. Failure of one does not suppress the other.";
  try {
    const results = await Promise.allSettled([loadLiterature(query, seq), loadTrials(query, seq), loadGovernedPathway(query, seq)]);
    if (seq !== requestSequence) return;
    const successes = results.slice(0, 2).filter((x) => x.status === "fulfilled" && x.value).length;
    $("fetchMeta").textContent = "Search completed " + new Date().toISOString() +
      " · " + successes + "/2 upstream services returned usable JSON. Source dates and fingerprint scope appear on records; access and evidentiary quality are not implied.";
  } finally {
    if (seq === requestSequence) {
      BUTTON.disabled = false; BUTTON.textContent = "Search sources";
      stopCubeSearch();
    }
  }
});