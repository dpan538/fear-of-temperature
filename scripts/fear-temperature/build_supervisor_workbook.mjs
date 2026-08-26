#!/usr/bin/env node
/** Regenerate the canonical supervisor workbook from version-controlled exports. */

import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "/Users/jarlgiovanni/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const root = "/Users/jarlgiovanni/Desktop/fear_of_temperature";
const outputDir = path.join(root, "outputs", "quantitative-v01");
const previewDir = "/tmp/fear_temperature_supervisor_previews";
const outputPath = path.join(outputDir, "fear_temperature_quantitative_v01.xlsx");
const validationPath = path.join(root, "data/fear-temperature/exports/supervisor_workbook_validation.json");

const COLORS = {
  navy: "#102A43", navy2: "#17324D", teal: "#0B6E75", tealLight: "#D9F0F0",
  purple: "#6B5CA5", purpleLight: "#F3F0F8", orange: "#C65D3B", orangeLight: "#FFF3EC",
  amber: "#D49B28", amberLight: "#FFF8E7", green: "#2E7D5B", greenLight: "#E7F4ED",
  red: "#B42318", redLight: "#FDECEC", gray: "#667085", grayLight: "#F2F4F7",
  blueLight: "#E8F1FB", ink: "#243B53", grid: "#D9E2EC", white: "#FFFFFF",
};

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
  const h = header.toLowerCase();
  if (["rank", "priority_rank", "priority rank"].includes(h)) return true;
  if (h.includes("frequency") || h.includes(" mean") || h.endsWith("_mean") || h.includes("median") || h.includes("maximum")) return true;
  if (h.includes("result count") || h.includes("observation count") || h.includes("total_results") || h.includes("members_") || h.includes("query_rule_count")) return true;
  if (h === "year" || h.endsWith("_year") || h.includes("year start") || h.includes("year end") || h === "latest_supported_year") return true;
  if (/^(1842|1938|1988|2006|2007|2015|2022)(_value)?$/.test(h)) return true;
  if (h.includes("_value") || h.endsWith("_count") || h.includes("per million")) return true;
  return false;
}

function typedMatrix(parsed) {
  const headers = parsed[0];
  const rows = parsed.slice(1).map((sourceRow) => sourceRow.map((value, index) => {
    const trimmed = value.trim();
    if (isNumericHeader(headers[index]) && /^-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) return Number(trimmed);
    if (["true", "false"].includes(trimmed.toLowerCase())) return trimmed.toLowerCase() === "true";
    return trimmed;
  }));
  return [headers, ...rows];
}

async function loadCsv(relativePath) {
  return typedMatrix(parseCsv(await fs.readFile(path.join(root, relativePath), "utf8")));
}

function headerIndexMap(headers) { return Object.fromEntries(headers.map((header, index) => [header, index])); }

function styleTitle(sheet, title, note, colCount) {
  const last = columnLetter(Math.max(colCount - 1, 7));
  sheet.getRange(`A1:${last}1`).merge();
  sheet.getRange(`A1:${last}1`).values = [[title]];
  sheet.getRange(`A1:${last}1`).format = { fill: COLORS.navy, font: { name: "Arial", size: 18, bold: true, color: COLORS.white }, verticalAlignment: "center" };
  sheet.getRange(`A1:${last}1`).format.rowHeight = 38;
  sheet.getRange(`A2:${last}2`).merge();
  sheet.getRange(`A2:${last}2`).values = [[note]];
  sheet.getRange(`A2:${last}2`).format = { fill: "#D9EAF0", font: { name: "Arial", size: 10, italic: true, color: COLORS.navy2 }, wrapText: true, verticalAlignment: "center" };
  sheet.getRange(`A2:${last}2`).format.rowHeight = 31;
}

function preferredWidth(header) {
  const h = header.toLowerCase();
  if (h.includes("note") || h.includes("sense") || h.includes("definition") || h.includes("provenance") || h.includes("reason") || h.includes("warning")) return 42;
  if (h.includes("url") || h.includes("path") || h.includes("interface") || h.includes("citation")) return 38;
  if (h.includes("surface") || h.includes("measurement form") || h.includes("query string") || h.includes("normalised concept") || h.includes("members")) return 26;
  if (h.includes("status") || h.includes("match") || h.includes("exactness") || h.includes("classification") || h.includes("mapping") || h.includes("missingness")) return 23;
  if (h.includes("candidate id") || h.includes("query id") || h.includes("source id") || h.includes("original_candidate_id")) return 24;
  if (isNumericHeader(header)) return 17;
  if (h.includes("timestamp") || h.includes("retrieved at") || h.includes("access date")) return 21;
  return 16;
}

function applyStatusFormatting(range) {
  range.conditionalFormats.add("containsText", { text: "FULLY", format: { fill: COLORS.greenLight, font: { color: COLORS.green, bold: true } } });
  range.conditionalFormats.add("containsText", { text: "SUCCESS", format: { fill: COLORS.greenLight, font: { color: COLORS.green } } });
  range.conditionalFormats.add("containsText", { text: "DIRECT_HEADWORD", format: { fill: COLORS.greenLight, font: { color: COLORS.green } } });
  range.conditionalFormats.add("containsText", { text: "TECHNICAL_GLOSSARY", format: { fill: COLORS.tealLight, font: { color: COLORS.teal } } });
  range.conditionalFormats.add("containsText", { text: "ZERO", format: { fill: COLORS.amberLight, font: { color: "#7B5B12", bold: true } } });
  range.conditionalFormats.add("containsText", { text: "UNRESOLVED", format: { fill: COLORS.redLight, font: { color: COLORS.red, bold: true } } });
  range.conditionalFormats.add("containsText", { text: "PENDING", format: { fill: COLORS.redLight, font: { color: COLORS.red } } });
  range.conditionalFormats.add("containsText", { text: "NOT_EXPOSED", format: { fill: COLORS.blueLight, font: { color: "#175CD3" } } });
  range.conditionalFormats.add("containsText", { text: "NOT_ANNOTATED", format: { fill: COLORS.blueLight, font: { color: "#175CD3" } } });
  range.conditionalFormats.add("containsText", { text: "NOT_LOCATED", format: { fill: COLORS.purpleLight, font: { color: COLORS.purple } } });
  range.conditionalFormats.add("containsText", { text: "NOT_APPLICABLE", format: { fill: COLORS.grayLight, font: { color: COLORS.gray } } });
}

