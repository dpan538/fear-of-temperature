#!/usr/bin/env node
/** Build the formula-linked supervisor workbook from canonical CSV exports. */

import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "/Users/jarlgiovanni/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const root = "/Users/jarlgiovanni/Desktop/fear_of_temperature";
const outputDir = path.join(root, "outputs", "quantitative-v01");
const previewDir = "/tmp/fear_temperature_workbook_previews";
const outputPath = path.join(outputDir, "fear_temperature_quantitative_v01.xlsx");

const sources = [
  ["Master Frequency", "data/fear-temperature/exports/keyword_frequency_summary.csv"],
  ["Anchor Matrix", "data/fear-temperature/exports/anchor_keyword_frequency_matrix.csv"],
  ["Family Summary", "data/fear-temperature/exports/lexical_family_frequency_summary.csv"],
  ["Query Audit", "data/fear-temperature/exports/ngram_compatibility_audit.csv"],
  ["Ngram Status", "data/fear-temperature/ngram/ngram_query_execution_results.csv"],
  ["Voice Matrix", "data/fear-temperature/exports/voice_keyword_matrix.csv"],
  ["Seed Ledger", "data/fear-temperature/seed/seed_candidates.csv"],
];

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        field += '"';
        i += 1;
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
  header.format.rowHeight = 34;
  for (let col = 0; col < colCount; col += 1) {
    const name = headers[col].toLowerCase();
    const range = sheet.getRangeByIndexes(0, col, rowCount, 1);
    let width = 15;
    if (name.includes("surface") || name === "term" || name.includes("concept")) width = 24;
    if (name.includes("note") || name.includes("reason") || name.includes("report") || name.includes("members") || name.includes("warning") || name.includes("pattern") || name.includes("metadata")) width = 42;
    if (name.includes("id") || name.includes("sha") || name.includes("path")) width = 24;
    if (name.includes("frequency") || name.includes("value") || name.includes("mean") || name.includes("median") || name.includes("maximum")) {
      width = 18;
      if (rowCount > 1) sheet.getRangeByIndexes(1, col, rowCount - 1, 1).format.numberFormat = "0.0000000000E+00";
    }
    if (name.endsWith("_at") || name.includes("timestamp")) {
      width = 20;
      if (rowCount > 1) sheet.getRangeByIndexes(1, col, rowCount - 1, 1).format.numberFormat = "yyyy-mm-dd hh:mm:ss";
    }
    range.format.columnWidth = width;
    if (width >= 24) range.format.wrapText = true;
  }
  if (rowCount > 1) {
    const body = sheet.getRangeByIndexes(1, 0, rowCount - 1, colCount);
    body.format.borders = { preset: "inside", style: "thin", color: "#E8EEF3" };
  }
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

const summary = workbook.worksheets.add("Summary");
summary.showGridLines = false;
summary.getRange("A1:H1").merge();
summary.getRange("A1:H1").values = [["Fear of Temperature — Quantitative Baseline v0.1"]];
summary.getRange("A1:H1").format = {
  fill: "#102A43",
  font: { name: "Arial", size: 22, bold: true, color: "#FFFFFF" },
  verticalAlignment: "center",
};
summary.getRange("A1:H1").format.rowHeight = 42;
summary.getRange("A2:H2").merge();
summary.getRange("A2:H2").values = [["Provisional, provenance-labelled research baseline · Google Books Ngram current English corpus · 1842–2022"]];
summary.getRange("A2:H2").format = {
  fill: "#D9EAF0",
  font: { name: "Arial", size: 11, italic: true, color: "#17324D" },
};

summary.getRange("A4:B4").values = [["Research status", "Value"]];
summary.getRange("A4:B4").format = { fill: "#0B6E75", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A5:A17").values = [
  ["Research version"], ["Query rules"], ["Ngram-executable"], ["Successful non-zero series"],
  ["Zero-result series"], ["Failed requests"], ["Not run — incompatible"], ["Annual observations"],
  ["Year start"], ["Year end"], ["Seed ledger records"], ["Lexical families"], ["Voice × anchor cells"],
];
summary.getRange("B5").values = [["fear-temperature-quant-v0.1-provisional"]];
summary.getRange("B6:B17").formulas = [
  ["=COUNTA('Query Audit'!A2:A144)"],
  ["=COUNTIF('Query Audit'!F2:F144,\"True\")"],
  ["=COUNTIF('Ngram Status'!C2:C144,\"SUCCEEDED\")"],
  ["=COUNTIF('Ngram Status'!C2:C144,\"ZERO_RESULT\")"],
  ["=COUNTIF('Ngram Status'!C2:C144,\"FAILED\")"],
  ["=COUNTIF('Ngram Status'!C2:C144,\"NOT_RUN_INCOMPATIBLE\")"],
  ["=SUM('Ngram Status'!E2:E144)"],
  ["=MIN('Master Frequency'!J2:J144)"],
  ["=MAX('Master Frequency'!K2:K144)"],
  ["=COUNTA('Seed Ledger'!A2:A397)"],
  ["=COUNTA('Family Summary'!A2:A15)"],
  ["=COUNTA('Voice Matrix'!A2:A31)"],
];
summary.getRange("A5:B17").format.borders = { preset: "all", style: "thin", color: "#C9D4DF" };
summary.getRange("A5:A17").format.fill = "#EEF4F7";
summary.getRange("A5:A17").format.font = { bold: true, color: "#17324D" };

