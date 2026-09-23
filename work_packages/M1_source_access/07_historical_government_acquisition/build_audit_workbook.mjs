import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = "/Users/jarlgiovanni/Desktop/fear_of_temperature";
const reportDir = path.join(projectRoot, "work_packages/M1_source_access/07_historical_government_acquisition/reports");
const outputDir = path.join(projectRoot, "outputs/01a0c28b-466f-7a23-b28c-0d66628f6a28");
const outputPath = path.join(outputDir, "historical_government_acquisition_audit.xlsx");
const previewDir = "/private/tmp/historical_government_acquisition_workbook_previews";
const fontName = "Arial";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        value += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        value += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(value);
      value = "";
    } else if (char === "\n") {
      row.push(value.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      value = "";
    } else {
      value += char;
    }
  }
  if (value.length > 0 || row.length > 0) {
    row.push(value.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows;
}

function columnName(index) {
  let current = index + 1;
  let name = "";
  while (current > 0) {
    const remainder = (current - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    current = Math.floor((current - 1) / 26);
  }
  return name;
}

function typedMatrix(matrix) {
  if (matrix.length === 0) return matrix;
  const headers = matrix[0];
  const integerHeaders = new Set([
    "year", "enumerated_targets", "already_in_06", "net_new_expected", "content_objects_expected",
    "attempted_objects", "downloaded_objects", "extracted_objects", "failed_or_deferred_objects",
    "ingested_records", "frozen_target_records", "original_text_acquired_records", "parsed_records",
    "formally_committed_records", "failed_target_records", "failed_or_retry_objects", "not_yet_processed_records",
    "unprocessed_content_objects",
    "enumerated_records", "already_in_06_records", "net_new_record_targets", "attempted_content_objects",
    "downloaded_content_objects", "extracted_content_objects", "confirmed_target_exceptions",
    "policy_document", "ministerial_written_answer", "ministerial_written_statement", "all_three_series",
    "before", "after", "change",
  ]);
  return matrix.map((row, rowIndex) => row.map((cell, colIndex) => {
    if (rowIndex === 0) return cell;
    const header = headers[colIndex] || "";
    if (integerHeaders.has(header) && /^-?\d+$/.test(cell)) return Number(cell);
    return cell;
  }));
}

async function readCsv(name) {
  const text = await fs.readFile(path.join(reportDir, name), "utf8");
  return typedMatrix(parseCsv(text));
}

function selectColumns(matrix, wantedHeaders) {
  const indexes = wantedHeaders.map((header) => matrix[0].indexOf(header));
  if (indexes.some((index) => index < 0)) throw new Error(`Missing requested column in workbook source: ${wantedHeaders.join(", ")}`);
  return matrix.map((row) => indexes.map((index) => row[index]));
}

function styleSheet(sheet, matrix, { title = null, startRow = 1, tableName }) {
  sheet.showGridLines = false;
  const rows = matrix.length;
  const cols = matrix[0]?.length || 1;
  const start = startRow;
  const endRow = start + rows - 1;
  const endCol = columnName(cols - 1);
  if (title) {
    sheet.getRange("A2").values = [[title]];
    sheet.getRange("A2").format.font = { name: fontName, size: 14, bold: true, color: "#20303A" };
    sheet.getRange(`A3:${endCol}3`).format.borders = { bottom: { style: "thin", color: "#87959B" } };
  }
  const tableRange = sheet.getRange(`A${start}:${endCol}${endRow}`);
  tableRange.values = matrix;
  tableRange.format.font = { name: fontName, size: 10, color: "#20303A" };
  tableRange.format.verticalAlignment = "center";
  const header = sheet.getRange(`A${start}:${endCol}${start}`);
  header.format = {
    fill: "#24495F",
    font: { name: fontName, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { insideVertical: { style: "thin", color: "#FFFFFF" }, bottom: { style: "medium", color: "#24495F" } },
  };
  header.format.rowHeight = 32;
  if (rows > 1) {
    sheet.tables.add(`A${start}:${endCol}${endRow}`, true, tableName).style = "TableStyleMedium2";
    sheet.getRange(`A${start + 1}:${endCol}${endRow}`).format.rowHeight = 19;
  }
  sheet.getRange(`A${start}:${endCol}${endRow}`).format.autofitColumns();
  for (let col = 0; col < cols; col += 1) {
    const width = Math.min(42, Math.max(10, sheet.getRangeByIndexes(start - 1, col, Math.max(1, rows), 1).format.columnWidth || 10));
    sheet.getRangeByIndexes(start - 1, col, Math.max(1, rows), 1).format.columnWidth = width;
  }
  sheet.freezePanes.freezeRows(start);
  sheet.tabColor = title ? "#24495F" : "#6F7D4C";
  return { endRow, endCol };
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const [progress, annual, quarterly, sourceYear, exceptions, departments, beforeAfter] = await Promise.all([
  readCsv("source_progress.csv"),
  readCsv("annual_distribution.csv"),
  readCsv("quarterly_distribution.csv"),
  readCsv("source_year_progress.csv"),
  readCsv("exceptions_and_gaps.csv"),
  readCsv("department_genre_register.csv"),
  readCsv("pre2010_before_after.csv"),
]);
const progressSummary = selectColumns(progress, [
  "source_tranche", "series", "enumerated_targets", "already_in_06", "net_new_expected",
  "original_text_acquired_records", "parsed_records", "formally_committed_records",
  "failed_target_records", "failed_or_retry_objects", "not_yet_processed_records",
  "unprocessed_content_objects",
]);

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
const annualSheet = workbook.worksheets.add("Annual");
const quarterSheet = workbook.worksheets.add("Quarterly");
const sourceYearSheet = workbook.worksheets.add("Source by year");
const exceptionSheet = workbook.worksheets.add("Exceptions");
const departmentSheet = workbook.worksheets.add("Departments");

summary.showGridLines = false;
summary.getRange("A2").values = [["Historical government acquisition audit"]];
summary.getRange("A2").format.font = { name: fontName, size: 14, bold: true, color: "#20303A" };
summary.getRange("A3").values = [["Cutoff: 2026-09-21. Policy documents, ministerial written answers and written statements remain separate series."]];
summary.getRange("A3").format.font = { name: fontName, size: 10, italic: true, color: "#5D6A70" };
summary.getRange("A4:J4").format.borders = { bottom: { style: "thin", color: "#87959B" } };
summary.getRange("A6").values = [["Pre-2010 change"]];
summary.getRange("A6").format.font = { name: fontName, size: 11, bold: true, color: "#24495F" };
summary.getRange(`A7:${columnName(beforeAfter[0].length - 1)}${6 + beforeAfter.length}`).values = beforeAfter;
summary.getRange(`A7:${columnName(beforeAfter[0].length - 1)}7`).format = { fill: "#6F7D4C", font: { name: fontName, size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
summary.getRange("A13").values = [["Source progress"]];
summary.getRange("A13").format.font = { name: fontName, size: 11, bold: true, color: "#24495F" };
const progressStart = 14;
const progressEnd = progressStart + progressSummary.length - 1;
const progressEndCol = columnName(progressSummary[0].length - 1);
summary.getRange(`A${progressStart}:${progressEndCol}${progressEnd}`).values = progressSummary;
summary.getRange(`A${progressStart}:${progressEndCol}${progressStart}`).format = { fill: "#24495F", font: { name: fontName, size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
summary.tables.add(`A${progressStart}:${progressEndCol}${progressEnd}`, true, "SourceProgressTable").style = "TableStyleMedium2";
summary.getRange(`A${progressStart + 1}:${progressEndCol}${progressEnd}`).format.font = { name: fontName, size: 10, color: "#20303A" };
summary.getRange(`A${progressStart}:${progressEndCol}${progressEnd}`).format.autofitColumns();
summary.getRange(`A${progressStart}:${progressEndCol}${progressEnd}`).format.verticalAlignment = "center";
summary.getRange(`A${progressStart}:${progressEndCol}${progressStart}`).format.rowHeight = 34;
summary.getRange("K6").values = [["Coverage boundary"]];
summary.getRange("K6").format.font = { name: fontName, size: 11, bold: true, color: "#C57A43" };
summary.getRange("K7").values = [["Counts describe the frozen official source partitions, not all UK government discourse or a climate-only sample. Zero observations are not proof of no activity. Current downloaded versions may post-date first publication."]];
summary.getRange("K7").format = { font: { name: fontName, size: 10, color: "#5D6A70" }, wrapText: true, verticalAlignment: "top" };
summary.getRange("K7").format.columnWidth = 38;
summary.getRange("K7").format.rowHeight = 95;
summary.freezePanes.freezeRows(progressStart);
summary.tabColor = "#24495F";

styleSheet(annualSheet, annual, { title: "Annual distribution by independent series", startRow: 5, tableName: "AnnualDistributionTable" });
styleSheet(quarterSheet, quarterly, { title: "Quarterly distribution by independent series", startRow: 5, tableName: "QuarterlyDistributionTable" });
styleSheet(sourceYearSheet, sourceYear, { title: "Source and year reconciliation", startRow: 5, tableName: "SourceYearProgressTable" });
styleSheet(exceptionSheet, exceptions, { title: "Remaining exceptions and gaps", startRow: 5, tableName: "ExceptionsTable" });
styleSheet(departmentSheet, departments, { title: "Department and genre scope register", startRow: 5, tableName: "DepartmentsTable" });

workbook.recalculate();
const summaryCheck = await workbook.inspect({ kind: "table", range: "Summary!A1:N24", include: "values,formulas", tableMaxRows: 24, tableMaxCols: 14, maxChars: 10000 });
console.log(summaryCheck.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errors.ndjson);

for (const sheetName of ["Summary", "Annual", "Quarterly", "Source by year", "Exceptions", "Departments"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, previewDir }, null, 2));