function addTableSheet(workbook, name, matrix, title, note, options = {}) {
  const sheet = workbook.worksheets.add(name);
  const headers = matrix[0];
  const dataCount = matrix.length - 1;
  const colCount = headers.length;
  const lastCol = columnLetter(colCount - 1);
  const endRow = 4 + dataCount;
  sheet.showGridLines = false;
  styleTitle(sheet, title, note, colCount);
  sheet.getRangeByIndexes(3, 0, matrix.length, colCount).values = matrix;
  const table = sheet.tables.add(`A4:${lastCol}${endRow}`, true, options.tableName || name.replace(/[^A-Za-z0-9]/g, "") + "Table");
  table.style = options.tableStyle || "TableStyleMedium2";
  table.showFilterButton = true;
  const used = sheet.getRange(`A4:${lastCol}${endRow}`);
  used.format.font = { name: "Arial", size: options.fontSize || 9, color: COLORS.ink };
  used.format.verticalAlignment = "top";
  const header = sheet.getRange(`A4:${lastCol}4`);
  header.format = { fill: options.headerFill || COLORS.navy2, font: { name: "Arial", size: 9, bold: true, color: COLORS.white }, wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.grid } };
  header.format.rowHeight = 42;
  if (dataCount) {
    const body = sheet.getRangeByIndexes(4, 0, dataCount, colCount);
    body.format.rowHeight = options.rowHeight || 25;
    body.format.borders = { preset: "inside", style: "thin", color: "#E8EEF3" };
  }
  headers.forEach((columnName, index) => {
    const range = sheet.getRangeByIndexes(3, index, matrix.length, 1);
    const width = preferredWidth(columnName);
    range.format.columnWidth = width;
    if (width >= 23) range.format.wrapText = true;
    if (isNumericHeader(columnName) && dataCount) {
      sheet.getRangeByIndexes(4, index, dataCount, 1).format.numberFormat = columnName.toLowerCase().includes("count") || columnName.toLowerCase().includes("year") || columnName === "Rank" ? "0" : "0.0000000000E+00";
    }
    if (/timestamp|retrieved at|access date/i.test(columnName) && dataCount) sheet.getRangeByIndexes(4, index, dataCount, 1).format.numberFormat = "yyyy-mm-dd hh:mm:ss";
    if (/status|match|mapping|gap|priority|missingness|exactness/i.test(columnName) && dataCount) applyStatusFormatting(sheet.getRangeByIndexes(4, index, dataCount, 1));
  });
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(options.freezeColumns || 3);
  return { sheet, headers, headerMap: headerIndexMap(headers), dataCount, endRow, matrix };
}

function box(range, fill, fontColor = COLORS.ink, bold = false) {
  range.format = { fill, font: { name: "Arial", size: 10, color: fontColor, bold }, wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.grid } };
}

function mergeSet(sheet, address, value, format = {}) {
  const range = sheet.getRange(address);
  range.merge();
  range.values = [[value]];
  range.format = { wrapText: true, verticalAlignment: "center", ...format };
  return range;
}

function findRowForTerm(sheetInfo, term) {
  const surfaceIndex = sheetInfo.headerMap.surface_form;
  const rowIndex = sheetInfo.matrix.slice(1).findIndex((row) => String(row[surfaceIndex]).toLowerCase() === term.toLowerCase());
  if (rowIndex < 0) throw new Error(`Term not found in Master Frequency: ${term}`);
  return 5 + rowIndex;
}

function sourceFormula(sheetInfo, term, header) {
  return `='Master Frequency'!$${columnLetter(sheetInfo.headerMap[header])}$${findRowForTerm(sheetInfo, term)}`;
}

const workbook = Workbook.create();
const dashboard = workbook.worksheets.add("Supervisor Dashboard");
const method = workbook.worksheets.add("Keyword Discovery Method");
const summary = workbook.worksheets.add("Summary");

const priorityMatrix = await loadCsv("data/fear-temperature/exports/priority180_supervisor_coverage.csv");
const ngramMatrix = await loadCsv("data/fear-temperature/exports/ngram_supervisor_coverage.csv");
const ngramExceptionMatrix = await loadCsv("data/fear-temperature/exports/ngram_candidate_mapping_exceptions.csv");
const dictionaryMatrix = await loadCsv("data/fear-temperature/exports/dictionary_supervisor_180.csv");
const searchMatrix = await loadCsv("data/fear-temperature/exports/search_supervisor_180.csv");
const seedMatrix = await loadCsv("data/fear-temperature/exports/seed_ledger_supervisor.csv");
const masterMatrix = await loadCsv("data/fear-temperature/exports/keyword_frequency_summary.csv");
const anchorMatrix = await loadCsv("data/fear-temperature/exports/anchor_keyword_frequency_matrix.csv");
const familyMatrix = await loadCsv("data/fear-temperature/exports/lexical_family_frequency_summary.csv");
const voiceMatrix = await loadCsv("data/fear-temperature/exports/voice_keyword_matrix.csv");
const queryAuditMatrix = await loadCsv("data/fear-temperature/exports/ngram_compatibility_audit.csv");
const ngramStatusMatrix = await loadCsv("data/fear-temperature/ngram/ngram_query_execution_results.csv");
const validation = JSON.parse(await fs.readFile(validationPath, "utf8"));

