#!/usr/bin/env node
/** Add presentation-ready relational-analysis sheets to the canonical workbook. */

import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = "/Users/jarlgiovanni/Desktop/fear_of_temperature";
const outputPath = path.join(root, "outputs/quantitative-v01/fear_temperature_quantitative_v01.xlsx");
const previewDir = "/tmp/fear_temperature_relational_workbook_previews";
const existingPreview = "/tmp/fear_temperature_relational_existing_dashboard.png";
const backupPath = "/tmp/fear_temperature_quantitative_v01.pre_relational.xlsx";
const relationalDir = path.join(root, "data/fear-temperature/analysis/relational-v01");
const figureDir = path.join(root, "figures/fear-temperature/relational-v01");
const validationPath = path.join(relationalDir, "relational_workbook_validation.json");

const COLORS = {
  navy: "#102A43", navy2: "#17324D", teal: "#2F6B8A", tealLight: "#E3F0F5",
  purple: "#6655A4", purpleLight: "#E8E3F4", orange: "#D05A32", orangeLight: "#F6DED5",
  amber: "#D79A2B", amberLight: "#FFF4D6", green: "#3C7F78", greenLight: "#E6F2F0",
  red: "#B42318", redLight: "#FDECEC", gray: "#667085", grayLight: "#F2F4F7",
  missing: "#E5E9EE", ink: "#243B53", grid: "#D9E2EC", white: "#FFFFFF",
};

