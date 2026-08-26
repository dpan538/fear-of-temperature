#!/usr/bin/env node
/** Build the formula-linked Priority 180 supervisor workbook. */

import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "/Users/jarlgiovanni/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const root = "/Users/jarlgiovanni/Desktop/fear_of_temperature";
const outputDir = path.join(root, "outputs", "priority180");
const previewDir = "/tmp/fear_temperature_priority180_previews";
const outputPath = path.join(outputDir, "fear_temperature_full_180_coverage.xlsx");

const sources = [
  ["Priority_180", "data/fear-temperature/priority180/priority180_candidate_model.csv"],
  ["Ngram_Coverage", "data/fear-temperature/exports/priority180_ngram_coverage.csv"],
  ["Ngram_Anchor_Stats", "data/fear-temperature/exports/priority180_ngram_anchor_stats.csv"],
  ["Dictionary_180", "data/fear-temperature/exports/dictionary_coverage_180.csv"],
  ["Search_180", "data/fear-temperature/exports/search_statistics_180.csv"],
  ["Voice_Mapping", "data/fear-temperature/exports/voice_keyword_matrix.csv"],
  ["Lexical_Families", "data/fear-temperature/seed/lexical_families.csv"],
];

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"' && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows;
}

function columnLetter(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    value -= 1;
    result = String.fromCharCode(65 + (value % 26)) + result;
    value = Math.floor(value / 26);
  }
  return result;
}

function headerColumn(parsed, name) {
  const index = parsed[0].indexOf(name);
  if (index < 0) throw new Error(`Missing header ${name}`);
  return columnLetter(index);
}

function styleDataSheet(sheet, parsed) {
  const rowCount = parsed.length;
  const headers = parsed[0];
  const colCount = headers.length;
  const used = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  used.format.font = { name: "Arial", size: 9, color: "#243B53" };
  used.format.rowHeight = 19;
  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format = {
    fill: "#17324D",
    font: { name: "Arial", size: 9, bold: true, color: "#FFFFFF" },
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: "#D9E2EC" },
  };
  header.format.rowHeight = 38;
  for (let column = 0; column < colCount; column += 1) {
    const name = headers[column].toLowerCase();
    const range = sheet.getRangeByIndexes(0, column, rowCount, 1);
    let width = 15;
    if (name.includes("surface") || name.includes("form") || name.includes("concept")) width = 25;
    if (name.includes("status") || name.includes("exception_type")) width = 28;
    if (name.includes("note") || name.includes("reason") || name.includes("provenance") || name.includes("source") || name.includes("sense") || name.includes("definition")) width = 42;
    if (name.includes("id") || name.includes("url") || name.includes("path")) width = 25;
    if (name.includes("frequency") || name.includes("value") || name.includes("mean") || name.includes("median") || name.includes("max")) {
      width = 18;
      if (rowCount > 1) sheet.getRangeByIndexes(1, column, rowCount - 1, 1).format.numberFormat = "0.0000000000E+00";
    }
    if (name.includes("total_results") || name.includes("result_count")) {
      width = 18;
      if (rowCount > 1) sheet.getRangeByIndexes(1, column, rowCount - 1, 1).format.numberFormat = "0";
    }
    range.format.columnWidth = width;
    if (width >= 25) range.format.wrapText = true;
  }
  if (rowCount > 1) {
    sheet.getRangeByIndexes(1, 0, rowCount - 1, colCount).format.borders = { preset: "inside", style: "thin", color: "#E8EEF3" };
  }
}

function writeMatrix(sheet, values) {
  const width = Math.max(...values.map((row) => row.length));
  const padded = values.map((row) => [...row, ...Array(width - row.length).fill("")]);
  sheet.getRangeByIndexes(0, 0, padded.length, width).values = padded;
}

const workbook = Workbook.create();
const parsedBySheet = new Map();
for (const [sheetName, relativePath] of sources) {
  const csvText = await fs.readFile(path.join(root, relativePath), "utf8");
  await workbook.fromCSV(csvText, { sheetName });
  const parsed = parseCsv(csvText);
  parsedBySheet.set(sheetName, parsed);
  styleDataSheet(workbook.worksheets.getItem(sheetName), parsed);
}

const masterText = await fs.readFile(path.join(root, "data/fear-temperature/exports/priority180_full_coverage_matrix.csv"), "utf8");
const master = parseCsv(masterText);
const masterHeader = master[0];
const idx = (name) => masterHeader.indexOf(name);

