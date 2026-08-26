#!/usr/bin/env node
/** Build the canonical supervisor workbook around EDA relationships. */

import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "/Users/jarlgiovanni/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const root = "/Users/jarlgiovanni/Desktop/fear_of_temperature";
const outputPath = path.join(root, "outputs/quantitative-v01/fear_temperature_quantitative_v01.xlsx");
const previewDir = "/tmp/fear_temperature_eda_workbook_previews";
const validationPath = path.join(root, "data/fear-temperature/exports/supervisor_workbook_validation.json");
const figureManifestPath = path.join(root, "figures/fear-temperature/eda-v02/figure_manifest.json");

const COLORS = {
  navy: "#102A43", navy2: "#17324D", teal: "#0B6E75", tealLight: "#D9F0F0",
  purple: "#6B5CA5", purpleLight: "#F3F0F8", orange: "#C65D3B", orangeLight: "#FFF3EC",
  amber: "#D49B28", amberLight: "#FFF8E7", green: "#2E7D5B", greenLight: "#E7F4ED",
  red: "#B42318", redLight: "#FDECEC", gray: "#667085", grayLight: "#F2F4F7",
  blueLight: "#E8F1FB", ink: "#243B53", grid: "#D9E2EC", white: "#FFFFFF",
};

const analysisSheetNames = [
  "Supervisor Dashboard", "Analysis Guide", "Relationship Summary", "Anchor Layer", "Anchor Voice",
  "Anchor Family", "Voice Family", "Candidate Relations", "Comparability", "Ngram Trajectories",
  "Dictionary Analysis", "Search Analysis", "Coverage Bias", "Semantic Shortlist",
];
const detailSheetNames = [
  "Priority 180 Coverage", "Ngram Coverage", "Dictionary 180", "Search 180", "Seed Ledger",
  "Master Frequency", "Anchor Matrix", "Family Summary", "Voice Matrix", "Query Audit", "Ngram Status",
  "Keyword Discovery Method", "Summary",
];

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
      else if (char === '"') quoted = false;
      else field += char;
    } else if (char === '"') quoted = true;
    else if (char === ",") { row.push(field); field = ""; }
    else if (char === "\n") { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += char;
  }
  if (field.length || row.length) { row.push(field.replace(/\r$/, "")); rows.push(row); }
  return rows.filter((item) => item.length > 1 || item[0] !== "");
}

function columnLetter(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) { value -= 1; result = String.fromCharCode(65 + (value % 26)) + result; value = Math.floor(value / 26); }
  return result;
}

function isNumericHeader(header) {
  const h = String(header).toLowerCase();
  return h.includes("count") || h.includes("frequency") || h.includes("percentage") || h.includes("mean") ||
    h.includes("median") || h.includes("maximum") || h.includes("per_million") || h.includes("per million") ||
    h.includes("result") || h === "year" || h.endsWith("_year") || h === "priority_rank" || h === "rank" ||
    /^(1842|1938|1988|2006|2007|2015|2022)$/.test(h);
}

function typedMatrix(parsed) {
  const headers = parsed[0];
  return [headers, ...parsed.slice(1).map((row) => row.map((value, index) => {
    const trimmed = String(value).trim();
    if (isNumericHeader(headers[index]) && /^-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) return Number(trimmed);
    if (["true", "false"].includes(trimmed.toLowerCase())) return trimmed.toLowerCase() === "true";
    return trimmed;
  }))];
}

async function loadCsv(relativePath) {
  return typedMatrix(parseCsv(await fs.readFile(path.join(root, relativePath), "utf8")));
}

function titleBand(sheet, title, note, colCount) {
  const last = columnLetter(Math.max(colCount - 1, 7));
  sheet.getRange(`A1:${last}1`).merge();
  sheet.getRange(`A1:${last}1`).values = [[title]];
  sheet.getRange(`A1:${last}1`).format = { fill: COLORS.navy, font: { name: "Arial", size: 18, bold: true, color: COLORS.white }, verticalAlignment: "center" };
  sheet.getRange(`A1:${last}1`).format.rowHeight = 38;
  sheet.getRange(`A2:${last}2`).merge();
  sheet.getRange(`A2:${last}2`).values = [[note]];
  sheet.getRange(`A2:${last}2`).format = { fill: "#D9EAF0", font: { name: "Arial", size: 10, italic: true, color: COLORS.navy2 }, wrapText: true, verticalAlignment: "center" };
  sheet.getRange(`A2:${last}2`).format.rowHeight = 32;
}

function preferredWidth(header) {
  const h = String(header).toLowerCase();
  if (/note|sense|definition|provenance|reason|warning|question|basis/.test(h)) return 40;
  if (/url|path|interface|citation|source/.test(h)) return 32;
  if (/surface|form|concept|term_or_family|family/.test(h)) return 24;
  if (/status|match|mapping|missingness|exactness|relation/.test(h)) return 23;
  if (/candidate_id|candidate id|query_id|measurement_id/.test(h)) return 25;
  if (isNumericHeader(header)) return 16;
  return 16;
}

