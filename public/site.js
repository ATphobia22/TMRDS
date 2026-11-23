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


/* Additional direct public records; no backend or clinical data needed. */
function crossrefRecord(work) {
  const doi = String(work && work.DOI || "").trim();
  const validDoi = doi.startsWith("10.") && doi.includes("/") && doi.length <= 200 &&
    !Array.from(doi).some((character) => character.charCodeAt(0) <= 32);
  if (!validDoi) return null;
  const parts = work.published && Array.isArray(work.published["date-parts"]) ?
    work.published["date-parts"][0] : [];
  return {
    provider: "Crossref", identifier: "DOI:" + doi.toLowerCase(),
    title: textLimited(Array.isArray(work.title) ? work.title[0] : work.title, 350),
    date: Array.isArray(parts) && parts.length ? parts.slice(0, 3).join("-") : "Not supplied",
    note: textLimited(Array.isArray(work["container-title"]) ? work["container-title"][0] : "", 100),
    type: "Deposited DOI metadata; does not imply peer review, efficacy, or independent replication",
    href: "https://doi.org/" + encodeURIComponent(doi)
  };
}
async function loadCrossref(query, seq) {
  setStatus("crossref", "wait", "Checking source…");
  try {
    const url = "https://api.crossref.org/works?rows=5&select=DOI,title,published,container-title&query.bibliographic=" +
      encodeURIComponent(query);
    const out = await getJson(url, 22000);
    if (seq !== requestSequence) return;
    const values = out.data && out.data.message && out.data.message.items;
    if (!Array.isArray(values)) throw new Error("Unexpected Crossref schema");
    const records = values.map(crossrefRecord).filter(Boolean);
    $("crossrefCount").textContent = records.length + " DOI records";
    setStatus("crossref", "ok", "Fetched " + out.retrievedAt);
    await showRecords("crossrefResults", records, seq);
    return out.retrievedAt;
  } catch (error) {
    if (seq !== requestSequence) return null;
    setStatus("crossref", "bad", errorLabel(error));
    $("crossrefCount").textContent = "unavailable";
    clearResults("crossrefResults", "Crossref unavailable or blocked by CORS; use the official Crossref search.");
    return null;
  }
}

/* Each link is a human-initiated search in the named original service.
 * They are not secretly routed through the TMRDS server.
 */
const researchPortals = [
  {name:"PubMed", base:"https://pubmed.ncbi.nlm.nih.gov/", key:"term", why:"Original NLM biomedical citation records"},
  {name:"Crossref", base:"https://search.crossref.org/", key:"q", why:"DOI-deposited publication metadata"},
  {name:"ClinVar", base:"https://www.ncbi.nlm.nih.gov/clinvar/", key:"term", why:"Variant interpretations with review status"},
  {name:"UniProtKB", base:"https://www.uniprot.org/uniprotkb", key:"query", why:"Protein identifiers, functions and references"},
  {name:"RCSB PDB", base:"https://www.rcsb.org/", key:null, why:"Experimental three-dimensional structures"},
  {name:"Open Targets", base:"https://platform.opentargets.org/", key:null, why:"Target-disease evidence by original source"},
  {name:"ChEMBL", base:"https://www.ebi.ac.uk/chembl/", key:null, why:"Compound assays, mechanisms and annotations"},
  {name:"PubChem", base:"https://pubchem.ncbi.nlm.nih.gov/", key:null, why:"Chemical identities and public assays"},
  {name:"Reactome", base:"https://reactome.org/content/query", key:"q", why:"Curated biological reaction pathways"},
  {name:"NLM MeSH", base:"https://meshb.nlm.nih.gov/", key:null, why:"Controlled indexing vocabulary"},
  {name:"FDA Orange Book", base:"https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files", key:null, why:"Drug approval, patent and exclusivity metadata"},
  {name:"USPTO Patent Search", base:"https://www.uspto.gov/patents/search", key:null, why:"Patent claims and legal-status records"}
];
function updateResearchPortalLinks() {
  const term = $("query").value.trim().slice(0, 100);
  const root = $("portalList");
  root.replaceChildren();
  for (const portal of researchPortals) {
    const card = node("article", "medical-entry");
    card.append(node("span", "medical-type", portal.key ? "Original-source search link" : "Original-source research destination"),
      node("strong", "", portal.name), node("p", "", portal.why));
    const link = node("a", "", portal.key && term ? "Search this source for current topic" : "Open official source");
    const destination = new URL(portal.base);
    if (portal.key && term) destination.searchParams.set(portal.key, term);
    link.href = destination.href; link.target = "_blank"; link.rel = "noopener noreferrer";
    card.append(link); root.append(card);
  }
}
$("query").addEventListener("change", updateResearchPortalLinks);
$("query").addEventListener("input", updateResearchPortalLinks);
updateResearchPortalLinks();