const priorityInfo = addTableSheet(workbook, "Priority 180 Coverage", priorityMatrix, "Priority 180 - Complete Candidate-Level Coverage", "Exactly 180 Priority Candidates. Ngram, dictionary, bounded search, provenance and remaining annotation limitations are shown together; duplicated surface strings remain separate candidate records.", { tableName: "Priority180CoverageTable", freezeColumns: 4, rowHeight: 34 });
const ngramInfo = addTableSheet(workbook, "Ngram Coverage", ngramMatrix, "Ngram Coverage and Rule Reconciliation", "All 143 provisional query rules are retained: 132 successful non-zero series, 6 zero results and 5 technically incompatible rules. NGRAM_UNEXPLAINED = 0. Observation Count is numeric and formula-summed in Summary.", { tableName: "NgramCoverageTable", freezeColumns: 3, rowHeight: 27 });

const exceptionStartCol = 16;
const exceptionLastLetter = columnLetter(exceptionStartCol + ngramExceptionMatrix[0].length - 1);
ngramInfo.sheet.getRangeByIndexes(0, exceptionStartCol, 1, ngramExceptionMatrix[0].length).merge();
ngramInfo.sheet.getRangeByIndexes(0, exceptionStartCol, 1, ngramExceptionMatrix[0].length).values = [["Priority candidate mapping exceptions"]];
ngramInfo.sheet.getRangeByIndexes(0, exceptionStartCol, 1, ngramExceptionMatrix[0].length).format = { fill: COLORS.purple, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } };
ngramInfo.sheet.getRangeByIndexes(1, exceptionStartCol, 1, ngramExceptionMatrix[0].length).merge();
ngramInfo.sheet.getRangeByIndexes(1, exceptionStartCol, 1, ngramExceptionMatrix[0].length).values = [["Two normalized variants, three validated aliases and one technically unrepresentable Priority Candidate; each remains visible below."]];
ngramInfo.sheet.getRangeByIndexes(1, exceptionStartCol, 1, ngramExceptionMatrix[0].length).format = { fill: COLORS.purpleLight, font: { name: "Arial", size: 9, italic: true, color: COLORS.purple }, wrapText: true };
ngramInfo.sheet.getRangeByIndexes(3, exceptionStartCol, ngramExceptionMatrix.length, ngramExceptionMatrix[0].length).values = ngramExceptionMatrix;
const exceptionEndRow = 4 + ngramExceptionMatrix.length - 1;
const exceptionTable = ngramInfo.sheet.tables.add(`Q4:${exceptionLastLetter}${exceptionEndRow}`, true, "NgramCandidateExceptionsTable");
exceptionTable.style = "TableStyleMedium4";
exceptionTable.showFilterButton = true;
ngramInfo.sheet.getRange(`Q4:${exceptionLastLetter}4`).format = { fill: COLORS.purple, font: { name: "Arial", size: 9, bold: true, color: COLORS.white }, wrapText: true };
ngramExceptionMatrix[0].forEach((header, idx) => {
  const width = preferredWidth(header);
  ngramInfo.sheet.getRangeByIndexes(3, exceptionStartCol + idx, ngramExceptionMatrix.length, 1).format.columnWidth = width;
  if (width >= 23) ngramInfo.sheet.getRangeByIndexes(3, exceptionStartCol + idx, ngramExceptionMatrix.length, 1).format.wrapText = true;
});

const dictionaryInfo = addTableSheet(workbook, "Dictionary 180", dictionaryMatrix, "Dictionary and Lexicographic Coverage - 180 Candidates", "Definitions are concise paraphrases with source attribution. NO_STANDALONE_HEADWORD marks phrases supported by component, historical or technical evidence rather than an invented dictionary entry.", { tableName: "Dictionary180Table", freezeColumns: 4, rowHeight: 38 });
const searchInfo = addTableSheet(workbook, "Search 180", searchMatrix, "Bounded and Reproducible Search Coverage - 180 Candidates", "Primary metric: Internet Archive Advanced Search API numFound at retrieval time. It is a discovery-result count, not lexical prevalence. Strict/contextual counts use supported date filters; ordinary Google web estimates are excluded.", { tableName: "Search180Table", freezeColumns: 4, rowHeight: 34 });
const seedInfo = addTableSheet(workbook, "Seed Ledger", seedMatrix, "Provisional Seed Ledger - 396 Provenance-Bearing Records", "INITIAL_180 evidence IDs are recovered from the report's Evidence source column. Later voice/mode/source gaps use controlled missingness states; no original candidate IDs are fabricated.", { tableName: "SeedLedgerTable", freezeColumns: 3, rowHeight: 32 });
const masterInfo = addTableSheet(workbook, "Master Frequency", masterMatrix, "Keyword Frequency Master Table", "Annual normalized Google Books Ngram values and descriptive statistics. Generic forms remain semantically ambiguous; family members are never summed.", { tableName: "MasterFrequencyTable", rowHeight: 23 });
addTableSheet(workbook, "Anchor Matrix", anchorMatrix, "Six-Anchor Keyword Frequency Matrix", "Raw normalized frequencies for 1842, 1938, 1988, 2006, 2007, the labelled 2006-07 mean, 2015 and 2022/latest.", { tableName: "AnchorMatrixTable", rowHeight: 23 });
addTableSheet(workbook, "Family Summary", familyMatrix, "Lexical Family Frequency Summary", "Fourteen semantic families. Member trajectories are described individually; no overlapping strings are summed into a composite index.", { tableName: "FamilySummaryTable", rowHeight: 40 });
addTableSheet(workbook, "Voice Matrix", voiceMatrix, "Six Anchors x Five Voices", "Evidence-backed coverage only. Historically unsupported cells remain visible rather than being filled for symmetry.", { tableName: "VoiceMatrixTable", rowHeight: 44 });
addTableSheet(workbook, "Query Audit", queryAuditMatrix, "Ngram Compatibility Audit", "Compatibility, reason and provenance for every provisional query rule, including corpus-only and symbol-dependent exclusions.", { tableName: "QueryAuditTable", rowHeight: 30 });
addTableSheet(workbook, "Ngram Status", ngramStatusMatrix, "Raw Ngram Execution Status", "Provider response accounting, raw-response checksums, timestamps and explicit zero/incompatible outcomes.", { tableName: "NgramStatusTable", rowHeight: 27 });