const audit = workbook.worksheets.add("Coverage_Audit");
audit.showGridLines = false;
audit.getRange("A1:D1").merge();
audit.getRange("A1:D1").values = [["Priority 180 coverage gate"]];
audit.getRange("A1:D1").format = { fill: "#102A43", font: { name: "Arial", size: 20, bold: true, color: "#FFFFFF" } };
audit.getRange("A2:D2").merge();
audit.getRange("A2:D2").values = [["Candidate-level accounting · three independent evidence channels · zero is retained as a result"]];
audit.getRange("A2:D2").format = { fill: "#D9EAF0", font: { name: "Arial", italic: true, color: "#17324D" } };
audit.getRange("A4:D4").values = [["Metric", "Formula-linked value", "Required", "Status"]];
audit.getRange("A4:D4").format = { fill: "#0B6E75", font: { bold: true, color: "#FFFFFF" } };
audit.getRange("A5:A18").values = [
  ["Priority candidates"], ["Ngram exact"], ["Ngram normalized variant"], ["Ngram validated alias"],
  ["Ngram technically unrepresentable"], ["Dictionary direct headword"], ["Dictionary technical glossary"],
  ["Dictionary no standalone headword"], ["Dictionary unresolved"], ["Search primary completed"],
  ["Search primary zero"], ["Search primary nonzero"], ["Priority accounted"], ["Unexplained rows"],
];
const ngramMappingCol = headerColumn(parsedBySheet.get("Ngram_Coverage"), "ngram_mapping_type");
const dictStatusCol = headerColumn(parsedBySheet.get("Dictionary_180"), "dictionary_status");
const searchStatusCol = headerColumn(parsedBySheet.get("Search_180"), "search_status");
audit.getRange("B5:B18").formulas = [
  ["=COUNTA(Priority_180!A2:A181)"],
  [`=COUNTIF(Ngram_Coverage!${ngramMappingCol}2:${ngramMappingCol}181,"EXACT")`],
  [`=COUNTIF(Ngram_Coverage!${ngramMappingCol}2:${ngramMappingCol}181,"NORMALIZED_VARIANT")`],
  [`=COUNTIF(Ngram_Coverage!${ngramMappingCol}2:${ngramMappingCol}181,"VALIDATED_ALIAS")`],
  [`=COUNTIF(Ngram_Coverage!${ngramMappingCol}2:${ngramMappingCol}181,"TECHNICALLY_UNREPRESENTABLE")`],
  [`=COUNTIF(Dictionary_180!${dictStatusCol}2:${dictStatusCol}181,"DIRECT_HEADWORD")`],
  [`=COUNTIF(Dictionary_180!${dictStatusCol}2:${dictStatusCol}181,"TECHNICAL_GLOSSARY")`],
  [`=COUNTIF(Dictionary_180!${dictStatusCol}2:${dictStatusCol}181,"NO_STANDALONE_HEADWORD")`],
  [`=COUNTIF(Dictionary_180!${dictStatusCol}2:${dictStatusCol}181,"UNRESOLVED")`],
  ["=B15+B16"],
  [`=COUNTIF(Search_180!${searchStatusCol}2:${searchStatusCol}181,"COMPLETED_ZERO")`],
  [`=COUNTIF(Search_180!${searchStatusCol}2:${searchStatusCol}181,"COMPLETED_NONZERO")`],
  ["=MIN(B5,SUM(B6:B9),SUM(B10:B13),B14)"],
  ["=B5-B17"],
];
audit.getRange("C5:C18").values = [[180], [""], [""], [""], [""], [""], [""], [""], [0], [180], [""], [""], [180], [0]];
audit.getRange("D5:D18").formulas = Array.from({ length: 14 }, (_, i) => [`=IF(COUNT(C${i + 5})=0,"INFO",IF(B${i + 5}=C${i + 5},"PASS","CHECK"))`]);
audit.getRange("A5:D18").format.borders = { preset: "all", style: "thin", color: "#C9D4DF" };
audit.getRange("A5:A18").format.fill = "#EEF4F7";
audit.getRange("A5:A18").format.font = { bold: true, color: "#17324D" };
audit.getRange("A20:D22").merge();
audit.getRange("A20:D22").values = [["Interpretation rule: Ngram frequency, dictionary evidence, and bounded-search result counts are separate evidence dimensions. They must never be summed or treated as a single scale."]];
audit.getRange("A20:D22").format = { fill: "#FFF3EC", wrapText: true, font: { name: "Arial", size: 11, color: "#7B341E" }, borders: { preset: "all", style: "thin", color: "#E9C2AE" } };
audit.getRange("A:D").format.columnWidth = 28;
audit.getRange("A1:D22").format.font.name = "Arial";
audit.freezePanes.freezeRows(4);