/* Model-to-model data exchange is inspired by OpenMI but not certified as
 * an OpenMI runtime. Do not claim clinical interoperability or QPU execution.
 */
async function loadBackendCrosscheck(query, seq) {
  const root = $("crosscheckRecords");
  if (!(await backendConfiguration) || seq !== requestSequence) {
    $("crosscheckState").textContent = "No Python cross-check backend on static Pages";
    root.replaceChildren(node("p", "empty", "Direct public source searches remain available above and below."));
    return null;
  }
  $("crosscheckState").textContent = "Cross-checking twelve metadata providers…";
  root.replaceChildren(node("p", "empty", "Checking original DOI / PMID / NCT identifiers…"));
  try {
    const response = await getJson("/api/v1/research/cross-check?limit=2&query=" + encodeURIComponent(query), 48000);
    if (seq !== requestSequence) return null;
    const data = response.data;
    if (!data || !Array.isArray(data.groups) || !data.source_status ||
        !data.openmi_inspired_exchange) throw new Error("Invalid evidence cross-check contract");
    root.replaceChildren();
    const multihits = data.groups.filter((g) => Array.isArray(g.sources) && g.sources.length > 1);
    const chosen = multihits.length ? multihits.slice(0, 8) : data.groups.slice(0, 5);
    for (const group of chosen) {
      const article = node("article", "pathway-entry");
      article.append(node("strong", "", group.sources.join(" · ")),
        node("p", "", (group.exact_identifiers || []).join(" · ") || "Source-only record; no exact shared identifiers"),
        node("p", "", group.interpretation === "cross_index_metadata_overlap_only" ?
          "Same indexed source item in multiple catalogs; NOT independent experimental replication" :
          "Single original-source record; corroboration not established"));
      root.append(article);
    }
    if (!chosen.length) root.append(node("p", "empty", "No bounded records returned; missing sources and failures must be reviewed."));
    const states = Object.values(data.source_status);
    const responsive = states.filter((v) => v.state === "responding").length;
    $("crosscheckState").textContent = responsive + "/12 source requests responded · " +
      data.metadata_overlap_groups + " exact-ID overlap groups · " + response.retrievedAt;
    $("crosscheckFootnote").textContent =
      "Fingerprint " + textLimited(data.snapshot_sha256, 64) +
      " applies to source counts/status, not original raw records. " +
      "OpenMI-inspired exchange is NOT OGC-conformance-tested. Scientific replication, patent freedom to operate, clinical effect and cures NOT verified.";
    return data.status;
  } catch (_) {
    if (seq === requestSequence) {
      root.replaceChildren(node("p", "empty", "Bounded cross-check unavailable; this is not evidence of absence."));
      $("crosscheckState").textContent = "Backend source cross-check unavailable";
    }
    return null;
  }
}

/* Official FDA Orange Book can be queried directly from GitHub Pages.
 * FDA-reported dates are NEVER automatically translated to rights or FTO.
 */