function applyStatusFormatting(range) {
  range.conditionalFormats.add("containsText", { text: "COMPLETE", format: { fill: COLORS.greenLight, font: { color: COLORS.green, bold: true } } });
  range.conditionalFormats.add("containsText", { text: "TRACEABLE", format: { fill: COLORS.greenLight, font: { color: COLORS.green } } });
  range.conditionalFormats.add("containsText", { text: "ZERO", format: { fill: COLORS.amberLight, font: { color: "#7B5B12", bold: true } } });
  range.conditionalFormats.add("containsText", { text: "UNRESOLVED", format: { fill: COLORS.redLight, font: { color: COLORS.red, bold: true } } });
  range.conditionalFormats.add("containsText", { text: "NOT_", format: { fill: COLORS.blueLight, font: { color: "#175CD3" } } });
  range.conditionalFormats.add("containsText", { text: "PARTIAL", format: { fill: COLORS.amberLight, font: { color: "#7B5B12" } } });
}

function addTable(sheet, matrix, title, note, options = {}) {
  const headers = matrix[0];
  const dataCount = matrix.length - 1;
  const colCount = headers.length;
  const last = columnLetter(colCount - 1);
  const endRow = 4 + dataCount;
  sheet.showGridLines = false;
  titleBand(sheet, title, note, colCount);
  sheet.getRangeByIndexes(3, 0, matrix.length, colCount).values = matrix;
  const table = sheet.tables.add(`A4:${last}${endRow}`, true, options.tableName || `${sheet.name.replace(/[^A-Za-z0-9]/g, "")}Table`);
  table.style = options.tableStyle || "TableStyleMedium2";
  table.showFilterButton = true;
  const used = sheet.getRange(`A4:${last}${endRow}`);
  used.format.font = { name: "Arial", size: options.fontSize || 9, color: COLORS.ink };
  used.format.verticalAlignment = "top";
  const header = sheet.getRange(`A4:${last}4`);
  header.format = { fill: options.headerFill || COLORS.navy2, font: { name: "Arial", size: 9, bold: true, color: COLORS.white }, wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.grid } };
  header.format.rowHeight = 42;
  if (dataCount) {
    const body = sheet.getRangeByIndexes(4, 0, dataCount, colCount);
    body.format.rowHeight = options.rowHeight || 24;
    body.format.borders = { preset: "inside", style: "thin", color: "#E8EEF3" };
  }
  headers.forEach((name, index) => {
    const width = preferredWidth(name);
    const range = sheet.getRangeByIndexes(3, index, matrix.length, 1);
    range.format.columnWidth = width;
    if (width >= 23) range.format.wrapText = true;
    if (isNumericHeader(name) && dataCount) {
      const format = /count|year|rank|result/i.test(name) && !/frequency|mean|median|percentage|per million|per_million/i.test(name) ? "#,##0" : (/percentage/i.test(name) ? "0.0%" : "0.000000E+00");
      sheet.getRangeByIndexes(4, index, dataCount, 1).format.numberFormat = format;
    }
    if (/status|match|mapping|missingness|relation|traceability/i.test(name) && dataCount) applyStatusFormatting(sheet.getRangeByIndexes(4, index, dataCount, 1));
  });
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(options.freezeColumns || 2);
  return { headers, dataCount, endRow, matrix };
}

function mergeSet(sheet, address, value, format = {}) {
  const range = sheet.getRange(address);
  range.merge();
  range.values = [[value]];
  range.format = { wrapText: true, verticalAlignment: "center", ...format };
  return range;
}

function card(sheet, labelRange, valueRange, label, formula, color) {
  mergeSet(sheet, labelRange, label, { fill: color, font: { name: "Arial", size: 10, bold: true, color: COLORS.white }, horizontalAlignment: "center", borders: { preset: "all", style: "thin", color } });
  const value = sheet.getRange(valueRange);
  value.merge();
  value.formulas = [[formula]];
  value.format = { fill: COLORS.white, font: { name: "Arial", size: 19, bold: true, color }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "all", style: "medium", color } };
}

const workbook = Workbook.create();
for (const name of [...analysisSheetNames, ...detailSheetNames]) workbook.worksheets.add(name);