const exceptions = workbook.worksheets.add("Exceptions");
const exceptionRows = [["candidate_id", "anchor", "surface_form", "exception_type", "status", "detail"]];
for (let rowIndex = 1; rowIndex < master.length; rowIndex += 1) {
  const row = master[rowIndex];
  const candidateId = row[idx("candidate_id")];
  const anchor = row[idx("anchor")];
  const surface = row[idx("surface_form")];
  const mapping = row[idx("ngram_mapping_type")];
  const ngramStatus = row[idx("ngram_status")];
  const sense = row[idx("dictionary_anchor_sense_match")];
  if (mapping !== "EXACT") exceptionRows.push([candidateId, anchor, surface, "NGRAM_MAPPING", mapping, row[idx("ngram_notes")]]);
  if (ngramStatus.startsWith("ZERO_RESPONSE")) exceptionRows.push([candidateId, anchor, surface, "NGRAM_EMPTY_RESPONSE", ngramStatus, row[idx("coverage_exception_reason")]]);
  if (["PARTIAL", "DIFFERENT", "UNRESOLVED"].includes(sense)) exceptionRows.push([candidateId, anchor, surface, "HISTORICAL_SENSE", sense, row[idx("dictionary_historical_sense")]]);
}
exceptionRows.push(["PROVIDER", "ALL", "Google Books API", "SEARCH_PROVIDER", "QUOTA_0", "No volume-search totalItems counts claimed; Ngram is a separate service."]);
exceptionRows.push(["PROVIDER", "ALL", "OpenAlex", "SEARCH_PROVIDER", "PARTIAL_100_REQUESTS", "Anonymous daily budget exhausted; 36 candidate all-period rows completed."]);
writeMatrix(exceptions, exceptionRows);
styleDataSheet(exceptions, exceptionRows);

