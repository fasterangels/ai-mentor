/**
 * Build a human-readable PDF report from the analysis result. BLOCK 9.1
 * Content: Header (app name + timestamp), Resolver, Evidence Pack, Analyzer Decision, NO_PREDICTION when applicable.
 * jsPDF is loaded dynamically at runtime so Vite does not bundle it in the web build.
 *
 * BLOCK 2: buildResultSummaryPdf — concise export from ResultVM (match header, resolver, analyzer, evaluation KPIs, evidence titles, notes/warnings).
 */

import type { ResultVM } from "../ui/result/types";

const APP_NAME = "AI Mentor";
const MARGIN = 14;
const MAX_WIDTH = 180;
const LINE_HEIGHT = 5.5;
const FONT_SIZE = 10;
const SECTION_GAP = 8;

function safeArray<T>(x: unknown): T[] {
  return Array.isArray(x) ? (x as T[]) : [];
}

function na(value: unknown): string {
  if (value === undefined || value === null) return "N/A";
  if (typeof value === "string" && value.trim() === "") return "N/A";
  return String(value);
}

function isNoPrediction(result: Record<string, unknown> | null | undefined): boolean {
  if (!result || typeof result !== "object") return false;
  const top = (result.status ?? "").toString().toUpperCase();
  const resolverStatus = ((result.resolver as Record<string, unknown>)?.status ?? "").toString().toUpperCase();
  const analyzerStatus = ((result.analyzer as Record<string, unknown>)?.status ?? "").toString().toUpperCase();
  if (["NO_PREDICTION", "NOT_FOUND", "AMBIGUOUS"].includes(top)) return true;
  if (["NOT_FOUND", "AMBIGUOUS"].includes(resolverStatus)) return true;
  if (analyzerStatus === "NO_PREDICTION") return true;
  const analyzer = result.analyzer as Record<string, unknown> | undefined;
  const flags = safeArray<string>(result.flags).concat(
    safeArray<string>(analyzer?.analysis_run && typeof analyzer.analysis_run === "object" ? (analyzer.analysis_run as Record<string, unknown>).flags : undefined)
  );
  if (flags.some((f) => /NO_PREDICTION|NO_BET|NO_DECISION/i.test(String(f)))) return true;
  const decisions = safeArray(analyzer?.decisions);
  if (decisions.some((d) => /NO_PREDICTION|NO_BET|NO_DECISION/i.test(String((d as Record<string, unknown>)?.decision ?? ""))))
    return true;
  return false;
}

function getNoPredictionMessage(result: Record<string, unknown> | null | undefined): string {
  if (!result) return "Not available";
  const resolverStatus = ((result.resolver as Record<string, unknown>)?.status ?? "").toString().toUpperCase();
  const top = (result.status ?? "").toString().toUpperCase();
  if (resolverStatus === "AMBIGUOUS" || top === "AMBIGUOUS")
    return "AMBIGUOUS: ο αγώνας δεν επιλύθηκε μονοσήμαντα.";
  if (resolverStatus === "NOT_FOUND" || top === "NOT_FOUND")
    return "NOT_FOUND: δεν βρέθηκε αγώνας στο παράθυρο kickoff.";
  if (top === "NO_PREDICTION")
    return "NO_PREDICTION: δεν υπάρχουν αρκετά αξιόπιστα δεδομένα/σήματα.";
  return "NO_PREDICTION: δεν υπάρχουν αρκετά αξιόπιστα δεδομένα/σήματα.";
}

/** Add wrapped text and return new y position */
function addWrappedText(doc: { splitTextToSize: (text: string, w: number) => string[]; text: (lines: string[] | string, x: number, y: number) => void }, text: string, x: number, y: number): number {
  const lines = doc.splitTextToSize(text, MAX_WIDTH);
  doc.text(lines, x, y);
  return y + lines.length * LINE_HEIGHT;
}