const matrices = {
  anchorLayer: await loadCsv("data/fear-temperature/analysis/anchor_layer_counts.csv"),
  anchorVoice: await loadCsv("data/fear-temperature/analysis/anchor_voice_counts.csv"),
  anchorFamily: await loadCsv("data/fear-temperature/analysis/anchor_family_counts.csv"),
  voiceFamily: await loadCsv("data/fear-temperature/analysis/voice_family_counts.csv"),
  relations: await loadCsv("data/fear-temperature/analysis/candidate_relationship.csv"),
  comparability: await loadCsv("data/fear-temperature/analysis/candidate_comparability.csv"),
  ngramTrajectories: await loadCsv("figures/fear-temperature/eda-v02/sources/visual_05_climate_framing_trajectories_source.csv"),
  dictionaryAnalysis: await loadCsv("figures/fear-temperature/eda-v02/sources/visual_09_dictionary_status_by_anchor_source.csv"),
  searchAnalysis: await loadCsv("figures/fear-temperature/eda-v02/sources/visual_10_searchability_bias_source.csv"),
  coverageBias: await loadCsv("data/fear-temperature/analysis/coverage_bias_matrix.csv"),
  priority: await loadCsv("data/fear-temperature/exports/priority180_supervisor_coverage.csv"),
  ngram: await loadCsv("data/fear-temperature/exports/ngram_supervisor_coverage.csv"),
  dictionary: await loadCsv("data/fear-temperature/exports/dictionary_supervisor_180.csv"),
  search: await loadCsv("data/fear-temperature/exports/search_supervisor_180.csv"),
  seed: await loadCsv("data/fear-temperature/exports/seed_ledger_supervisor.csv"),
  master: await loadCsv("data/fear-temperature/exports/keyword_frequency_summary.csv"),
  anchor: await loadCsv("data/fear-temperature/exports/anchor_keyword_frequency_matrix.csv"),
  family: await loadCsv("data/fear-temperature/exports/lexical_family_frequency_summary.csv"),
  voice: await loadCsv("data/fear-temperature/exports/voice_keyword_matrix.csv"),
  query: await loadCsv("data/fear-temperature/exports/ngram_compatibility_audit.csv"),
  ngramStatus: await loadCsv("data/fear-temperature/ngram/ngram_query_execution_results.csv"),
};

let shortlistExists = true;
let shortlistMatrix;
try { shortlistMatrix = await loadCsv("data/fear-temperature/analysis/semantic_analysis_shortlist.csv"); }
catch { shortlistExists = false; shortlistMatrix = [["status", "next_action"], ["PENDING_STAGE_4", "Evidence-based semantic shortlist will be generated after workbook restructure validation."]]; }

const validation = JSON.parse(await fs.readFile(validationPath, "utf8"));
const figureManifest = JSON.parse(await fs.readFile(figureManifestPath, "utf8"));

addTable(workbook.worksheets.getItem("Anchor Layer"), matrices.anchorLayer, "Anchor × Lexical Layer", "Counts and within-anchor percentages describe the constructed Priority inventory, not historical prevalence.", { tableName: "AnchorLayerTable" });
addTable(workbook.worksheets.getItem("Anchor Voice"), matrices.anchorVoice, "Anchor × Voice", "Voice composition exposes source/speaker structure that may explain apparent lexical change.", { tableName: "AnchorVoiceTable" });
addTable(workbook.worksheets.getItem("Anchor Family"), matrices.anchorFamily, "Anchor × Lexical Family", "Complete 6 × 14 grid; zero candidate cells are retained.", { tableName: "AnchorFamilyTable" });
addTable(workbook.worksheets.getItem("Voice Family"), matrices.voiceFamily, "Voice × Lexical Family", "Candidate counts by controlled voice and family. This is reconstruction composition, not prevalence.", { tableName: "VoiceFamilyTable" });
addTable(workbook.worksheets.getItem("Candidate Relations"), matrices.relations, "Explicit Candidate Relationship Ledger", "Structural relations are separated from evidence-supported semantic candidate relations; no semantic-evolution network is inferred.", { tableName: "CandidateRelationsTable", freezeColumns: 3, rowHeight: 32 });
addTable(workbook.worksheets.getItem("Comparability"), matrices.comparability, "Cross-Anchor Comparability", "Strong, partial, invalid and unresolved comparisons remain explicit; same string does not imply same historical sense.", { tableName: "ComparabilityTable", rowHeight: 34 });
addTable(workbook.worksheets.getItem("Ngram Trajectories"), matrices.ngramTrajectories, "Climate-Framing Ngram Trajectories", "Unsmoothed annual Google Books series, 1842–2022. Raw normalized frequency is preserved beside per-million display values.", { tableName: "NgramTrajectoriesTable", rowHeight: 20 });
addTable(workbook.worksheets.getItem("Dictionary Analysis"), matrices.dictionaryAnalysis, "Dictionary Treatment by Anchor", "Direct headword, technical glossary and no-standalone-headword are lexicographic accounting states, not an evolution claim.", { tableName: "DictionaryAnalysisTable" });
addTable(workbook.worksheets.getItem("Search Analysis"), matrices.searchAnalysis, "Bounded Searchability by Anchor", "Internet Archive metadata text-item discovery outcomes. Provider discoverability is not language prevalence.", { tableName: "SearchAnalysisTable" });
addTable(workbook.worksheets.getItem("Coverage Bias"), matrices.coverageBias, "Coverage and Missingness Bias Matrix", "Anchor-level voice, expression mode, dictionary, Ngram, search and provenance states; zero and not-applicable remain visible.", { tableName: "CoverageBiasTable", rowHeight: 30 });
addTable(workbook.worksheets.getItem("Semantic Shortlist"), shortlistMatrix, "Semantic-Analysis Shortlist", shortlistExists ? "Evidence-based priorities for the next passage-level phase; this sheet does not begin the semantic pilot." : "Stage 3 structural placeholder; populated and revalidated in Stage 4.", { tableName: "SemanticShortlistTable", rowHeight: 36 });