summary.showGridLines = false;
mergeSet(summary, "A1:H1", "Fear of Temperature - Quantitative and Lexicographic Baseline v0.1", { fill: COLORS.navy, font: { name: "Arial", size: 21, bold: true, color: COLORS.white } }).format.rowHeight = 42;
mergeSet(summary, "A2:H2", "Formula-linked summary · provisional provenance-labelled research baseline · 1842-2022", { fill: "#D9EAF0", font: { name: "Arial", size: 10, italic: true, color: COLORS.navy2 } });
summary.getRange("A4:B4").values = [["Research status", "Value"]];
summary.getRange("A4:B4").format = { fill: COLORS.teal, font: { name: "Arial", bold: true, color: COLORS.white } };
summary.getRange("A5:A23").values = [["Research version"], ["Query rules"], ["Ngram-executable"], ["Successful non-zero series"], ["Zero-result series"], ["Failed requests"], ["Not run - incompatible"], ["Annual observations"], ["Year start"], ["Year end"], ["Seed ledger records"], ["Priority candidates"], ["Dictionary candidate rows"], ["Search candidate rows"], ["Lexical families"], ["Voice x anchor cells"], ["Ngram unexplained"], ["Blank annotation metadata"], ["Controlled missingness cells"]];
summary.getRange("B5").values = [["fear-temperature-quant-v0.1-provisional"]];
summary.getRange("B6:B23").formulas = [
  ["=COUNTA('Ngram Coverage'!A5:A147)"], ["=COUNTIF('Ngram Coverage'!G5:G147,\"SUCCEEDED\")+COUNTIF('Ngram Coverage'!G5:G147,\"ZERO_RESULT\")+COUNTIF('Ngram Coverage'!G5:G147,\"FAILED\")"],
  ["=COUNTIF('Ngram Coverage'!G5:G147,\"SUCCEEDED\")"], ["=COUNTIF('Ngram Coverage'!G5:G147,\"ZERO_RESULT\")"],
  ["=COUNTIF('Ngram Coverage'!G5:G147,\"FAILED\")"], ["=COUNTIF('Ngram Coverage'!G5:G147,\"NOT_RUN_INCOMPATIBLE\")"],
  ["=SUM('Ngram Coverage'!I5:I147)"], ["=MIN('Master Frequency'!J5:J147)"], ["=MAX('Master Frequency'!K5:K147)"],
  ["=COUNTA('Seed Ledger'!A5:A400)"], ["=COUNTA('Priority 180 Coverage'!A5:A184)"], ["=COUNTA('Dictionary 180'!A5:A184)"],
  ["=COUNTA('Search 180'!A5:A184)"], ["=COUNTA('Family Summary'!A5:A18)"], ["=COUNTA('Voice Matrix'!A5:A34)"],
  ["=COUNTIF('Ngram Coverage'!H5:H147,\"UNRESOLVED\")"], ["=COUNTBLANK('Seed Ledger'!H5:J400)"], [`=${validation.controlled_missingness_count}`],
];
box(summary.getRange("A5:B23"), COLORS.white);
summary.getRange("A5:A23").format.fill = "#EEF4F7";
summary.getRange("A5:A23").format.font = { name: "Arial", size: 10, bold: true, color: COLORS.navy2 };
summary.getRange("B12").format = { fill: COLORS.greenLight, font: { name: "Arial", size: 12, bold: true, color: COLORS.green }, borders: { preset: "all", style: "thin", color: COLORS.green } };
summary.getRange("A12").format = { fill: COLORS.greenLight, font: { name: "Arial", size: 10, bold: true, color: COLORS.green }, borders: { preset: "all", style: "thin", color: COLORS.green } };
mergeSet(summary, "D4:H4", "Data-supported quantitative observations", { fill: COLORS.purple, font: { name: "Arial", size: 11, bold: true, color: COLORS.white } });
summary.getRange("D5:F10").values = [["Term", "1988 per million", "2022 per million"], ["climate change", null, null], ["climatic change", null, null], ["greenhouse effect", null, null], ["global warming", null, null], ["climate anxiety", null, null]];
summary.getRange("E6:E10").formulas = ["climate change", "climatic change", "greenhouse effect", "global warming", "climate anxiety"].map((term) => [sourceFormula(masterInfo, term, "1988_value") + "*1000000"]);
summary.getRange("F6:F10").formulas = ["climate change", "climatic change", "greenhouse effect", "global warming", "climate anxiety"].map((term) => [sourceFormula(masterInfo, term, "2022_value") + "*1000000"]);
box(summary.getRange("D5:F10"), COLORS.purpleLight);
summary.getRange("D5:F5").format = { fill: COLORS.purple, font: { name: "Arial", bold: true, color: COLORS.white }, borders: { preset: "all", style: "thin", color: COLORS.grid } };
summary.getRange("E6:F10").format.numberFormat = "0.0000";
mergeSet(summary, "D12:H14", "String frequency is not equivalent to historical fear. Generic strings can occur in unrelated senses, and Ngram does not identify speaker, source, expression mode or reception.", { fill: COLORS.orangeLight, font: { name: "Arial", size: 11, bold: true, color: "#7B341E" }, borders: { preset: "all", style: "thin", color: COLORS.orange } });
mergeSet(summary, "D16:H18", "The same word may perform different historical and social functions depending on speaker, source, expression mode and context.", { fill: COLORS.tealLight, font: { name: "Arial", size: 11, bold: true, color: COLORS.teal }, borders: { preset: "all", style: "thin", color: COLORS.teal } });
mergeSet(summary, "D20:H23", "Generated from the current project database and research exports; source tables remain version-controlled. Search counts are Internet Archive discovery-result counts reported by the API, not language prevalence.", { fill: COLORS.grayLight, font: { name: "Arial", size: 10, italic: true, color: COLORS.gray }, borders: { preset: "all", style: "thin", color: COLORS.grid } });
summary.getRange("A:H").format.font.name = "Arial";
summary.getRange("A:A").format.columnWidth = 28;
summary.getRange("B:B").format.columnWidth = 24;
summary.getRange("C:C").format.columnWidth = 3;
summary.getRange("D:H").format.columnWidth = 19;
summary.freezePanes.freezeRows(2);