/** Add section title and return new y */
function addSectionTitle(doc: { setFont: (family: string, style?: string) => void; setFontSize: (size: number) => void; text: (s: string, x: number, y: number) => void }, title: string, x: number, y: number): number {
  doc.setFont("helvetica", "bold");
  doc.setFontSize(FONT_SIZE);
  doc.text(title, x, y);
  doc.setFont("helvetica", "normal");
  return y + LINE_HEIGHT + 2;
}

export async function buildAnalysisPdf(result: Record<string, unknown>): Promise<{ output: (format: string) => ArrayBuffer; save: (filename: string) => void }> {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF();
  doc.setFontSize(FONT_SIZE);
  let y = MARGIN;

  // Header: app name + timestamp
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text(APP_NAME, MARGIN, y);
  y += LINE_HEIGHT;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(FONT_SIZE);
  const timestamp = new Date().toISOString();
  y = addWrappedText(doc, `Report generated: ${timestamp}`, MARGIN, y);
  y += SECTION_GAP;

  // Resolver
  y = addSectionTitle(doc, "Resolver", MARGIN, y);
  const resolver = result?.resolver ?? {};
  const matchId = result?.match_id ?? resolver.match_id ?? null;
  y = addWrappedText(doc, `Status: ${na(resolver.status)} · Match ID: ${na(matchId)}`, MARGIN, y);
  const notes = safeArray<string>(resolver.notes).concat(safeArray<string>(result?.notes));
  if (notes.length > 0) {
    y += 2;
    for (const n of notes) {
      y = addWrappedText(doc, `• ${String(n)}`, MARGIN, y);
    }
  }
  y += SECTION_GAP;

  // Evidence Pack
  y = addSectionTitle(doc, "Evidence Pack", MARGIN, y);
  const ep = result?.evidence_pack;
  if (ep && typeof ep === "object") {
    const parts: string[] = [];
    if (ep.match_id != null) parts.push(`match_id: ${na(ep.match_id)}`);
    const domains = safeArray<string>(ep.domains);
    if (domains.length) parts.push(`domains: ${domains.join(", ")}`);
    if (ep.captured_at_utc != null) parts.push(`captured_at_utc: ${na(ep.captured_at_utc)}`);
    const epFlags = safeArray<string>(ep.flags);
    if (epFlags.length) parts.push(`flags: ${epFlags.join(", ")}`);
    y = addWrappedText(doc, parts.length ? parts.join(" · ") : "—", MARGIN, y);
  } else {
    y = addWrappedText(doc, "No evidence data", MARGIN, y);
  }
  y += SECTION_GAP;

  // Analyzer Decision
  y = addSectionTitle(doc, "Analyzer Decision", MARGIN, y);
  const analyzer = (result?.analyzer ?? {}) as Record<string, unknown>;
  const analysisRun = (analyzer.analysis_run ?? {}) as Record<string, unknown>;
  y = addWrappedText(
    doc,
    `Status: ${na(analyzer.status)}${analysisRun.logic_version != null ? ` · Logic: ${na(analysisRun.logic_version)}` : ""}`,
    MARGIN,
    y
  );
  const runFlags = safeArray<string>(analysisRun.flags);
  if (runFlags.length) {
    y = addWrappedText(doc, `Flags: ${runFlags.join(", ")}`, MARGIN, y);
  }
  const decisions = safeArray(analyzer.decisions);
  if (decisions.length > 0) {
    const summary = decisions.map((d: unknown) => {
      const o = d as Record<string, unknown>;
      return `${o?.market ?? "?"}: ${o?.decision ?? "—"}`;
    }).join("; ");
    y = addWrappedText(doc, `Decisions: ${summary}`, MARGIN, y);
  }
  y += SECTION_GAP;

  // NO_PREDICTION
  if (isNoPrediction(result)) {
    y = addSectionTitle(doc, "NO_PREDICTION", MARGIN, y);
    y = addWrappedText(doc, getNoPredictionMessage(result), MARGIN, y);
  }

  return doc;
}