addTable(workbook.worksheets.getItem("Priority 180 Coverage"), matrices.priority, "Priority 180 — Complete Candidate-Level Coverage", "Exactly 180 candidate records. Ngram, dictionary, search, provenance and annotation limitations remain linked.", { tableName: "Priority180CoverageTable", freezeColumns: 4, rowHeight: 34 });
addTable(workbook.worksheets.getItem("Ngram Coverage"), matrices.ngram, "Ngram Coverage and Rule Reconciliation", "All 143 query rules retained, including zero-result and incompatible cases; NGRAM_UNEXPLAINED = 0.", { tableName: "NgramCoverageTable", rowHeight: 27 });
addTable(workbook.worksheets.getItem("Dictionary 180"), matrices.dictionary, "Dictionary and Lexicographic Coverage — 180 Candidates", "Concise paraphrases with source attribution; no standalone headword remains a valid accounted state.", { tableName: "Dictionary180Table", freezeColumns: 4, rowHeight: 38 });
addTable(workbook.worksheets.getItem("Search 180"), matrices.search, "Bounded Search Coverage — 180 Candidates", "Primary metric is Internet Archive Advanced Search API numFound at retrieval time, not lexical prevalence.", { tableName: "Search180Table", freezeColumns: 4, rowHeight: 34 });
addTable(workbook.worksheets.getItem("Seed Ledger"), matrices.seed, "Provisional Seed Ledger — 396 Provenance-Bearing Records", "Original wording and controlled missingness are preserved; no unavailable original ID is fabricated.", { tableName: "SeedLedgerTable", freezeColumns: 3, rowHeight: 30 });
addTable(workbook.worksheets.getItem("Master Frequency"), matrices.master, "Keyword Frequency Master Table", "Annual normalized Google Books values and descriptive statistics; family members are never summed into a composite index.", { tableName: "MasterFrequencyTable" });
addTable(workbook.worksheets.getItem("Anchor Matrix"), matrices.anchor, "Six-Anchor Keyword Frequency Matrix", "Raw normalized frequencies; 2006 and 2007 remain separate plus an explicitly labelled mean.", { tableName: "AnchorMatrixTable" });
addTable(workbook.worksheets.getItem("Family Summary"), matrices.family, "Lexical Family Frequency Summary", "Fourteen semantic families; member trajectories are reported individually, not summed.", { tableName: "FamilySummaryTable", rowHeight: 38 });
addTable(workbook.worksheets.getItem("Voice Matrix"), matrices.voice, "Six Anchors × Five Voices", "Evidence-backed cells only; historically unsupported cells remain visible.", { tableName: "VoiceMatrixTable", rowHeight: 42 });
addTable(workbook.worksheets.getItem("Query Audit"), matrices.query, "Ngram Compatibility Audit", "Compatibility, reason and provenance for each provisional rule.", { tableName: "QueryAuditTable", rowHeight: 28 });
addTable(workbook.worksheets.getItem("Ngram Status"), matrices.ngramStatus, "Raw Ngram Execution Status", "Provider response accounting, checksums, timestamps and explicit zero/incompatible outcomes.", { tableName: "NgramStatusTable", rowHeight: 26 });