summary.getRange("D4:H4").merge();
summary.getRange("D4:H4").values = [["Three supported quantitative observations"]];
summary.getRange("D4:H4").format = { fill: "#6B5CA5", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("D5:H6").merge();
summary.getRange("D5:H6").values = [["1. ‘climate change’ rises from 1.24 occurrences per million in 1988 to 28.90 per million in 2022; this is lexical frequency, not evidence of public fear."]];
summary.getRange("D7:H8").merge();
summary.getRange("D7:H8").values = [["2. ‘global warming’ peaks in 2009 (5.45 per million), while ‘climate change’ reaches its interval maximum in 2022."]];
summary.getRange("D9:H10").merge();
summary.getRange("D9:H10").values = [["3. Modern compounds peak in 2022: climate crisis 0.939, climate emergency 0.263, eco-anxiety 0.0550, and climate anxiety 0.0358 occurrences per million."]];
summary.getRange("D5:H10").format = { fill: "#F3F0F8", wrapText: true, font: { size: 11, color: "#243B53" }, borders: { preset: "all", style: "thin", color: "#D8D0E7" } };

summary.getRange("A19:H19").merge();
summary.getRange("A19:H19").values = [["Methodological safeguards"]];
summary.getRange("A19:H19").format = { fill: "#C65D3B", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A20:H22").merge();
summary.getRange("A20:H22").values = [["Generic string frequency ≠ climate-specific meaning. Threat/risk ≠ emotion. Survey wording, media imperatives, researcher constructs, and participant-generated affect remain distinct. Corpus-observed first presence is not historical coinage. Family members are never summed into a composite index."]];
summary.getRange("A20:H22").format = { fill: "#FFF3EC", wrapText: true, font: { size: 11, color: "#7B341E" }, borders: { preset: "all", style: "thin", color: "#E9C2AE" } };

const anchorRows = parsedBySheet.get("Anchor Matrix");
const firstRowByTerm = new Map();
for (let index = 1; index < anchorRows.length; index += 1) {
  const term = anchorRows[index][1].toLowerCase();
  if (!firstRowByTerm.has(term)) firstRowByTerm.set(term, index + 1);
}
summary.getRange("A24:B24").values = [["Modern compound", "2022 per million"]];
summary.getRange("A25:A28").values = [["climate crisis"], ["climate emergency"], ["climate anxiety"], ["eco-anxiety"]];
summary.getRange("B25:B28").formulas = ["climate crisis", "climate emergency", "climate anxiety", "eco-anxiety"].map((term) => [
  `='Anchor Matrix'!L${firstRowByTerm.get(term)}*1000000`,
]);
summary.getRange("A24:B28").format.borders = { preset: "all", style: "thin", color: "#C9D4DF" };
summary.getRange("A24:B24").format = { fill: "#0B6E75", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("B25:B28").format.numberFormat = "0.000";
const chart = summary.charts.add("bar", summary.getRange("A24:B28"));
chart.title = "Modern climate-specific compounds in 2022";
chart.hasLegend = false;
chart.xAxis = { axisType: "textAxis" };
chart.yAxis = { numberFormatCode: "0.000" };
chart.setPosition("D24", "H37");

summary.getRange("A30:B30").values = [["Next step", "200-passage semantic retrieval pilot"]];
summary.getRange("A30:B30").format = { fill: "#D49B28", font: { bold: true, color: "#102A43" } };
summary.getRange("A32:B35").merge();
summary.getRange("A32:B35").values = [["Provisional: later-stage structured artifacts were unavailable. Reconstructed records use new project IDs; this is not a final research freeze."]];
summary.getRange("A32:B35").format = { fill: "#FFF8E7", wrapText: true, font: { italic: true, color: "#7B5B12" }, borders: { preset: "outside", style: "thin", color: "#D49B28" } };
summary.getRange("A32:B35").format.rowHeight = 28;
summary.getRange("A1:H37").format.font.name = "Arial";
summary.getRange("A1:H37").format.verticalAlignment = "center";
summary.getRange("A1:H37").format.wrapText = true;
summary.getRange("A:A").format.columnWidth = 26;
summary.getRange("B:B").format.columnWidth = 24;
summary.getRange("C:C").format.columnWidth = 3;
summary.getRange("D:H").format.columnWidth = 18;
summary.freezePanes.freezeRows(2);

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const keyInspection = await workbook.inspect({
  kind: "table",
  range: "Summary!A1:H34",
  include: "values,formulas",
  tableMaxRows: 40,
  tableMaxCols: 10,
  maxChars: 9000,
});
console.log(keyInspection.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  sheetId: "Summary",
  range: "A1:H37",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(formulaErrors.ndjson);

const renderRanges = new Map([
  ["Summary", "A1:H37"], ["Master Frequency", "A1:AC18"], ["Anchor Matrix", "A1:M18"],
  ["Family Summary", "A1:K15"], ["Query Audit", "A1:K18"], ["Ngram Status", "A1:L18"],
  ["Voice Matrix", "A1:F20"], ["Seed Ledger", "A1:R18"],
]);
for (const [sheetName, range] of renderRanges) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  const safeName = sheetName.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  await fs.writeFile(path.join(previewDir, `${safeName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });
console.log(JSON.stringify({ outputPath, previewDir, sheetCount: 8, formulaErrorScan: formulaErrors.ndjson }));