method.showGridLines = false;
mergeSet(method, "A1:N1", "Keyword Discovery Method", { fill: COLORS.navy, font: { name: "Arial", size: 22, bold: true, color: COLORS.white } }).format.rowHeight = 42;
mergeSet(method, "A2:N2", "How the historical lexicon was built before frequency measurement", { fill: "#D9EAF0", font: { name: "Arial", size: 11, italic: true, color: COLORS.navy2 } });
mergeSet(method, "A4:N4", "Research question", { fill: COLORS.teal, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } });
mergeSet(method, "A5:N6", "Which vocabulary was historically available for temperature/physical phenomena, climate/causal framing, affect, and threat/risk/harm - and how did its function depend on anchor, speaker, source and expression mode?", { fill: COLORS.tealLight, font: { name: "Arial", size: 11, color: COLORS.navy2 }, borders: { preset: "all", style: "thin", color: COLORS.teal } });
mergeSet(method, "A8:N8", "Discovery workflow", { fill: COLORS.purple, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } });
const workflowTop = ["Topic definition", "→", "A-D conceptual seed", "→", "Historical source retrieval at six anchors", "→", "Exact lexical-form extraction", "→", "Source + voice + provenance annotation"];
const workflowTopRanges = ["A10:B12", "C10:C12", "D10:E12", "F10:F12", "G10:H12", "I10:I12", "J10:K12", "L10:L12", "M10:N12"];
workflowTopRanges.forEach((address, index) => mergeSet(method, address, workflowTop[index], { fill: index % 2 ? COLORS.white : COLORS.purpleLight, font: { name: "Arial", size: index % 2 ? 18 : 10, bold: index % 2 === 0, color: index % 2 ? COLORS.purple : COLORS.ink }, borders: { preset: "all", style: "thin", color: COLORS.grid }, horizontalAlignment: "center" }));
const workflowBottom = ["Candidate normalisation", "→", "30 Priority Candidates per anchor", "→", "Additional Expansion Candidates", "→", "Dictionary / Ngram / search validation", "→", "Later passage-level semantic validation"];
const workflowBottomRanges = ["A14:B16", "C14:C16", "D14:E16", "F14:F16", "G14:H16", "I14:I16", "J14:K16", "L14:L16", "M14:N16"];
workflowBottomRanges.forEach((address, index) => mergeSet(method, address, workflowBottom[index], { fill: index % 2 ? COLORS.white : COLORS.tealLight, font: { name: "Arial", size: index % 2 ? 18 : 10, bold: index % 2 === 0, color: index % 2 ? COLORS.teal : COLORS.ink }, borders: { preset: "all", style: "thin", color: COLORS.grid }, horizontalAlignment: "center" }));
mergeSet(method, "A18:N18", "CRITICAL METHODOLOGICAL POINT", { fill: COLORS.orange, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } });
mergeSet(method, "A19:N22", "Keywords were not selected because they were frequent. Frequency was intentionally excluded from initial candidate selection to avoid circularity and cherry-picking. Candidate construction began from conceptual scope and historical source evidence; quantitative measures were added only after the lexical forms and provenance were recorded.", { fill: COLORS.orangeLight, font: { name: "Arial", size: 12, bold: true, color: "#7B341E" }, borders: { preset: "all", style: "medium", color: COLORS.orange } });
mergeSet(method, "A24:G24", "Role of programming", { fill: COLORS.teal, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } });
mergeSet(method, "H24:N24", "What programming did NOT do", { fill: COLORS.purple, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } });
const roleText = ["1. Ingest candidate records.", "2. Normalise forms without erasing historical wording.", "3. Deduplicate identical retrieval requests while preserving candidate provenance.", "4. Map terms into lexical families.", "5. Associate anchors, voices, modes and sources.", "6. Generate reproducible query rules.", "7. Run Ngram frequency retrieval.", "8. Collect bounded search statistics.", "9. Connect dictionary evidence.", "10. Create coverage audits, flag ambiguity/missing metadata and prepare semantic validation."].join("\n");
const notText = ["- It did not simply extract the most frequent words.", "- It did not use an unsupervised 'top words' algorithm as the historical lexicon.", "- It did not treat Ngram frequency as semantic evidence.", "- It did not infer missing historical voices for balance."].join("\n\n");
mergeSet(method, "A25:G36", roleText, { fill: COLORS.tealLight, font: { name: "Arial", size: 10, color: COLORS.ink }, borders: { preset: "all", style: "thin", color: COLORS.teal } });
mergeSet(method, "H25:N36", notText, { fill: COLORS.purpleLight, font: { name: "Arial", size: 11, color: COLORS.ink }, borders: { preset: "all", style: "thin", color: COLORS.purple } });
method.getRange("A:N").format.columnWidth = 11;
method.getRange("A1:N36").format.font.name = "Arial";
method.freezePanes.freezeRows(2);