$("patentForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const ingredient = $("ingredient").value.trim().toUpperCase();
  if (!/^[A-Z][A-Z0-9 -]{1,55}$/.test(ingredient)) {
    $("patentState").textContent = "Enter one public drug ingredient without punctuation or personal information.";
    return;
  }
  const root = $("patentRecords");
  const button = $("patentSubmit");
  button.disabled = true;
  root.replaceChildren(node("p", "empty", "Requesting original FDA Orange Book records…"));
  $("patentState").textContent = "FDA source query in progress…";
  try {
    const out = await getJson("https://api.fda.gov/drug/orangebook.json?search=" +
      encodeURIComponent("products.active_ingredients.name:" + ingredient) + "&limit=3", 17000);
    const records = out.data && out.data.results;
    if (!Array.isArray(records)) throw new Error("FDA schema mismatch");
    root.replaceChildren();
    for (const record of records.slice(0, 3)) {
      const products = Array.isArray(record.products) ? record.products.slice(0, 4) : [];
      const names = products.map((p) => textLimited(p.brand_name, 80)).filter(Boolean).join(", ");
      const article = node("article", "result");
      article.append(node("strong", "", names || "FDA listed application"),
        node("p", "identifier", "Application: " +
          products.map((p) => textLimited(p.application_number, 15)).filter(Boolean).join(", ")));
      const patents = Array.isArray(record.patents) ? record.patents.slice(0, 10) : [];
      if (patents.length) {
        for (const patent of patents) {
          article.append(node("p", "", "FDA-listed patent " + textLimited(patent.patent_number, 20) +
            " · reported expiration " + textLimited(patent.expiration_date, 15) +
            " · legal validity and freedom to operate UNVERIFIED"));
        }
      } else {
        article.append(node("p", "", "No patents listed on this result; this does NOT establish public-domain availability."));
      }
      const exclusivity = Array.isArray(record.exclusivity) ? record.exclusivity : [];
      for (const row of exclusivity.slice(0, 6)) {
        article.append(node("p", "", "Regulatory exclusivity: " +
          textLimited(row.exclusivity_code, 30) + " · listed through " +
          textLimited(row.exclusivity_expiration_date, 15)));
      }
      root.append(article);
    }
    if (!root.children.length) root.append(node("p", "empty", "FDA returned no bounded records."));
    $("patentState").textContent = "Official FDA record lookup at " + out.retrievedAt +
      " · database last updated: " + textLimited(out.data.meta && out.data.meta.last_updated, 30) +
      " · patent status/claims and freedom to operate NOT independently verified.";
  } catch (error) {
    root.replaceChildren(node("p", "empty",
      errorLabel(error) + ". No patent expiry or clearance conclusion may be made."));
    $("patentState").textContent = "FDA source unavailable / no usable response; no legal claims verified";
  } finally {
    button.disabled = false;
  }
});

/* Auditable project index is published as a static JSON asset on GitHub Pages.
 * Project discovery does not mean its software is installed or connected.
 */