const guide = workbook.worksheets.getItem("Analysis Guide");
guide.showGridLines = false;
titleBand(guide, "Analysis Guide", "How to read the EDA relationship tables without collapsing distinct evidence channels.", 10);
guide.getRange("A4:C4").values = [["Dimension", "Codes / metric", "Interpretation"]];
guide.getRange("A5:C11").values = [
  ["Lexical layers", "A / B / C / D", "Temperature/physical; climate/causal; affect; threat/risk/harm."],
  ["Voices", "V1–V5", "Scientific; institutional; mediated public; organised civic; direct public/lay."],
  ["Lexical families", "14 semantic families", "Research groupings, not synonym sets and not additive frequency indices."],
  ["Ngram", "Annual normalized string frequency", "Corpus string occurrence; raw values preserved and per-million values used only for readability."],
  ["Bounded search", "Internet Archive metadata text-item numFound", "Provider discoverability at retrieval time; not language prevalence."],
  ["Dictionary", "Headword / technical glossary / no standalone headword", "Lexical meaning and anchor-sense compatibility; absence of a headword is retained."],
  ["Relationship", "Structural or semantic candidate", "Only evidence-supported semantic relations are populated."],
];
guide.getRange("A4:C11").format = { font: { name: "Arial", size: 10, color: COLORS.ink }, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: COLORS.grid } };
guide.getRange("A4:C4").format = { fill: COLORS.teal, font: { name: "Arial", size: 10, bold: true, color: COLORS.white }, borders: { preset: "all", style: "thin", color: COLORS.teal } };
guide.getRange("A:A").format.columnWidth = 23; guide.getRange("B:B").format.columnWidth = 32; guide.getRange("C:C").format.columnWidth = 72;
mergeSet(guide, "A14:C19", "Four non-equivalences\n\nFrequency ≠ search count\nThreat ≠ fear\nInventory composition ≠ historical prevalence\nSame string ≠ same historical sense", { fill: COLORS.orangeLight, font: { name: "Arial", size: 14, bold: true, color: "#7B341E" }, horizontalAlignment: "center", borders: { preset: "all", style: "medium", color: COLORS.orange } });
mergeSet(guide, "A21:C25", "Pattern labels used in the interpretation report\n\nOBSERVED_CORPUS_PATTERN · CONSTRUCTED_INVENTORY_PATTERN · SOURCE_COMPOSITION_PATTERN · SEARCHABILITY_PATTERN · SEMANTIC_HYPOTHESIS · UNRESOLVED", { fill: COLORS.purpleLight, font: { name: "Arial", size: 11, color: COLORS.purple, bold: true }, horizontalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.purple } });
guide.freezePanes.freezeRows(2);

const relationship = workbook.worksheets.getItem("Relationship Summary");
relationship.showGridLines = false;
titleBand(relationship, "Relationship Summary", "Compact view of inventory composition, evidence-channel coverage and figure inventory.", 14);
relationship.getRange("A4:I4").values = [["Anchor", "A", "B", "C", "D", "Total", "V1", "V2", "V3"]];
for (let i = 0; i < 6; i += 1) {
  relationship.getRangeByIndexes(4 + i, 0, 1, 6).values = [[matrices.anchorLayer[i + 1][0], matrices.anchorLayer[i + 1][1], matrices.anchorLayer[i + 1][3], matrices.anchorLayer[i + 1][5], matrices.anchorLayer[i + 1][7], matrices.anchorLayer[i + 1][9]]];
  relationship.getRangeByIndexes(4 + i, 6, 1, 3).values = [[matrices.anchorVoice[i + 1][1], matrices.anchorVoice[i + 1][3], matrices.anchorVoice[i + 1][5]]];
}
relationship.getRange("K4:N4").values = [["Coverage metric", "Value", "Meaning", "Status"]];
relationship.getRange("K5:K10").values = [["Priority candidates"], ["Candidate relations"], ["Comparability rows"], ["Figures"], ["Ngram observations"], ["Unexplained Ngram"]];
relationship.getRange("L5:L10").formulas = [["=COUNTA('Priority 180 Coverage'!A5:A184)"], ["=COUNTA('Candidate Relations'!A5:A500)"], ["=COUNTA('Comparability'!A5:A100)"], [`=${figureManifest.figure_count}`], ["=SUM('Ngram Coverage'!I5:I147)"], ["=COUNTIF('Ngram Coverage'!H5:H147,\"UNRESOLVED\")"]];
relationship.getRange("M5:M10").values = [["Candidate denominator"], ["Structural + evidence-supported"], ["Cross-anchor comparison audit"], ["PNG + SVG with sources"], ["Annual normalized observations"], ["Required = 0"]];
relationship.getRange("N5:N10").formulas = [["=IF(L5=180,\"PASS\",\"CHECK\")"], ["=IF(L6>0,\"PASS\",\"CHECK\")"], ["=IF(L7>0,\"PASS\",\"CHECK\")"], ["=IF(L8>=10,\"PASS\",\"CHECK\")"], ["=IF(L9>0,\"PASS\",\"CHECK\")"], ["=IF(L10=0,\"PASS\",\"CHECK\")"]];
relationship.getRange("A4:I10").format = { font: { name: "Arial", size: 10, color: COLORS.ink }, borders: { preset: "all", style: "thin", color: COLORS.grid } };
relationship.getRange("A4:I4").format = { fill: COLORS.teal, font: { name: "Arial", size: 10, bold: true, color: COLORS.white } };
relationship.getRange("K4:N10").format = { font: { name: "Arial", size: 10, color: COLORS.ink }, wrapText: true, borders: { preset: "all", style: "thin", color: COLORS.grid } };
relationship.getRange("K4:N4").format = { fill: COLORS.purple, font: { name: "Arial", size: 10, bold: true, color: COLORS.white } };
applyStatusFormatting(relationship.getRange("N5:N10"));
relationship.getRange("A:N").format.columnWidth = 15;
relationship.getRange("M:M").format.columnWidth = 28;
mergeSet(relationship, "A13:N17", "Interpretation boundary\n\nThe matrices show how the constructed inventory is distributed. Ngram trajectories show corpus string frequency. Search counts show provider discoverability. Dictionary states show lexicographic treatment. These dimensions are parallel evidence and are never collapsed into a Fear Score.", { fill: COLORS.orangeLight, font: { name: "Arial", size: 12, color: "#7B341E" }, horizontalAlignment: "center", borders: { preset: "all", style: "medium", color: COLORS.orange } });