dashboard.showGridLines = false;
mergeSet(dashboard, "A1:N1", "Fear of Temperature - Supervisor Dashboard", { fill: COLORS.navy, font: { name: "Arial", size: 24, bold: true, color: COLORS.white } }).format.rowHeight = 46;
mergeSet(dashboard, "A2:N2", "Six anchors · four lexical layers · five voices · fourteen semantic families · provisional quantitative and lexicographic audit", { fill: "#D9EAF0", font: { name: "Arial", size: 11, italic: true, color: COLORS.navy2 } });
mergeSet(dashboard, "A4:D4", "Study design", { fill: COLORS.teal, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } });
mergeSet(dashboard, "E4:H4", "Priority-180 coverage", { fill: COLORS.purple, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } });
mergeSet(dashboard, "I4:N4", "Status legend", { fill: COLORS.gray, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } });
dashboard.getRange("A5:C10").values = [["Historical anchors", null, "6 positions"], ["Priority Candidates", null, "30 per anchor"], ["Expansion Candidates", null, "Separate denominator"], ["Lexical layers", 4, "A-D"], ["Voices", null, "V1-V5"], ["Lexical families", null, "Not synonym sets"]];
dashboard.getRange("B5:B7").formulas = [["=COUNTA('Voice Matrix'!A5:A34)/5"], ["=COUNTIF('Seed Ledger'!B5:B400,\"PRIORITY_180\")"], ["=COUNTIF('Seed Ledger'!B5:B400,\"EXPANSION_36\")"]];
dashboard.getRange("B9:B10").formulas = [["=COUNTA('Voice Matrix'!A5:A34)/6"], ["=COUNTA('Family Summary'!A5:A18)"]];
box(dashboard.getRange("A5:C10"), COLORS.tealLight);
dashboard.getRange("A5:A10").format.font = { name: "Arial", size: 10, bold: true, color: COLORS.teal };
dashboard.getRange("B5:B10").format.font = { name: "Arial", size: 14, bold: true, color: COLORS.navy };
dashboard.getRange("E5:G10").values = [["Ngram accounted", null, "180 / 180"], ["Dictionary accounted", null, "180 / 180"], ["Search accounted", null, "180 / 180"], ["Ngram unexplained", null, "Required: 0"], ["Blank annotation metadata", null, "Required: 0"], ["Controlled missingness cells", validation.controlled_missingness_count, "Visible limitations"]];
dashboard.getRange("F5:F9").formulas = [["=COUNTA('Priority 180 Coverage'!A5:A184)"], ["=COUNTA('Dictionary 180'!A5:A184)"], ["=COUNTA('Search 180'!A5:A184)"], ["=COUNTIF('Ngram Coverage'!H5:H147,\"UNRESOLVED\")"], ["=COUNTBLANK('Seed Ledger'!H5:J400)"]];
box(dashboard.getRange("E5:G10"), COLORS.purpleLight);
dashboard.getRange("E5:E10").format.font = { name: "Arial", size: 10, bold: true, color: COLORS.purple };
dashboard.getRange("F5:F10").format.font = { name: "Arial", size: 14, bold: true, color: COLORS.navy };
mergeSet(dashboard, "I5:N5", "COMPLETE / ACCOUNTED", { fill: COLORS.greenLight, font: { name: "Arial", size: 10, bold: true, color: COLORS.green }, borders: { preset: "all", style: "thin", color: COLORS.green } });
mergeSet(dashboard, "I6:N6", "ZERO RESULT - retained as a finding", { fill: COLORS.amberLight, font: { name: "Arial", size: 10, bold: true, color: "#7B5B12" }, borders: { preset: "all", style: "thin", color: COLORS.amber } });
mergeSet(dashboard, "I7:N7", "UNRESOLVED / PENDING REVIEW", { fill: COLORS.redLight, font: { name: "Arial", size: 10, bold: true, color: COLORS.red }, borders: { preset: "all", style: "thin", color: COLORS.red } });
mergeSet(dashboard, "I8:N8", "NOT APPLICABLE", { fill: COLORS.grayLight, font: { name: "Arial", size: 10, bold: true, color: COLORS.gray }, borders: { preset: "all", style: "thin", color: COLORS.gray } });
mergeSet(dashboard, "I9:N10", "SOURCE / PROVENANCE LIMITATION - explicitly labelled; not inferred", { fill: COLORS.blueLight, font: { name: "Arial", size: 10, bold: true, color: "#175CD3" }, borders: { preset: "all", style: "thin", color: "#175CD3" } });