let medicalProjects = [];
function medicalSafeLink(link) {
  try {
    const url = new URL(String(link));
    return url.protocol === "https:" && !url.username && !url.password && !url.port &&
      url.hostname.length > 3 && !/^(localhost|127\\.|10\\.|192\\.168\\.)/.test(url.hostname);
  } catch (_) { return false; }
}
function drawMedicalProjects() {
  const category = $("medicalCategory").value;
  const chosen = medicalProjects.filter((project) => category === "all" || project.category === category);
  const root = $("medicalList");
  root.replaceChildren();
  for (const project of chosen) {
    const item = node("article", "medical-entry");
    item.append(node("span", "medical-type", project.category.replaceAll("_", " ")),
      node("strong", "", project.name),
      node("span", "medical-state", "Connection: " + project.integration_state.replaceAll("_", " ")),
      node("p", "", project.interface),
      node("p", "", project.license_notes),
      node("p", "", "Source review: " + project.verification.replaceAll("_", " ")));
    if (medicalSafeLink(project.source_url)) {
      const anchor = node("a", "", "Official project or documentation");
      anchor.href = project.source_url; anchor.target = "_blank"; anchor.rel = "noopener noreferrer";
      item.append(anchor);
    }
    root.append(item);
  }
  $("medicalCount").textContent = chosen.length + " of " + medicalProjects.length + " cataloged projects";
  if (!chosen.length) root.append(node("p", "empty", "No projects in this category."));
}
async function loadMedicalProjectCatalog() {
  try {
    const outcome = await getJson("./medical-projects.json", 9000);
    const json = outcome.data;
    if (!json || json.schema_version !== "1.0" || !Array.isArray(json.projects) ||
        json.projects.length < 10 || json.all_platforms_installed !== false) {
      throw new Error("unrecognized project catalog schema");
    }
    medicalProjects = json.projects.filter((item) =>
      typeof item.name === "string" && typeof item.category === "string" &&
      typeof item.integration_state === "string" && typeof item.source_url === "string");
    const categories = [...new Set(medicalProjects.map((p) => p.category))].sort();
    $("medicalCategory").append(...categories.map((category) => {
      const option = node("option", "", category.replaceAll("_", " "));
      option.value = category;
      return option;
    }));
    drawMedicalProjects();
    $("medicalRegistryStatus").textContent =
      "Official project/repository references last inventoried " + String(json.reviewed_on) +
      ". License approvals and runtime health are NOT automatically verified. No patient data or clinical connectors enabled.";
  } catch (_) {
    $("medicalList").replaceChildren(node("p", "empty", "Project catalog unavailable; no project status can be inferred."));
    $("medicalCount").textContent = "Catalog unavailable";
  }
}
$("medicalCategory").addEventListener("change", drawMedicalProjects);
void loadMedicalProjectCatalog();

async function loadBackendPubMed(query, seq) {
  if (!(await backendConfiguration) || seq !== requestSequence) {
    $("pubmedBackendState").textContent = "Python backend not configured on this site. PubMed official search remains available by link.";
    return null;
  }
  const container = $("pubmedBackendRecords");
  container.replaceChildren(node("p", "empty", "Querying NCBI PubMed citations…"));
  $("pubmedBackendState").textContent = "Bounded live PubMed metadata lookup…";
  try {
    const outcome = await getJson("/api/v1/research/pubmed-citations?limit=5&query=" +
      encodeURIComponent(query), 24000);
    if (seq !== requestSequence) return null;
    const data = outcome.data;
    if (!data || !Array.isArray(data.records) || !["responding", "source_unavailable"].includes(data.status)) {
      throw new Error("invalid PubMed citation contract");
    }
    container.replaceChildren();
    if (data.status !== "responding") {
      container.append(node("p", "empty", "NCBI service unavailable; no negative findings inferred."));
    } else {
      for (const record of data.records) {
        if (!validPmId(record.pmid)) continue;
        const item = node("article", "result");
        const link = node("a", "", textLimited(record.title, 350));
        link.href = "https://pubmed.ncbi.nlm.nih.gov/" + record.pmid + "/";
        link.target = "_blank"; link.rel = "noopener noreferrer";
        item.append(link,
          node("p", "identifier", "PMID " + record.pmid + " · " + textLimited(record.published, 40)),
          node("p", "", textLimited(record.journal, 150)));
        container.append(item);
      }
      if (!container.children.length) container.append(node("p", "empty", "No bounded citation matches returned."));
    }
    $("pubmedBackendState").textContent = "PubMed source: " + data.status + " · checked " + outcome.retrievedAt;
    return data.status;
  } catch (_) {
    if (seq === requestSequence) {
      container.replaceChildren(node("p", "empty", "PubMed backend request failed or exceeded bounds."));
      $("pubmedBackendState").textContent = "Backend unavailable; no research result inferred.";
    }
    return null;
  }
}
$("structureForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const accession = $("uniprotAccession").value.trim().toUpperCase();
  const target = $("structureBackendRecords");
  if (!/^[A-Z0-9]{6,10}$/.test(accession)) {
    $("structureBackendState").textContent = "Use a public UniProt identifier of 6-10 alphanumeric characters.";
    return;
  }
  if (!(await backendConfiguration)) {
    target.replaceChildren(node("p", "empty", "The static website does not execute structure APIs."));
    $("structureBackendState").textContent = "Backend not deployed on this site. Visit the official AlphaFold DB.";
    return;
  }
  const submit = $("structureSubmit");
  submit.disabled = true;
  target.replaceChildren(node("p", "empty", "Checking AlphaFold DB official record…"));
  try {
    const response = await getJson("/api/v1/research/alphafold-db/" + encodeURIComponent(accession), 22000);
    const data = response.data;
    if (!data || typeof data.status !== "string" || !Array.isArray(data.records)) {
      throw new Error("invalid structure response");
    }
    target.replaceChildren();
    if (data.status === "predicted_structure_metadata" && data.records.length) {
      const rec = data.records[0];
      const article = node("article", "result");
      article.append(node("p", "identifier", "UniProt " + accession + " · predicted, not experimentally verified"),
        node("p", "", "Gene: " + textLimited(rec.gene, 80) +
          " · Mean pLDDT: " + (typeof rec.mean_plddt === "number" ? rec.mean_plddt : "not reported")),
        node("p", "", "Model version: " + textLimited(rec.model_version, 50) +
          " · Normalized evidence SHA-256: " + textLimited(data.record_sha256, 80)));
      if (medicalSafeLink(rec.cif_url) && new URL(rec.cif_url).hostname === "alphafold.ebi.ac.uk") {
        const link = node("a", "", "View original predicted mmCIF structure");
        link.href = rec.cif_url; link.target = "_blank"; link.rel = "noopener noreferrer";
        article.append(link);
      }
      target.append(article);
    } else {
      target.append(node("p", "empty", data.status === "not_found" ?
        "No source structure exists for this accession." :
        "AlphaFold DB unavailable/invalid; no predicted structure fabricated."));
    }
    $("structureBackendState").textContent = "AlphaFold DB: " + data.status + " · " + response.retrievedAt +
      " · This is NOT AlphaFold 3 inference.";
  } catch (_) {
    target.replaceChildren(node("p", "empty", "Structure lookup unavailable; do not infer a structure."));
    $("structureBackendState").textContent = "Source or backend unavailable";
  } finally {
    submit.disabled = false;
  }
});