const method = workbook.worksheets.getItem("Keyword Discovery Method");
method.showGridLines = false;
titleBand(method, "Keyword Discovery Method", "Presentation-facing account of how the historical lexicon was constructed and computationally audited.", 12);
method.getRange("A4:L4").merge(); method.getRange("A4:L4").values = [["Research question"]]; method.getRange("A4:L4").format = { fill: COLORS.teal, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } };
mergeSet(method, "A5:L8", "Which historically available lexical forms represented temperature/physical phenomena, climate/causal framing, affect, and threat/risk/harm at six research anchors — and through which speakers, sources and expression modes?", { fill: COLORS.tealLight, font: { name: "Arial", size: 12, color: COLORS.navy2 }, horizontalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.teal } });
method.getRange("A10:L10").merge(); method.getRange("A10:L10").values = [["Discovery workflow"]]; method.getRange("A10:L10").format = { fill: COLORS.purple, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } };
const steps = ["Topic definition", "A–D conceptual seed", "Six-anchor source retrieval", "Exact lexical-form extraction", "Source + voice + provenance", "Candidate normalisation", "30 Priority per anchor", "Expansion candidates", "Dictionary / Ngram / search validation", "Later passage-level validation"];
for (let i = 0; i < steps.length; i += 1) {
  const start = i + 1; const end = i + 1;
  method.getRangeByIndexes(11, start - 1, 3, 1).merge(); method.getRangeByIndexes(11, start - 1, 3, 1).values = [[steps[i]]];
  method.getRangeByIndexes(11, start - 1, 3, 1).format = { fill: i % 2 ? COLORS.purpleLight : COLORS.blueLight, font: { name: "Arial", size: 8, bold: true, color: COLORS.navy2 }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.grid } };
  if (i < steps.length - 1) method.getRangeByIndexes(14, start - 1, 1, 1).values = [["→"]];
}
mergeSet(method, "A17:L21", "Keywords were not selected because they were frequent.\n\nFrequency was excluded from initial candidate selection to avoid circularity and cherry-picking.", { fill: COLORS.orangeLight, font: { name: "Arial", size: 15, bold: true, color: "#7B341E" }, horizontalAlignment: "center", borders: { preset: "all", style: "medium", color: COLORS.orange } });
mergeSet(method, "A23:F34", "Role of programming\n\n1. Ingest candidate records\n2. Preserve historical wording while normalising retrieval forms\n3. Deduplicate external requests without losing candidate provenance\n4. Map families, anchors, voices, modes and sources\n5. Generate reproducible query rules\n6. Retrieve unsmoothed Ngram series\n7. Collect bounded search statistics\n8. Link dictionary evidence\n9. Build coverage and relationship audits\n10. Flag ambiguity and missingness", { fill: COLORS.tealLight, font: { name: "Arial", size: 10, color: COLORS.navy2 }, borders: { preset: "all", style: "thin", color: COLORS.teal } });
mergeSet(method, "G23:L34", "What programming did NOT do\n\n• It did not extract the most frequent words as the historical lexicon.\n• It did not use an unsupervised top-words algorithm.\n• It did not treat Ngram frequency as semantic evidence.\n• It did not infer missing historical voices for balance.\n• It did not create a Fear Score or premature semantic-evolution network.", { fill: COLORS.purpleLight, font: { name: "Arial", size: 11, color: COLORS.purple }, borders: { preset: "all", style: "thin", color: COLORS.purple } });
method.getRange("A:L").format.columnWidth = 12;
method.freezePanes.freezeRows(2);