mergeSet(dashboard, "A12:N12", "Key quantitative findings - annual normalized Ngram frequency (occurrences per million)", { fill: COLORS.purple, font: { name: "Arial", size: 12, bold: true, color: COLORS.white } });
dashboard.getRange("A13:E18").values = [["Term", "1988", "2022", "Peak year", "Peak per million"], ["climatic change", null, null, null, null], ["greenhouse effect", null, null, null, null], ["global warming", null, null, null, null], ["climate change", null, null, null, null], ["climate crisis", null, null, null, null]];
const keyTerms = ["climatic change", "greenhouse effect", "global warming", "climate change", "climate crisis"];
dashboard.getRange("B14:B18").formulas = keyTerms.map((term) => [sourceFormula(masterInfo, term, "1988_value") + "*1000000"]);
dashboard.getRange("C14:C18").formulas = keyTerms.map((term) => [sourceFormula(masterInfo, term, "2022_value") + "*1000000"]);
dashboard.getRange("D14:D18").formulas = keyTerms.map((term) => [sourceFormula(masterInfo, term, "peak_year")]);
dashboard.getRange("E14:E18").formulas = keyTerms.map((term) => [sourceFormula(masterInfo, term, "peak_frequency") + "*1000000"]);
box(dashboard.getRange("A13:E18"), COLORS.white);
dashboard.getRange("A13:E13").format = { fill: COLORS.navy2, font: { name: "Arial", size: 9, bold: true, color: COLORS.white }, borders: { preset: "all", style: "thin", color: COLORS.grid } };
dashboard.getRange("B14:C18").format.numberFormat = "0.0000";
dashboard.getRange("E14:E18").format.numberFormat = "0.0000";
dashboard.getRange("G13:J18").values = [["Modern compound", "2022 per million", "Peak year", "Interpretation"], ["climate crisis", null, null, "climate-specific threat frame"], ["climate emergency", null, null, "climate-specific emergency frame"], ["climate anxiety", null, null, "often researcher-defined construct"], ["eco-anxiety", null, null, "often researcher-defined construct"], ["Search metric", 180, null, "Internet Archive API candidate rows"]];
const modernTerms = ["climate crisis", "climate emergency", "climate anxiety", "eco-anxiety"];
dashboard.getRange("H14:H17").formulas = modernTerms.map((term) => [sourceFormula(masterInfo, term, "2022_value") + "*1000000"]);
dashboard.getRange("I14:I17").formulas = modernTerms.map((term) => [sourceFormula(masterInfo, term, "peak_year")]);
box(dashboard.getRange("G13:J18"), COLORS.white);
dashboard.getRange("G13:J13").format = { fill: COLORS.navy2, font: { name: "Arial", size: 9, bold: true, color: COLORS.white }, borders: { preset: "all", style: "thin", color: COLORS.grid } };
dashboard.getRange("H14:H17").format.numberFormat = "0.0000";
mergeSet(dashboard, "K13:N15", "Method warning\n\nString frequency is not equivalent to historical fear.", { fill: COLORS.orangeLight, font: { name: "Arial", size: 11, bold: true, color: "#7B341E" }, borders: { preset: "all", style: "medium", color: COLORS.orange }, horizontalAlignment: "center" });
mergeSet(dashboard, "K16:N18", "Key methodological result\n\nThe same word may perform different historical and social functions depending on speaker, source, expression mode and context.", { fill: COLORS.tealLight, font: { name: "Arial", size: 10, bold: true, color: COLORS.teal }, borders: { preset: "all", style: "medium", color: COLORS.teal }, horizontalAlignment: "center" });

mergeSet(dashboard, "A20:G20", "Figure 1 - Climate framing vocabulary", { fill: COLORS.teal, font: { name: "Arial", size: 11, bold: true, color: COLORS.white } });
mergeSet(dashboard, "H20:N20", "Figure 5 - Modern climate-specific compounds", { fill: COLORS.purple, font: { name: "Arial", size: 11, bold: true, color: COLORS.white } });
mergeSet(dashboard, "A33:G34", "Climate-specific issue labels emerge at different times in this corpus; observed presence is not historical coinage.", { fill: COLORS.tealLight, font: { name: "Arial", size: 9, italic: true, color: COLORS.teal }, borders: { preset: "all", style: "thin", color: COLORS.teal } });
mergeSet(dashboard, "H33:N34", "Modern compounds are corpus-observed late and require source-level voice and expression-mode validation.", { fill: COLORS.purpleLight, font: { name: "Arial", size: 9, italic: true, color: COLORS.purple }, borders: { preset: "all", style: "thin", color: COLORS.purple } });
mergeSet(dashboard, "A36:G36", "Figure 2 - Temperature and heat vocabulary", { fill: COLORS.teal, font: { name: "Arial", size: 11, bold: true, color: COLORS.white } });
mergeSet(dashboard, "H36:N36", "Figure 3 - Threat and risk vocabulary", { fill: COLORS.purple, font: { name: "Arial", size: 11, bold: true, color: COLORS.white } });
mergeSet(dashboard, "A55:G56", "Broad physical terms span the interval but are semantically ambiguous; their frequency does not identify climate meaning.", { fill: COLORS.tealLight, font: { name: "Arial", size: 9, italic: true, color: COLORS.teal }, borders: { preset: "all", style: "thin", color: COLORS.teal } });
mergeSet(dashboard, "H55:N56", "Threat and risk strings are not emotion measures and include extensive non-climate senses.", { fill: COLORS.purpleLight, font: { name: "Arial", size: 9, italic: true, color: COLORS.purple }, borders: { preset: "all", style: "thin", color: COLORS.purple } });
mergeSet(dashboard, "A58:G58", "Figure 4 - Affect vocabulary", { fill: COLORS.teal, font: { name: "Arial", size: 11, bold: true, color: COLORS.white } });
mergeSet(dashboard, "H58:N58", "Next research gate", { fill: COLORS.amber, font: { name: "Arial", size: 11, bold: true, color: COLORS.navy } });
mergeSet(dashboard, "A77:G78", "Generic affect strings are background controls only; they cannot establish climate-related fear without contextual passage review.", { fill: COLORS.tealLight, font: { name: "Arial", size: 9, italic: true, color: COLORS.teal }, borders: { preset: "all", style: "thin", color: COLORS.teal } });
mergeSet(dashboard, "H60:N65", "Passage-level semantic validation after complete 180-keyword lexical coverage.", { fill: COLORS.amberLight, font: { name: "Arial", size: 15, bold: true, color: "#7B5B12" }, borders: { preset: "all", style: "medium", color: COLORS.amber }, horizontalAlignment: "center" });
mergeSet(dashboard, "H67:N72", "Generated from the current project database and research exports; source tables remain version-controlled.\n\nPrimary search metric: Internet Archive Advanced Search API numFound at retrieval time. This is a discovery count, not language prevalence.", { fill: COLORS.grayLight, font: { name: "Arial", size: 10, italic: true, color: COLORS.gray }, borders: { preset: "all", style: "thin", color: COLORS.grid } });