const newSheetNames = [
  "Relational Analysis", "Threat Linkage", "Affect Linkage", "Voice Comparison",
  "Lexicalisation", "Figure Gallery", "Supervisor Summary",
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

function isNumericHeader(header) {
  const value = String(header).toLowerCase();
  return value.includes("count") || value.includes("rate") || value.includes("ratio") ||
    value.includes("year") || value.includes("frequency") || value.includes("denominator") ||
    value.includes("balance") || value === "total";
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

async function loadCsv(name) {
  return typedMatrix(parseCsv(await fs.readFile(path.join(relationalDir, name), "utf8")));
}

function columnLetter(index) {
  let value = index + 1;
  let output = "";
  while (value > 0) {
    value -= 1;
    output = String.fromCharCode(65 + (value % 26)) + output;
    value = Math.floor(value / 26);
  }
  return output;
}

function mergeSet(sheet, address, value, format = {}) {
  const range = sheet.getRange(address);
  range.merge();
  range.values = [[value]];
  range.format = { wrapText: true, verticalAlignment: "center", ...format };
  return range;
}

function titleBand(sheet, title, note, lastColumn = "N") {
  sheet.showGridLines = false;
  mergeSet(sheet, `A1:${lastColumn}1`, title, {
    fill: COLORS.navy,
    font: { name: "Arial", size: 19, bold: true, color: COLORS.white },
  }).format.rowHeight = 40;
  mergeSet(sheet, `A2:${lastColumn}2`, note, {
    fill: "#D9EAF0",
    font: { name: "Arial", size: 10, italic: true, color: COLORS.navy2 },
  }).format.rowHeight = 34;
}

function preferredWidth(header) {
  const value = String(header).toLowerCase();
  if (/note|warning|status|scope|forms|denominator/.test(value)) return 35;
  if (/term|family|voice|anchor|mode/.test(value)) return 22;
  if (/count|rate|ratio|year|frequency|balance/.test(value)) return 17;
  return 18;
}

function styleHeader(range, fill = COLORS.navy2) {
  range.format = {
    fill,
    font: { name: "Arial", size: 9, bold: true, color: COLORS.white },
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: COLORS.grid },
  };
  range.format.rowHeight = 42;
}

function addMatrix(sheet, matrix, startRow, tableName, headerFill = COLORS.navy2) {
  const colCount = matrix[0].length;
  const dataCount = matrix.length - 1;
  const last = columnLetter(colCount - 1);
  const endRow = startRow + matrix.length - 1;
  sheet.getRangeByIndexes(startRow - 1, 0, matrix.length, colCount).values = matrix;
  styleHeader(sheet.getRange(`A${startRow}:${last}${startRow}`), headerFill);
  if (dataCount > 0) {
    const table = sheet.tables.add(`A${startRow}:${last}${endRow}`, true, tableName);
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;
    const body = sheet.getRangeByIndexes(startRow, 0, dataCount, colCount);
    body.format = {
      font: { name: "Arial", size: 9, color: COLORS.ink },
      verticalAlignment: "top",
      wrapText: true,
      borders: { preset: "inside", style: "thin", color: "#E8EEF3" },
    };
    body.format.rowHeight = 28;
  }
  matrix[0].forEach((header, index) => {
    sheet.getRangeByIndexes(startRow - 1, index, matrix.length, 1).format.columnWidth = preferredWidth(header);
    if (/rate|ratio/i.test(header) && dataCount) {
      sheet.getRangeByIndexes(startRow, index, dataCount, 1).format.numberFormat = "0.0%";
    } else if (/count|year|balance/i.test(header) && dataCount) {
      sheet.getRangeByIndexes(startRow, index, dataCount, 1).format.numberFormat = "#,##0";
    } else if (/frequency/i.test(header) && dataCount) {
      sheet.getRangeByIndexes(startRow, index, dataCount, 1).format.numberFormat = "0.0000";
    }
  });
  return { endRow, dataCount, colCount };
}

function applyUnsupportedFormatting(range) {
  range.conditionalFormats.add("containsText", {
    text: "UNSUPPORTED",
    format: { fill: COLORS.missing, font: { color: COLORS.gray, bold: true } },
  });
  range.conditionalFormats.add("containsText", {
    text: "UNRESOLVED",
    format: { fill: COLORS.amberLight, font: { color: "#7B5B12", bold: true } },
  });
}

function labelBand(sheet, row, label, lastColumn, fill) {
  mergeSet(sheet, `A${row}:${lastColumn}${row}`, label, {
    fill,
    font: { name: "Arial", size: 11, bold: true, color: COLORS.white },
  }).format.rowHeight = 25;
}

async function imageData(stem) {
  const bytes = await fs.readFile(path.join(figureDir, `${stem}.png`));
  return `data:image/png;base64,${bytes.toString("base64")}`;
}

async function inspectExisting() {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
  const overview = await workbook.inspect({
    kind: "workbook,sheet,table",
    maxChars: 9000,
    tableMaxRows: 5,
    tableMaxCols: 8,
  });
  console.log(overview.ndjson);
  const styles = await workbook.inspect({
    kind: "computedStyle",
    sheetId: "Supervisor Dashboard",
    range: "A1:N12",
    maxChars: 5000,
  });
  console.log(styles.ndjson);
  const preview = await workbook.render({
    sheetName: "Supervisor Dashboard",
    range: "A1:N78",
    scale: 0.7,
    format: "png",
  });
  await fs.writeFile(existingPreview, new Uint8Array(await preview.arrayBuffer()));
  console.log(JSON.stringify({ status: "READ_ONLY_INSPECTION_COMPLETE", existingPreview }, null, 2));
}

async function buildWorkbook() {
  try { await fs.access(backupPath); }
  catch { await fs.copyFile(outputPath, backupPath); }
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(backupPath));

  const matrices = {
    threatAnchor: await loadCsv("threat_linkage_by_anchor.csv"),
    threatVoice: await loadCsv("threat_linkage_by_anchor_voice.csv"),
    threatRegistry: await loadCsv("threat_linkage_passages.csv"),
    affectAnchor: await loadCsv("affect_linkage_by_anchor.csv"),
    affectVoice: await loadCsv("affect_linkage_by_anchor_voice.csv"),
    affectMode: await loadCsv("affect_linkage_by_anchor_affect_mode.csv"),
    affectRegistry: await loadCsv("affect_linkage_passages.csv"),
    voice: await loadCsv("voice_linkage_summary.csv"),
    lexical: await loadCsv("lexicalisation_comparison.csv"),
    inventory: await loadCsv("inventory_voice_layer_balance.csv"),
    gaps: await loadCsv("linkage_data_gap_registry.csv"),
  };

  const sheets = {};
  for (const name of newSheetNames) sheets[name] = workbook.worksheets.add(name);

  const relational = sheets["Relational Analysis"];
  titleBand(relational, "Relational Analysis", "Validated historical relations from A/B temperature-climate objects to D threat and C explicit affect.", "N");
  mergeSet(relational, "A4:F10", "A / B OBJECT\n\ntemperature · heat · warming · climate · greenhouse · thresholds", {
    fill: COLORS.tealLight,
    font: { name: "Arial", size: 15, bold: true, color: COLORS.teal },
    horizontalAlignment: "center",
    borders: { preset: "all", style: "medium", color: COLORS.teal },
  });
  mergeSet(relational, "H4:N6", "D — THREAT / RISK / HARM\n\nDanger, threat, risk, crisis, emergency, loss and damage", {
    fill: COLORS.orangeLight,
    font: { name: "Arial", size: 12, bold: true, color: COLORS.orange },
    horizontalAlignment: "center",
    borders: { preset: "all", style: "medium", color: COLORS.orange },
  });
  mergeSet(relational, "H8:N10", "C — EXPLICIT AFFECT\n\nDirect · prescribed · elicited · researcher-labelled", {
    fill: COLORS.purpleLight,
    font: { name: "Arial", size: 12, bold: true, color: COLORS.purple },
    horizontalAlignment: "center",
    borders: { preset: "all", style: "medium", color: COLORS.purple },
  });
  mergeSet(relational, "A12:N15", "THREAT ≠ AFFECT\n\nD is not the same as C. Co-occurrence is not a validated relation, and generic corpus frequency is not passage-level historical meaning.", {
    fill: COLORS.navy,
    font: { name: "Arial", size: 16, bold: true, color: COLORS.white },
    horizontalAlignment: "center",
  });
  labelBand(relational, 17, "Current denominator state", "N", COLORS.gray);
  addMatrix(relational, matrices.gaps, 18, "RelationalDataGapTable", COLORS.gray);
  relational.getRange("A19:G19").format.rowHeight = 62;
  mergeSet(relational, "A23:N26", "Current finding: the repository contains no populated passage → occurrence → annotation → review → linkage records. Link counts are therefore dataset zeros; rates remain blank and unsupported rather than being reported as 0%.", {
    fill: COLORS.amberLight,
    font: { name: "Arial", size: 12, bold: true, color: "#7B5B12" },
    horizontalAlignment: "center",
    borders: { preset: "all", style: "medium", color: COLORS.amber },
  });
  relational.getRange("A:N").format.columnWidth = 12;
  relational.freezePanes.freezeRows(2);

  const threat = sheets["Threat Linkage"];
  titleBand(threat, "Threat Linkage", "A/B object passages linked to validated D-layer threat, risk or harm expressions.", "N");
  labelBand(threat, 4, "By anchor", "N", COLORS.orange);
  addMatrix(threat, matrices.threatAnchor, 5, "ThreatByAnchorTable", COLORS.orange);
  labelBand(threat, 13, "By anchor × voice", "N", COLORS.orange);
  const threatVoiceInfo = addMatrix(threat, matrices.threatVoice, 14, "ThreatByVoiceTable", COLORS.orange);
  threat.getRange("A6:H11").format.rowHeight = 42;
  threat.getRange(`A15:I${threatVoiceInfo.endRow}`).format.rowHeight = 34;
  labelBand(threat, threatVoiceInfo.endRow + 2, "Passage registry — currently empty", "N", COLORS.gray);
  const threatRegistryRow = threatVoiceInfo.endRow + 3;
  threat.getRangeByIndexes(threatRegistryRow - 1, 0, 1, matrices.threatRegistry[0].length).values = [matrices.threatRegistry[0]];
  styleHeader(threat.getRange(`A${threatRegistryRow}:${columnLetter(matrices.threatRegistry[0].length - 1)}${threatRegistryRow}`), COLORS.gray);
  applyUnsupportedFormatting(threat.getRange(`A5:N${threatVoiceInfo.endRow}`));
  threat.freezePanes.freezeRows(4);

  const affect = sheets["Affect Linkage"];
  titleBand(affect, "Affect Linkage", "A/B object passages linked to validated C-layer affect while preserving expression mode.", "N");
  labelBand(affect, 4, "By anchor", "N", COLORS.purple);
  addMatrix(affect, matrices.affectAnchor, 5, "AffectByAnchorTable", COLORS.purple);
  labelBand(affect, 13, "By anchor × affect mode", "N", COLORS.purple);
  const affectModeInfo = addMatrix(affect, matrices.affectMode, 14, "AffectByModeTable", COLORS.purple);
  affect.getRange("A6:H11").format.rowHeight = 42;
  affect.getRange(`A15:I${affectModeInfo.endRow}`).format.rowHeight = 34;
  labelBand(affect, affectModeInfo.endRow + 2, "Passage registry — currently empty", "N", COLORS.gray);
  const affectRegistryRow = affectModeInfo.endRow + 3;
  affect.getRangeByIndexes(affectRegistryRow - 1, 0, 1, matrices.affectRegistry[0].length).values = [matrices.affectRegistry[0]];
  styleHeader(affect.getRange(`A${affectRegistryRow}:${columnLetter(matrices.affectRegistry[0].length - 1)}${affectRegistryRow}`), COLORS.gray);
  applyUnsupportedFormatting(affect.getRange(`A5:N${affectModeInfo.endRow}`));
  affect.freezePanes.freezeRows(4);

  const voice = sheets["Voice Comparison"];
  titleBand(voice, "Voice Comparison", "Central anchor × voice table. Rates and threat-to-affect ratios are withheld when the A/B denominator is zero.", "M");
  addMatrix(voice, matrices.voice, 4, "VoiceLinkageSummaryTable", COLORS.navy2);
  applyUnsupportedFormatting(voice.getRange("A5:M34"));
  labelBand(voice, 37, "Constructed inventory context — not passage linkage", "M", COLORS.teal);
  addMatrix(voice, matrices.inventory, 38, "InventoryVoiceBalanceTable", COLORS.teal);
  voice.freezePanes.freezeRows(4);

  const lexical = sheets["Lexicalisation"];
  titleBand(lexical, "Lexicalisation", "Four temporal markers remain distinct: first Ngram nonzero, first sustained, first candidate attestation, and first candidate-level target sense.", "N");
  addMatrix(lexical, matrices.lexical, 4, "LexicalisationComparisonTable", COLORS.teal);
  applyUnsupportedFormatting(lexical.getRange("A5:N21"));
  mergeSet(lexical, "A24:N27", "Interpretation rule: raw Ngram appearance is not a coinage date. Candidate-level attestation and target-sense anchors are not first-ever dates and remain provisional until source-linked passage validation.", {
    fill: COLORS.amberLight,
    font: { name: "Arial", size: 11, bold: true, color: "#7B5B12" },
    horizontalAlignment: "center",
    borders: { preset: "all", style: "medium", color: COLORS.amber },
  });
  lexical.freezePanes.freezeRows(4);

  const gallery = sheets["Figure Gallery"];
  titleBand(gallery, "Figure Gallery", "Twelve designed relational figures. Each PNG has a matching SVG, source table and metadata record in the repository.", "Q");
  gallery.getRange("A4:B16").values = [
    ["Figure", "Title"],
    ...[
      "Research model", "Threat-link rate by anchor", "Affect-link rate by anchor",
      "Threat versus affect by anchor", "Threat linkage heatmap", "Affect linkage heatmap",
      "Climate framing lexicalisation", "Affect lexicalisation", "Threat lexicalisation",
      "Structure of the constructed inventory", "Searchability / corpus caution", "Ngram versus validated sense",
    ].map((title, index) => [index + 1, title]),
  ];
  styleHeader(gallery.getRange("A4:B4"), COLORS.navy2);
  gallery.getRange("A5:B16").format = { font: { name: "Arial", size: 9, color: COLORS.ink }, borders: { preset: "inside", style: "thin", color: COLORS.grid } };
  gallery.getRange("A:A").format.columnWidth = 10;
  gallery.getRange("B:B").format.columnWidth = 42;
  const figureStems = [
    "figure_01_research_model", "figure_02_threat_link_rate_by_anchor",
    "figure_03_affect_link_rate_by_anchor", "figure_04_threat_vs_affect_by_anchor",
    "figure_05_threat_linkage_heatmap", "figure_06_affect_linkage_heatmap",
    "figure_07_climate_framing_lexicalisation_timeline", "figure_08_affect_lexicalisation_timeline",
    "figure_09_threat_lexicalisation_timeline", "figure_10_inventory_structure_flow",
    "figure_11_searchability_corpus_caution", "figure_12_ngram_vs_validated_sense",
  ];
  for (let index = 0; index < figureStems.length; index += 1) {
    const col = index % 2 === 0 ? 3 : 10;
    const row = 4 + Math.floor(index / 2) * 20;
    gallery.images.add({
      dataUrl: await imageData(figureStems[index]),
      anchor: { from: { row, col }, extent: { widthPx: 520, heightPx: 325 } },
    });
  }
  gallery.getRange("C:Q").format.columnWidth = 10;
  gallery.freezePanes.freezeRows(2);

  const summary = sheets["Supervisor Summary"];
  titleBand(summary, "Supervisor Summary", "Relationship-centred historical analysis: what can be said now, and what remains passage-dependent.", "N");
  summary.getRange("A:N").format.columnWidth = 11;
  summary.getRange("A4:D4").values = [["Metric", "Value", "Status", "Meaning"]];
  summary.getRange("A5:A11").values = [
    ["Priority Candidates"], ["Validated A/B object passages"], ["Threat-linked passages"],
    ["Threat-link rate"], ["Affect-linked passages"], ["Affect-link rate"], ["Lexicalisation terms"],
  ];
  summary.getRange("B5:B11").formulas = [
    ["=COUNTA('Priority 180 Coverage'!A5:A184)"],
    ["=SUM('Threat Linkage'!B5:B10)"],
    ["=SUM('Threat Linkage'!C5:C10)"],
    ["=IF(B6=0,\"Not estimable\",B7/B6)"],
    ["=SUM('Affect Linkage'!C5:C10)"],
    ["=IF(B6=0,\"Not estimable\",B9/B6)"],
    ["=COUNTA('Lexicalisation'!A5:A21)"],
  ];
  summary.getRange("C5:C11").values = [
    ["CONSTRUCTED INVENTORY"], ["DATA GAP"], ["DATA GAP"], ["UNSUPPORTED"],
    ["DATA GAP"], ["UNSUPPORTED"], ["COMPUTED"],
  ];
  summary.getRange("D5:D11").values = [
    ["Candidate-level analytical inventory"],
    ["No populated passage chain"],
    ["No validated D relation rows"],
    ["Blank rate is not 0%"],
    ["No validated C relation rows"],
    ["Blank rate is not 0%"],
    ["Four marker trajectories kept distinct"],
  ];
  summary.getRange("A4:D11").format = { font: { name: "Arial", size: 10, color: COLORS.ink }, wrapText: true, borders: { preset: "all", style: "thin", color: COLORS.grid } };
  summary.getRange("A5:D11").format.rowHeight = 34;
  styleHeader(summary.getRange("A4:D4"), COLORS.navy2);
  applyUnsupportedFormatting(summary.getRange("A5:D11"));
  summary.getRange("A:A").format.columnWidth = 31;
  summary.getRange("B:B").format.columnWidth = 18;
  summary.getRange("C:C").format.columnWidth = 24;
  summary.getRange("D:D").format.columnWidth = 38;
  mergeSet(summary, "F4:N7", "What the analysis now measures\n\nValidated relations between temperature/climate objects and threat or explicit affect, compared across historical anchors and voices. Threat and affect remain analytically distinct.", {
    fill: COLORS.tealLight,
    font: { name: "Arial", size: 12, bold: true, color: COLORS.teal },
    horizontalAlignment: "center",
    borders: { preset: "all", style: "medium", color: COLORS.teal },
  });
  mergeSet(summary, "F9:N12", "Preliminary result\n\nThe lexical and discoverability layers are ready, but passage-level linkage rates are not yet estimable. The absence of passage rows is a documented data gap, not a negative historical finding.", {
    fill: COLORS.amberLight,
    font: { name: "Arial", size: 12, bold: true, color: "#7B5B12" },
    horizontalAlignment: "center",
    borders: { preset: "all", style: "medium", color: COLORS.amber },
  });
  labelBand(summary, 14, "Presentation figures", "N", COLORS.purple);
  const summaryFigures = [
    ["figure_01_research_model", 14, 0], ["figure_04_threat_vs_affect_by_anchor", 14, 7],
    ["figure_10_inventory_structure_flow", 35, 0], ["figure_11_searchability_corpus_caution", 35, 7],
  ];
  for (const [stem, row, col] of summaryFigures) {
    summary.images.add({ dataUrl: await imageData(stem), anchor: { from: { row, col }, extent: { widthPx: 560, heightPx: 350 } } });
  }
  mergeSet(summary, "A57:N61", "Next step\n\nTargeted semantic passage validation guided by the relationship results: retrieve source-linked A/B passages, validate C/D relations in context, preserve affect mode, and compare voices only after denominator quality checks.", {
    fill: COLORS.navy,
    font: { name: "Arial", size: 14, bold: true, color: COLORS.white },
    horizontalAlignment: "center",
  });
  summary.freezePanes.freezeRows(2);

  await fs.mkdir(previewDir, { recursive: true });
  const inspect = await workbook.inspect({
    kind: "table",
    range: "Supervisor Summary!A1:N12",
    include: "values,formulas",
    tableMaxRows: 20,
    tableMaxCols: 16,
    maxChars: 12000,
  });
  console.log(inspect.ndjson);
  const formulaErrors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 500 },
    summary: "relational workbook formula error scan",
  });
  console.log(formulaErrors.ndjson);

  const renderRanges = new Map([
    ["Relational Analysis", "A1:N26"], ["Threat Linkage", "A1:N48"],
    ["Affect Linkage", "A1:N44"], ["Voice Comparison", "A1:M68"],
    ["Lexicalisation", "A1:N27"], ["Figure Gallery", "A1:Q124"],
    ["Supervisor Summary", "A1:N61"],
  ]);
  for (const [sheetName, range] of renderRanges) {
    const preview = await workbook.render({ sheetName, range, scale: sheetName === "Figure Gallery" ? 0.5 : 0.8, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName.toLowerCase().replace(/[^a-z0-9]+/g, "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
  }

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });

  const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
  const reopenInspect = await reopened.inspect({
    kind: "table",
    range: "Supervisor Summary!A4:D11",
    include: "values,formulas",
    tableMaxRows: 12,
    tableMaxCols: 6,
    maxChars: 8000,
  });
  console.log(reopenInspect.ndjson);
  const reopenErrors = await reopened.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 500 },
    summary: "reopened relational workbook formula error scan",
  });
  console.log(reopenErrors.ndjson);
  const sheetInspection = await reopened.inspect({ kind: "sheet", include: "id,name", maxChars: 10000 });
  const validation = {
    status: "PASS",
    output_path: outputPath,
    new_sheet_names: newSheetNames,
    new_sheet_count: newSheetNames.length,
    source_priority_candidates: 180,
    validated_ab_object_passages: 0,
    threat_linked_passages: 0,
    affect_linked_passages: 0,
    lexicalisation_terms: 17,
    relational_figure_count: 12,
    embedded_relational_images: 16,
    rendered_new_sheets: renderRanges.size,
    formula_check: reopenErrors.ndjson.includes("matched 0 entries") || reopenErrors.ndjson.includes('"total":0') ? "PASS" : "REVIEW",
    artifact_tool_reopen_check: "PASS",
    sheet_inspection_contains_all_new_sheets: newSheetNames.every((name) => sheetInspection.ndjson.includes(name)),
    workbook_size_bytes: (await fs.stat(outputPath)).size,
  };
  if (validation.formula_check !== "PASS" || !validation.sheet_inspection_contains_all_new_sheets) {
    throw new Error(`workbook validation failed: ${JSON.stringify(validation)}`);
  }
  await fs.writeFile(validationPath, `${JSON.stringify(validation, null, 2)}\n`);
  console.log(JSON.stringify(validation, null, 2));
}

if (process.argv.includes("--inspect-existing")) await inspectExisting();
else await buildWorkbook();