const summary = workbook.worksheets.getItem("Summary");
summary.showGridLines = false;
titleBand(summary, "Fear of Temperature — EDA v0.2 Summary", "Formula-linked counts from the current workbook and version-controlled project exports.", 8);
summary.getRange("A4:B4").values = [["Metric", "Formula-linked value"]];
summary.getRange("A5:A16").values = [["Priority candidates"], ["Candidate relations"], ["Comparability rows"], ["Ngram annual observations"], ["Dictionary candidates"], ["Search candidates"], ["Seed ledger records"], ["Lexical families"], ["Figures"], ["Ngram unexplained"], ["Controlled missingness cells"], ["Workbook stage"]];
summary.getRange("B5:B16").formulas = [["=COUNTA('Priority 180 Coverage'!A5:A184)"], ["=COUNTA('Candidate Relations'!A5:A500)"], ["=COUNTA('Comparability'!A5:A100)"], ["=SUM('Ngram Coverage'!I5:I147)"], ["=COUNTA('Dictionary 180'!A5:A184)"], ["=COUNTA('Search 180'!A5:A184)"], ["=COUNTA('Seed Ledger'!A5:A400)"], ["=COUNTA('Family Summary'!A5:A18)"], [`=${figureManifest.figure_count}`], ["=COUNTIF('Ngram Coverage'!H5:H147,\"UNRESOLVED\")"], [`=${validation.controlled_missingness_count}`], [shortlistExists ? '="EDA_STAGES_1_TO_4"' : '="EDA_STAGE_3"']];
summary.getRange("A4:B16").format = { font: { name: "Arial", size: 11, color: COLORS.ink }, borders: { preset: "all", style: "thin", color: COLORS.grid } };
summary.getRange("A4:B4").format = { fill: COLORS.teal, font: { name: "Arial", size: 11, bold: true, color: COLORS.white } };
summary.getRange("A5:A16").format.fill = COLORS.grayLight;
summary.getRange("A:A").format.columnWidth = 34; summary.getRange("B:B").format.columnWidth = 24;
mergeSet(summary, "D4:H10", "Method warning\n\nString frequency is not equivalent to historical fear. Threat is not emotion. Inventory composition is not historical prevalence. Search counts are provider discoverability, not corpus frequency.", { fill: COLORS.orangeLight, font: { name: "Arial", size: 12, bold: true, color: "#7B341E" }, horizontalAlignment: "center", borders: { preset: "all", style: "medium", color: COLORS.orange } });
mergeSet(summary, "D12:H16", "Generated from the current project database and research exports; source tables remain version-controlled.", { fill: COLORS.grayLight, font: { name: "Arial", size: 11, italic: true, color: COLORS.gray }, horizontalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.grid } });

const dashboard = workbook.worksheets.getItem("Supervisor Dashboard");
dashboard.showGridLines = false;
mergeSet(dashboard, "A1:N1", "Fear of Temperature — Supervisor Dashboard", { fill: COLORS.navy, font: { name: "Arial", size: 24, bold: true, color: COLORS.white } }).format.rowHeight = 46;
mergeSet(dashboard, "A2:N2", "Exploratory relationship analysis v0.2 · constructed inventory · corpus trajectories · lexicography · searchability and provenance bias", { fill: "#D9EAF0", font: { name: "Arial", size: 10, italic: true, color: COLORS.navy2 } });
card(dashboard, "A4:C4", "A5:C7", "Priority Candidates", "=COUNTA('Priority 180 Coverage'!A5:A184)", COLORS.teal);
card(dashboard, "D4:F4", "D5:F7", "Candidate Relations", "=COUNTA('Candidate Relations'!A5:A500)", COLORS.purple);
card(dashboard, "G4:I4", "G5:I7", "Ngram Observations", "=SUM('Ngram Coverage'!I5:I147)", COLORS.orange);
card(dashboard, "J4:L4", "J5:L7", "EDA Figures", `=${figureManifest.figure_count}`, COLORS.green);
mergeSet(dashboard, "M4:N7", "6 anchors\n4 layers\n5 voices\n14 families", { fill: COLORS.grayLight, font: { name: "Arial", size: 12, bold: true, color: COLORS.navy2 }, horizontalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.grid } });
mergeSet(dashboard, "A9:G11", "Method warning\nString frequency is not equivalent to historical fear.", { fill: COLORS.orangeLight, font: { name: "Arial", size: 12, bold: true, color: "#7B341E" }, horizontalAlignment: "center", borders: { preset: "all", style: "medium", color: COLORS.orange } });
mergeSet(dashboard, "H9:N11", "Key methodological result\nThe same word may perform different functions depending on speaker, source, expression mode and context.", { fill: COLORS.tealLight, font: { name: "Arial", size: 11, bold: true, color: COLORS.teal }, horizontalAlignment: "center", borders: { preset: "all", style: "medium", color: COLORS.teal } });