/**
 * BLOCK 2: Build a concise, single-page-friendly PDF from ResultVM.
 * Content: Match header, Resolver status, Analyzer outcome + logic_version, Evaluation KPIs, Evidence titles only, Notes/warnings.
 * No raw JSON. Uses existing jsPDF (dynamic import).
 */
export async function buildResultSummaryPdf(
  vm: ResultVM
): Promise<{ output: (format: string) => ArrayBuffer; save: (filename: string) => void }> {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF();
  doc.setFontSize(FONT_SIZE);
  let y = MARGIN;

  // Header: app name + timestamp
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text(APP_NAME, MARGIN, y);
  y += LINE_HEIGHT;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(FONT_SIZE);
  y = addWrappedText(doc, `Report: ${new Date().toISOString()}`, MARGIN, y);
  y += SECTION_GAP;

  // Match header
  y = addSectionTitle(doc, "Match", MARGIN, y);
  const matchLine = [
    `Home: ${vm.homeTeam || "—"}`,
    `Away: ${vm.awayTeam || "—"}`,
    vm.matchId != null && vm.matchId !== "" ? `Match ID: ${vm.matchId}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  y = addWrappedText(doc, matchLine, MARGIN, y);
  y += SECTION_GAP;

  // Resolver status
  y = addSectionTitle(doc, "Resolver", MARGIN, y);
  y = addWrappedText(
    doc,
    `Status: ${na(vm.resolver?.status)}${vm.resolver?.matchId ? ` · Match ID: ${vm.resolver.matchId}` : ""}`,
    MARGIN,
    y
  );
  if (vm.resolver?.notes?.length) {
    y += 2;
    for (const n of vm.resolver.notes) {
      y = addWrappedText(doc, `• ${String(n)}`, MARGIN, y);
    }
  }
  y += SECTION_GAP;

  // Analyzer outcome + logic_version
  y = addSectionTitle(doc, "Analyzer", MARGIN, y);
  const analyzerLine = [
    `Outcome: ${na(vm.analyzer?.outcome ?? vm.analyzer?.statusLabel)}`,
    vm.analyzer?.logicVersion ? `Logic: ${vm.analyzer.logicVersion}` : "",
    vm.analyzer?.decisionCount != null ? `Decisions: ${vm.analyzer.decisionCount}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  y = addWrappedText(doc, analyzerLine, MARGIN, y);
  y += SECTION_GAP;

  // Evaluation KPIs (BLOCK 1)
  if (vm.evaluation != null && vm.evaluation.length > 0) {
    y = addSectionTitle(doc, "Evaluation", MARGIN, y);
    for (const kpi of vm.evaluation) {
      const line = `${kpi.label}: ${kpi.value}${kpi.unit != null && kpi.unit !== "" ? ` ${kpi.unit}` : ""}`;
      y = addWrappedText(doc, line, MARGIN, y);
    }
    y += SECTION_GAP;
  }

  // Evidence titles only
  y = addSectionTitle(doc, "Evidence", MARGIN, y);
  if (vm.evidence != null && vm.evidence.length > 0) {
    const titles = vm.evidence.map((e) => e.title || "—").filter(Boolean);
    y = addWrappedText(doc, titles.length ? titles.join(", ") : "—", MARGIN, y);
  } else {
    y = addWrappedText(doc, "—", MARGIN, y);
  }
  y += SECTION_GAP;

  // Notes / warnings
  const hasNotes = vm.notes != null && vm.notes.length > 0;
  const hasWarnings = vm.warnings != null && vm.warnings.length > 0;
  if (hasNotes || hasWarnings) {
    y = addSectionTitle(doc, "Notes / Warnings", MARGIN, y);
    if (hasNotes) {
      for (const n of vm.notes) {
        y = addWrappedText(doc, `• ${String(n)}`, MARGIN, y);
      }
    }
    if (hasWarnings) {
      for (const w of vm.warnings) {
        y = addWrappedText(doc, `⚠ ${String(w)}`, MARGIN, y);
      }
    }
  }

  return doc;
}