FORM.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = $("query").value.trim();
  const pieces = query.split("-");
  const isSSN = pieces.length === 3 && pieces[0].length === 3 && pieces[1].length === 2 &&
    pieces[2].length === 4 && pieces.every((part) => Array.from(part).every((c) => c >= "0" && c <= "9"));
  if (query.length < 2 || query.length > 100 || query.includes("@") || isSSN) {
    $("fetchMeta").textContent = "Enter a non-personal research topic between 2 and 100 characters.";
    return;
  }
  const seq = ++requestSequence;
  BUTTON.disabled = true;
  BUTTON.textContent = "Fetching…";
  startCubeSearch();
  $("litCount").textContent = "—"; $("trialCount").textContent = "—"; $("crossrefCount").textContent = "—";
  clearResults("literature", "Fetching source…");
  clearResults("trials", "Fetching source…");
  clearResults("crossrefResults", "Fetching original DOI metadata…");
  $("fetchMeta").textContent = "Querying three public services independently. Failure of one does not suppress the other.";
  try {
    const results = await Promise.allSettled([loadLiterature(query, seq), loadTrials(query, seq), loadCrossref(query, seq), loadGovernedPathway(query, seq), loadBackendPubMed(query, seq), loadBackendCrosscheck(query, seq)]);
    if (seq !== requestSequence) return;
    const successes = results.slice(0, 3).filter((x) => x.status === "fulfilled" && x.value).length;
    $("fetchMeta").textContent = "Search completed " + new Date().toISOString() +
      " · " + successes + "/3 upstream services returned usable JSON. Source dates and fingerprint scope appear on records; access and evidentiary quality are not implied.";
  } finally {
    if (seq === requestSequence) {
      BUTTON.disabled = false; BUTTON.textContent = "Search sources";
      stopCubeSearch();
    }
  }
});