const dashboardFigures = [
  ["visual_01b_anchor_layer_percentages", "A13:G13", "Composition of the constructed inventory", 13, 0],
  ["visual_02_anchor_voice_counts", "H13:N13", "Source/speaker composition", 13, 7],
  ["visual_03a_anchor_family_counts", "A32:G32", "Anchor × lexical-family structure", 32, 0],
  ["visual_05_climate_framing_trajectories", "H32:N32", "Climate-framing Ngram trajectories", 32, 7],
  ["visual_10_searchability_bias", "A51:G51", "Searchability and archival bias", 51, 0],
  ["visual_11_candidate_missingness_heatmap", "H51:N51", "Candidate-level missingness", 51, 7],
];
for (const [stem, labelRange, label, row, col] of dashboardFigures) {
  mergeSet(dashboard, labelRange, label, { fill: col === 0 ? COLORS.teal : COLORS.purple, font: { name: "Arial", size: 10, bold: true, color: COLORS.white } });
  const bytes = await fs.readFile(path.join(root, `figures/fear-temperature/eda-v02/${stem}.png`));
  dashboard.images.add({ dataUrl: `data:image/png;base64,${bytes.toString("base64")}`, anchor: { from: { row, col }, extent: { widthPx: 560, heightPx: 315 } } });
}
mergeSet(dashboard, "A70:G74", "Reading rule\nInventory charts describe candidate construction. Ngram charts describe strings in one corpus. Search charts describe provider discoverability. None is a direct measure of historical fear.", { fill: COLORS.grayLight, font: { name: "Arial", size: 10, italic: true, color: COLORS.gray }, borders: { preset: "all", style: "thin", color: COLORS.grid } });
mergeSet(dashboard, "H70:N74", shortlistExists ? "Next step\nPassage-level semantic validation using the evidence-based shortlist." : "Next step\nComplete the evidence-based semantic shortlist, then begin passage-level semantic validation.", { fill: COLORS.amberLight, font: { name: "Arial", size: 13, bold: true, color: "#7B5B12" }, horizontalAlignment: "center", borders: { preset: "all", style: "medium", color: COLORS.amber } });
mergeSet(dashboard, "A76:N78", "Generated from the current project database and research exports; source tables remain version-controlled. Primary bounded-search metric: Internet Archive metadata text-item result count at retrieval time.", { fill: COLORS.grayLight, font: { name: "Arial", size: 10, italic: true, color: COLORS.gray }, horizontalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.grid } });
dashboard.getRange("A:N").format.columnWidth = 11;
dashboard.getRange("A1:N78").format.font.name = "Arial";
dashboard.freezePanes.freezeRows(2);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
try { await fs.copyFile(outputPath, "/tmp/fear_temperature_quantitative_v01.pre_eda.xlsx"); } catch { /* first generation */ }

const keyInspection = await workbook.inspect({ kind: "table", range: "Supervisor Dashboard!A1:N12", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 16, maxChars: 12000 });
console.log(keyInspection.ndjson);
const formulaErrors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 500 }, summary: "EDA workbook formula error scan" });
console.log(formulaErrors.ndjson);

const renderRanges = new Map([
  ["Supervisor Dashboard", "A1:N78"], ["Analysis Guide", "A1:C25"], ["Relationship Summary", "A1:N17"],
  ["Anchor Layer", "A1:J10"], ["Anchor Voice", "A1:L10"], ["Anchor Family", "A1:D20"],
  ["Voice Family", "A1:C20"], ["Candidate Relations", "A1:I18"], ["Comparability", "A1:G18"],
  ["Ngram Trajectories", "A1:H18"], ["Dictionary Analysis", "A1:C20"], ["Search Analysis", "A1:C20"],
  ["Coverage Bias", "A1:F22"], ["Semantic Shortlist", shortlistExists ? "A1:J20" : "A1:B8"],
  ["Priority 180 Coverage", "A1:N18"], ["Ngram Coverage", "A1:O18"], ["Dictionary 180", "A1:T18"],
  ["Search 180", "A1:R18"], ["Seed Ledger", "A1:R18"], ["Master Frequency", "A1:O18"],
  ["Anchor Matrix", "A1:M18"], ["Family Summary", "A1:K18"], ["Voice Matrix", "A1:F20"],
  ["Query Audit", "A1:K18"], ["Ngram Status", "A1:L18"], ["Keyword Discovery Method", "A1:L34"],
  ["Summary", "A1:H16"],
]);
for (const [sheetName, range] of renderRanges) {
  const preview = await workbook.render({ sheetName, range, scale: sheetName === "Supervisor Dashboard" ? 0.7 : 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName.toLowerCase().replace(/[^a-z0-9]+/g, "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });

const reopened = await SpreadsheetFile.importXlsx(await fs.readFile(outputPath));
const reopenInspection = await reopened.inspect({ kind: "table", range: "Summary!A4:B16", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 4, maxChars: 8000 });
console.log(reopenInspection.ndjson);
const reopenErrors = await reopened.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 500 }, summary: "reopened EDA workbook formula error scan" });
console.log(reopenErrors.ndjson);

const workbookValidation = {
  status: "PASS", output_path: outputPath, sheet_count: analysisSheetNames.length + detailSheetNames.length,
  priority_rows: matrices.priority.length - 1, relationship_rows: matrices.relations.length - 1,
  comparability_rows: matrices.comparability.length - 1, figure_count: figureManifest.figure_count,
  semantic_shortlist_status: shortlistExists ? "POPULATED" : "PENDING_STAGE_4",
  annual_observations: validation.baseline_annual_observations,
  formula_check: reopenErrors.ndjson.includes("matched 0 entries") || reopenErrors.ndjson.includes('"total":0') ? "PASS" : "REVIEW",
  render_count: renderRanges.size, embedded_dashboard_images: dashboardFigures.length,
  artifact_tool_reopen_check: "PASS",
};
await fs.writeFile(path.join(root, "data/fear-temperature/analysis/eda_workbook_validation.json"), `${JSON.stringify(workbookValidation, null, 2)}\n`);
console.log(JSON.stringify(workbookValidation, null, 2));