const figurePaths = [
  ["figures/fear-temperature/figure_01_climate_framing.png", { from: { row: 20, col: 0 }, extent: { widthPx: 555, heightPx: 235 } }],
  ["figures/fear-temperature/figure_05_modern_climate_compounds.png", { from: { row: 20, col: 7 }, extent: { widthPx: 555, heightPx: 235 } }],
  ["figures/fear-temperature/figure_02_temperature_heat.png", { from: { row: 36, col: 0 }, extent: { widthPx: 555, heightPx: 360 } }],
  ["figures/fear-temperature/figure_03_threat_risk.png", { from: { row: 36, col: 7 }, extent: { widthPx: 555, heightPx: 360 } }],
  ["figures/fear-temperature/figure_04_affect.png", { from: { row: 58, col: 0 }, extent: { widthPx: 555, heightPx: 360 } }],
];
for (const [relativePath, anchor] of figurePaths) {
  const bytes = await fs.readFile(path.join(root, relativePath));
  dashboard.images.add({ dataUrl: `data:image/png;base64,${bytes.toString("base64")}`, anchor });
}
dashboard.getRange("A:N").format.columnWidth = 11;
dashboard.getRange("A1:N78").format.font.name = "Arial";
dashboard.freezePanes.freezeRows(2);

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
try { await fs.copyFile(outputPath, "/tmp/fear_temperature_quantitative_v01.pre_consolidation.xlsx"); } catch { /* first generation */ }

const inspectRanges = [
  ["Supervisor Dashboard", "A1:N18"], ["Keyword Discovery Method", "A1:N36"], ["Summary", "A1:H23"],
  ["Priority 180 Coverage", "A1:AM12"], ["Ngram Coverage", "A1:X12"], ["Dictionary 180", "A1:T12"],
  ["Search 180", "A1:R12"], ["Seed Ledger", "A1:R12"],
];
for (const [sheetName, range] of inspectRanges) {
  const inspection = await workbook.inspect({ kind: "table", range: `${sheetName}!${range}`, include: "values,formulas", tableMaxRows: 40, tableMaxCols: 42, maxChars: 12000 });
  console.log(inspection.ndjson);
}
const formulaErrors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 500 }, summary: "workbook formula error scan" });
console.log(formulaErrors.ndjson);

const renderRanges = new Map([
  ["Supervisor Dashboard", "A1:N78"], ["Keyword Discovery Method", "A1:N36"], ["Summary", "A1:H23"],
  ["Priority 180 Coverage", "A1:N20"], ["Ngram Coverage", "A1:X18"], ["Dictionary 180", "A1:T18"],
  ["Search 180", "A1:R18"], ["Seed Ledger", "A1:R18"], ["Master Frequency", "A1:O18"],
  ["Anchor Matrix", "A1:M18"], ["Family Summary", "A1:K18"], ["Voice Matrix", "A1:F20"],
  ["Query Audit", "A1:K18"], ["Ngram Status", "A1:L18"],
]);
for (const [sheetName, range] of renderRanges) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  const safeName = sheetName.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  await fs.writeFile(path.join(previewDir, `${safeName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });

const reopened = await SpreadsheetFile.importXlsx(await fs.readFile(outputPath));
const reopenInspection = await reopened.inspect({ kind: "table", range: "Summary!A4:B23", include: "values,formulas", tableMaxRows: 30, tableMaxCols: 4, maxChars: 7000 });
console.log(reopenInspection.ndjson);
const reopenErrors = await reopened.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 500 }, summary: "reopened workbook formula error scan" });
console.log(reopenErrors.ndjson);

console.log(JSON.stringify({ outputPath, previewDir, sheetCount: 14, priorityRows: priorityInfo.dataCount, dictionaryRows: dictionaryInfo.dataCount, searchRows: searchInfo.dataCount, ngramRuleRows: ngramInfo.dataCount, seedRows: seedInfo.dataCount, baselineAnnualObservations: validation.baseline_annual_observations, formulaErrors: formulaErrors.ndjson, reopenErrors: reopenErrors.ndjson }, null, 2));