const summary = workbook.worksheets.add("Supervisor_Summary");
summary.showGridLines = false;
summary.getRange("A1:H1").merge();
summary.getRange("A1:H1").values = [["Fear of Temperature — Full Priority 180 Coverage"]];
summary.getRange("A1:H1").format = { fill: "#102A43", font: { name: "Arial", size: 22, bold: true, color: "#FFFFFF" } };
summary.getRange("A2:H2").merge();
summary.getRange("A2:H2").values = [["Provisional candidate-level audit · Ngram + lexicography + bounded discovery statistics"]];
summary.getRange("A2:H2").format = { fill: "#D9EAF0", font: { name: "Arial", size: 11, italic: true, color: "#17324D" } };
summary.getRange("A4:B4").values = [["Coverage gate", "Formula-linked value"]];
summary.getRange("A4:B4").format = { fill: "#0B6E75", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A5:A10").values = [["Priority candidates"], ["Priority accounted"], ["Ngram unexplained"], ["Dictionary unresolved"], ["Search primary completed"], ["Search unexplained"]];
summary.getRange("B5:B10").formulas = [["=Coverage_Audit!B5"], ["=Coverage_Audit!B17"], ["=Coverage_Audit!B5-SUM(Coverage_Audit!B6:B9)"], ["=Coverage_Audit!B13"], ["=Coverage_Audit!B14"], ["=Coverage_Audit!B5-Coverage_Audit!B14"]];
summary.getRange("A5:B10").format.borders = { preset: "all", style: "thin", color: "#C9D4DF" };
summary.getRange("A5:A10").format.fill = "#EEF4F7";
summary.getRange("A5:A10").format.font = { bold: true, color: "#17324D" };

summary.getRange("D4:H4").merge();
summary.getRange("D4:H4").values = [["What is complete"]];
summary.getRange("D4:H4").format = { fill: "#6B5CA5", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("D5:H10").merge();
summary.getRange("D5:H10").values = [["180/180 candidate records have an explicit Ngram strategy, lexicographic treatment, and completed Internet Archive primary search. Repeated forms retain candidate-level anchor statistics. Empty responses, zero search results, no-headword phrases, and historical-sense differences remain visible."]];
summary.getRange("D5:H10").format = { fill: "#F3F0F8", wrapText: true, font: { name: "Arial", size: 11, color: "#243B53" }, borders: { preset: "all", style: "thin", color: "#D8D0E7" } };

summary.getRange("A12:H12").merge();
summary.getRange("A12:H12").values = [["Three evidence channels answer different questions"]];
summary.getRange("A12:H12").format = { fill: "#C65D3B", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A13:H17").values = [
  ["Ngram", "Annual normalized string frequency in the Google Books corpus", "Never semantic prevalence", "", "", "", "", ""],
  ["Dictionary", "Lexical meaning, polysemy, and historical-sense compatibility", "No standalone headword is still accounted", "", "", "", "", ""],
  ["Internet Archive", "Exact-phrase metadata text-item discovery count at retrieval time", "Not a full-text frequency", "", "", "", "", ""],
  ["OpenAlex", "Partial secondary scholarly-work discoverability count", "Daily budget exhausted after 100 requests", "", "", "", "", ""],
  ["Google Books API", "Provider quota probe", "Quota 0; no totalItems counts claimed", "", "", "", "", ""],
];
summary.getRange("A13:H17").format = { fill: "#FFF3EC", wrapText: true, font: { name: "Arial", size: 10, color: "#7B341E" }, borders: { preset: "all", style: "thin", color: "#E9C2AE" } };
summary.getRange("A13:A17").format.font = { bold: true, color: "#7B341E" };

summary.getRange("A19:H19").merge();
summary.getRange("A19:H19").values = [["Historically meaningful distinctions"]];
summary.getRange("A19:H19").format = { fill: "#0B6E75", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A20:H24").values = [
  ["1842 climate", "Historical meteorological condition; only partial match to modern issue meaning", "", "", "", "", "", ""],
  ["1842 depressing effect", "Bodily/energetic lowering; different from clinical depression", "", "", "", "", "", ""],
  ["2015 common concern", "Legal-institutional formula; not personal emotion", "", "", "", "", "", ""],
  ["2022 climate anxiety", "Research construct unless participant self-use is separately evidenced", "", "", "", "", "", ""],
  ["Threat / risk", "Institutional danger and probability are not automatically fear", "", "", "", "", "", ""],
];
summary.getRange("A20:H24").format = { fill: "#EDF8F7", wrapText: true, font: { name: "Arial", size: 10, color: "#17324D" }, borders: { preset: "all", style: "thin", color: "#B7D8D6" } };
summary.getRange("A20:A24").format.font = { bold: true, color: "#0B6E75" };

summary.getRange("A26:B26").values = [["Next step", "200-passage semantic retrieval pilot"]];
summary.getRange("A26:B26").format = { fill: "#D49B28", font: { bold: true, color: "#102A43" } };
summary.getRange("D26:H29").merge();
summary.getRange("D26:H29").values = [["Provisional provenance: all Priority records remain labelled RECONSTRUCTED_FROM_REPORT. This audit is complete for the provisional population, but it is not a final immutable production freeze."]];
summary.getRange("D26:H29").format = { fill: "#FFF8E7", wrapText: true, font: { name: "Arial", italic: true, color: "#7B5B12" }, borders: { preset: "all", style: "thin", color: "#D49B28" } };
summary.getRange("A1:H30").format.font.name = "Arial";
summary.getRange("A1:H30").format.verticalAlignment = "center";
summary.getRange("A1:H30").format.wrapText = true;
summary.getRange("A:A").format.columnWidth = 25;
summary.getRange("B:B").format.columnWidth = 28;
summary.getRange("C:C").format.columnWidth = 28;
summary.getRange("D:H").format.columnWidth = 18;
summary.freezePanes.freezeRows(2);

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const keyInspection = await workbook.inspect({
  kind: "table",
  range: "Supervisor_Summary!A1:H29",
  include: "values,formulas",
  tableMaxRows: 35,
  tableMaxCols: 10,
  maxChars: 12000,
});
console.log(keyInspection.ndjson);

for (const sheetName of ["Coverage_Audit", "Supervisor_Summary"]) {
  const formulaErrors = await workbook.inspect({
    kind: "match",
    sheetId: sheetName,
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: `formula error scan: ${sheetName}`,
  });
  console.log(formulaErrors.ndjson);
}

const renderRanges = new Map([
  ["Priority_180", "A1:AB20"], ["Ngram_Coverage", "A1:AF20"], ["Ngram_Anchor_Stats", "A1:AE20"],
  ["Dictionary_180", "A1:U20"], ["Search_180", "A1:V20"], ["Voice_Mapping", "A1:F25"],
  ["Lexical_Families", "A1:E15"], ["Coverage_Audit", "A1:D22"], ["Exceptions", "A1:F28"],
  ["Supervisor_Summary", "A1:H29"],
]);
for (const [sheetName, range] of renderRanges) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  const safeName = sheetName.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  await fs.writeFile(path.join(previewDir, `${safeName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });
console.log(JSON.stringify({ outputPath, previewDir, sheetCount: 10 }));
