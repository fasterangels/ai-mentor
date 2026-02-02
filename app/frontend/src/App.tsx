import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import { getBackendBaseUrl, isTauri } from "./api/backendBaseUrl";
import { mapApiToResultVM } from "./ui/result/mapper";
import ResultView from "./ui/result/ResultView";
import {
  getAnalyzeUIState,
  type ErrorKind,
} from "./ui/states/stateMachine";
import IdleState from "./ui/states/IdleState";
import LoadingState from "./ui/states/LoadingState";
import ErrorState from "./ui/states/ErrorState";
import EmptyResultState from "./ui/states/EmptyResultState";
import AppSettingsPanel from "./ui/settings/AppSettingsPanel";
import AppShell from "./ui/shell/AppShell";
import HomeScreen from "./ui/home/HomeScreen";
import { buildAnalysisPdf, buildResultSummaryPdf } from "./utils/buildAnalysisPdf";
import type { ResultVM } from "./ui/result/types";
import { t, labelResolverStatus, labelDecisionKind } from "./i18n";
import { buildInfoFormatted } from "./buildInfo";

/** Navigation view (no router). */
export type View = "HOME" | "NEW_PREDICTION" | "RESULT" | "SUMMARY" | "HISTORY" | "SETTINGS";

function viewToSidebarKey(view: View): string {
  switch (view) {
    case "HOME": return "home";
    case "NEW_PREDICTION":
    case "RESULT": return "predictions";
    case "SUMMARY": return "statistics";
    case "HISTORY": return "history";
    case "SETTINGS": return "settings";
    default: return "home";
  }
}

function viewToPageTitle(view: View): string {
  switch (view) {
    case "HOME": return t("page.home");
    case "NEW_PREDICTION": return t("page.new_prediction");
    case "RESULT": return t("page.result");
    case "SUMMARY": return t("page.summary");
    case "HISTORY": return t("page.history");
    case "SETTINGS": return t("page.settings");
    default: return t("page.home");
  }
}
const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const getInitialApiBase = () => DEFAULT_API_BASE;
const STORAGE_KEYS = {
  homeTeam: "ai-mentor.homeTeam",
  awayTeam: "ai-mentor.awayTeam",
  filters: "ai-mentor.filters",
  lastResult: "ai-mentor.lastResult",
  snapshots: "ai-mentor.snapshots",
  restoreWindowDefaults: "ai-mentor.restoreWindowDefaults",
  exportFileNameTemplate: "ai-mentor.exportFileNameTemplate",
} as const;
const LAST_RESULT_MAX_BYTES = 200 * 1024;
const SNAPSHOT_MAX_BYTES = 250 * 1024;
const SNAPSHOT_MAX_COUNT = 20;
const FILE_SIZE_WARN_BYTES = 2 * 1024 * 1024;
const PERSIST_DEBOUNCE_MS = 300;

// --- Types (defensive; all optional where backend may omit) ---
type Decision = {
  market?: string;
  decision?: string;
  confidence?: number;
  separation?: number;
  risk?: number;
  reasons?: string[];
  probabilities?: Record<string, number>;
  flags?: string[];
  policy?: Record<string, unknown>;
  evidence_refs?: unknown;
};

type AnalyzeResponse = {
  status?: string;
  match_id?: string | null;
  resolver?: {
    status?: string;
    match_id?: string | null;
    notes?: string[];
    candidates?: Array<Record<string, unknown>>;
  };
  evidence_pack?: {
    match_id?: string;
    domains?: string[];
    captured_at_utc?: string;
    flags?: string[];
  };
  analyzer?: {
    status?: string;
    analysis_run?: { logic_version?: string; flags?: string[] };
    decisions?: Decision[];
  };
  notes?: string[];
  flags?: string[];
};

// --- Helpers ---
function safeArray<T>(x: unknown): T[] {
  return Array.isArray(x) ? (x as T[]) : [];
}

function formatConfidence(n: unknown): string {
  if (typeof n !== "number" || Number.isNaN(n)) return "";
  return `${Math.round(n * 100)}%`;
}

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function copyText(text: string): Promise<boolean> {
  if (typeof navigator?.clipboard?.writeText === "function") {
    return navigator.clipboard.writeText(text).then(() => true).catch(() => false);
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "absolute";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return Promise.resolve(ok);
  } catch {
    return Promise.resolve(false);
  }
}

function getOutcomeBanner(
  result: AnalyzeResponse | null
): { kind: "AMBIGUOUS" | "NOT_FOUND" | "NO_PREDICTION" | null; message: string | null } {
  if (!result) return { kind: null, message: null };
  const topStatus = (result.status ?? "").toUpperCase();
  const resolverStatus = (result.resolver?.status ?? "").toUpperCase();
  if (resolverStatus === "AMBIGUOUS" || topStatus === "AMBIGUOUS")
    return { kind: "AMBIGUOUS", message: labelResolverStatus("AMBIGUOUS") + ": " + t("error.resolver_ambiguous") };
  if (resolverStatus === "NOT_FOUND" || topStatus === "NOT_FOUND")
    return { kind: "NOT_FOUND", message: labelResolverStatus("NOT_FOUND") + ": " + t("error.resolver_not_found") };
  if (topStatus === "NO_PREDICTION") return { kind: "NO_PREDICTION", message: labelDecisionKind("NO_PREDICTION") + ": " + t("error.analyzer_no_prediction") };
  const flags = safeArray<string>(result.flags).concat(
    safeArray<string>(result.analyzer?.analysis_run?.flags)
  );
  if (flags.some((f) => /NO_PREDICTION|NO_BET|NO_DECISION/i.test(String(f))))
    return { kind: "NO_PREDICTION", message: labelDecisionKind("NO_PREDICTION") + ": " + t("error.analyzer_no_prediction") };
  const decisions = safeArray(result.analyzer?.decisions);
  if (decisions.some((d) => /NO_PREDICTION|NO_BET|NO_DECISION/i.test(String(d.decision ?? ""))))
    return { kind: "NO_PREDICTION", message: labelDecisionKind("NO_PREDICTION") + ": " + t("error.analyzer_no_prediction") };
  return { kind: null, message: null };
}

// --- Decisions display helpers (BLOCK 8.8) ---
function normalizeMarketName(market?: string): string {
  const t = typeof market === "string" ? market.trim() : "";
  return t || "UNKNOWN";
}

function getDecisionKind(decision?: string): "PLAY" | "NO_BET" | "NO_PREDICTION" | "UNKNOWN" {
  const d = (decision ?? "").trim().toUpperCase();
  if (d === "NO_BET") return "NO_BET";
  if (d === "NO_PREDICTION") return "NO_PREDICTION";
  if (d === "NO_DECISION") return "NO_PREDICTION";
  if (d.length > 0) return "PLAY";
  return "UNKNOWN";
}

function flattenFlags(decision: Decision): string[] {
  const out: string[] = [];
  safeArray<string>(decision.flags).forEach((f) => out.push(String(f).trim()));
  const policy = decision.policy as { flags?: string[] } | undefined;
  if (policy && Array.isArray(policy.flags))
    policy.flags.forEach((f) => out.push(String(f).trim()));
  return [...new Set(out)].filter(Boolean);
}

function buildMarketGroups(decisions: Decision[]): Map<string, Decision[]> {
  const map = new Map<string, Decision[]>();
  for (const d of decisions) {
    const key = normalizeMarketName(d.market);
    const list = map.get(key) ?? [];
    list.push(d);
    map.set(key, list);
  }
  return map;
}

// Restore from localStorage (BLOCK 8.9)
function getStoredString(key: string, fallback: string): string {
  try {
    const v = localStorage.getItem(key);
    return typeof v === "string" && v.length > 0 ? v : fallback;
  } catch {
    return fallback;
  }
}

function getStoredFilters(): {
  marketFilter: string;
  kindFilter: string;
  flagFilter: string;
  searchText: string;
  sortBy: "confidence_desc" | "market_az" | "decision_az";
} {
  try {
    const j = localStorage.getItem(STORAGE_KEYS.filters);
    if (!j) return { marketFilter: "ALL", kindFilter: "ALL", flagFilter: "ALL", searchText: "", sortBy: "confidence_desc" };
    const o = JSON.parse(j) as Record<string, unknown>;
    return {
      marketFilter: typeof o?.marketFilter === "string" ? o.marketFilter : "ALL",
      kindFilter: typeof o?.kindFilter === "string" ? o.kindFilter : "ALL",
      flagFilter: typeof o?.flagFilter === "string" ? o.flagFilter : "ALL",
      searchText: typeof o?.searchText === "string" ? o.searchText : "",
      sortBy: o?.sortBy === "market_az" || o?.sortBy === "decision_az" ? o.sortBy : "confidence_desc",
    };
  } catch {
    return { marketFilter: "ALL", kindFilter: "ALL", flagFilter: "ALL", searchText: "", sortBy: "confidence_desc" };
  }
}

function getStoredResult(): AnalyzeResponse | null {
  try {
    const s = localStorage.getItem(STORAGE_KEYS.lastResult);
    if (!s || s.length > LAST_RESULT_MAX_BYTES) return null;
    return JSON.parse(s) as AnalyzeResponse;
  } catch {
    return null;
  }
}

// --- BLOCK 9.1: Snapshot type + text summary ---
type Snapshot = {
  id: string;
  created_at: string;
  homeTeam: string;
  awayTeam: string;
  httpStatus?: number | null;
  status?: string | null;
  resolver?: { status?: string; match_id?: string | number | null };
  banner?: { kind?: string | null; message?: string | null };
  filters: { marketFilter: string; kindFilter: string; flagFilter: string; searchText: string; sortBy: string };
  selected?: { market?: string | null; decision?: Decision | null };
  result: AnalyzeResponse;
  size_bytes: number;
};

function buildTextSummary(params: {
  timestamp: string;
  endpoint: string;
  homeTeam: string;
  awayTeam: string;
  result: AnalyzeResponse;
  httpStatus?: number | null;
  outcomeBanner: { kind: string | null; message: string | null };
  filteredDecisions: Decision[];
  kindCounts: { PLAY: number; NO_BET: number; NO_PREDICTION: number; UNKNOWN: number };
  filteredMarketKeys: string[];
  selectedMarket?: string | null;
  selectedDecision?: Decision | null;
}): string {
  const {
    timestamp,
    endpoint,
    homeTeam,
    awayTeam,
    result,
    httpStatus,
    outcomeBanner,
    filteredDecisions,
    kindCounts,
    filteredMarketKeys,
    selectedMarket,
    selectedDecision,
  } = params;
  const decisions = safeArray(result?.analyzer?.decisions);
  const candidates = safeArray(result?.resolver?.candidates);
  const lines: string[] = [];
  lines.push("AI ΜΕΝΤΟΡΑΣ — ANALYSIS SNAPSHOT");
  lines.push("Timestamp: " + timestamp);
  lines.push("Match input: " + (homeTeam || "—") + " vs " + (awayTeam || "—"));
  lines.push("Backend status: " + (result?.status ?? "—"));
  lines.push("HTTP status: " + (httpStatus != null ? String(httpStatus) : "—"));
  lines.push("");
  lines.push("Resolver:");
  lines.push("- status: " + (result?.resolver?.status ?? "—"));
  lines.push("- match_id: " + (result?.match_id ?? result?.resolver?.match_id ?? "—"));
  lines.push("- notes: " + (safeArray(result?.resolver?.notes).length ? "present" : "—"));
  lines.push("- candidates: " + candidates.length);
  lines.push("");
  lines.push("Outcome:");
  if (outcomeBanner.kind ?? outcomeBanner.message) {
    lines.push("- " + (outcomeBanner.kind ?? "—") + ": " + (outcomeBanner.message ?? "—"));
  } else {
    lines.push("- (none)");
  }
  lines.push("");
  lines.push("Decisions (filtered view):");
  lines.push("- total decisions: " + filteredDecisions.length);
  lines.push("- counts: PLAY " + kindCounts.PLAY + " | NO_BET " + kindCounts.NO_BET + " | NO_PREDICTION " + kindCounts.NO_PREDICTION + " | UNKNOWN " + kindCounts.UNKNOWN);
  const marketList = filteredMarketKeys.slice(0, 12);
  const more = filteredMarketKeys.length > 12 ? " (+" + (filteredMarketKeys.length - 12) + " more)" : "";
  lines.push("- markets: " + (marketList.join(", ") || "—") + more);
  lines.push("");
  if (selectedMarket != null || selectedDecision != null) {
    lines.push("Selected decision:");
    lines.push("- market: " + (selectedMarket ?? "—"));
    lines.push("- kind: " + (selectedDecision ? getDecisionKind(selectedDecision.decision) : "—"));
    lines.push("- decision: " + (selectedDecision?.decision ?? "—"));
    lines.push("- confidence: " + (selectedDecision ? formatConfidence(selectedDecision.confidence) : "—"));
    lines.push("- flags: " + (selectedDecision ? flattenFlags(selectedDecision).join(", ") || "—" : "—"));
    const reasons = safeArray<string>(selectedDecision?.reasons).slice(0, 10);
    lines.push("- reasons: " + (reasons.length ? reasons.join("; ") : "—"));
  } else {
    lines.push("Selected decision: (none)");
  }
  lines.push("");
  lines.push("Evidence/Analysis:");
  lines.push("- analyzer status: " + (result?.analyzer?.status ?? "—"));
  lines.push("- logic/policy version: " + (result?.analyzer?.analysis_run?.logic_version ?? "—"));
  lines.push("- evidence_pack present: " + (result?.evidence_pack ? "yes" : "no"));
  if (result?.evidence_pack) {
    lines.push("  (domains: " + safeArray(result.evidence_pack.domains).length + ")");
  }
  return lines.join("\n");
}

function getSnapshots(): Snapshot[] {
  try {
    const j = localStorage.getItem(STORAGE_KEYS.snapshots);
    if (!j) return [];
    const arr = JSON.parse(j) as Snapshot[];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function saveSnapshotsList(list: Snapshot[]): void {
  try {
    localStorage.setItem(STORAGE_KEYS.snapshots, JSON.stringify(list.slice(-SNAPSHOT_MAX_COUNT)));
  } catch {
    /* ignore */
  }
}

function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// --- BLOCK 9.3: Validation + Import helpers ---
function isPlainObject(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

function safeParseJson(text: string): { ok: true; value: unknown } | { ok: false; error: string } {
  try {
    const value = JSON.parse(text);
    return { ok: true, value };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Invalid JSON" };
  }
}

function validateAnalyzeResponse(x: unknown): { ok: true; value: AnalyzeResponse } | { ok: false; error: string } {
  if (!isPlainObject(x)) return { ok: false, error: "Not an object" };
  if (x.status !== undefined && typeof x.status !== "string") return { ok: false, error: "status must be string" };
  if (x.resolver !== undefined) {
    if (!isPlainObject(x.resolver)) return { ok: false, error: "resolver must be object" };
    if (x.resolver.status !== undefined && typeof x.resolver.status !== "string") return { ok: false, error: "resolver.status must be string" };
  }
  if (x.analyzer !== undefined && !isPlainObject(x.analyzer)) return { ok: false, error: "analyzer must be object" };
  if (x.analyzer?.decisions !== undefined && !Array.isArray((x.analyzer as Record<string, unknown>).decisions))
    return { ok: false, error: "analyzer.decisions must be array" };
  return { ok: true, value: x as AnalyzeResponse };
}

function validateSnapshot(x: unknown): { ok: true; value: Snapshot } | { ok: false; error: string } {
  if (!isPlainObject(x)) return { ok: false, error: "Not an object" };
  if (typeof (x as Snapshot).id !== "string") return { ok: false, error: "id must be string" };
  if (typeof (x as Snapshot).created_at !== "string") return { ok: false, error: "created_at must be string" };
  if (typeof (x as Snapshot).homeTeam !== "string") return { ok: false, error: "homeTeam must be string" };
  if (typeof (x as Snapshot).awayTeam !== "string") return { ok: false, error: "awayTeam must be string" };
  if (!isPlainObject((x as Snapshot).result)) return { ok: false, error: "result must be object" };
  const snap = x as Snapshot;
  const str = JSON.stringify(snap);
  const size = new TextEncoder().encode(str).length;
  if (size > SNAPSHOT_MAX_BYTES) return { ok: false, error: "Snapshot exceeds 250KB" };
  return { ok: true, value: { ...snap, size_bytes: (snap as Snapshot).size_bytes ?? size } };
}

function validateSnapshotBundle(x: unknown): { ok: true; value: { snapshots: Snapshot[]; rejectedCount: number }; warn?: string } | { ok: false; error: string } {
  if (!isPlainObject(x)) return { ok: false, error: "Not an object" };
  const arr = (x as { snapshots?: unknown }).snapshots;
  if (!Array.isArray(arr)) return { ok: false, error: "snapshots array missing" };
  let warn: string | undefined;
  if ((x as { app?: string }).app !== "ai-mentor" || (x as { bundle_version?: string }).bundle_version !== "1")
    warn = "Bundle app/version mismatch; importing if snapshots valid.";
  const snapshots: Snapshot[] = [];
  for (let i = 0; i < arr.length; i++) {
    const out = validateSnapshot(arr[i]);
    if (out.ok) snapshots.push(out.value);
  }
  const rejectedCount = arr.length - snapshots.length;
  return { ok: true, value: { snapshots, rejectedCount }, warn };
}

// --- BLOCK 9.2: CSV + Report helpers ---
function csvEscape(value: unknown, delimiter: string): string {
  if (value == null) return "";
  let s = String(value).replace(/\r\n/g, "\n");
  const needsQuotes = /["\n]/.test(s) || s.includes(delimiter);
  if (needsQuotes) s = '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function toPercentInt(confidence?: number): string {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) return "";
  if (confidence >= 0 && confidence <= 1) return Math.round(confidence * 100).toString();
  if (confidence >= 1 && confidence <= 100) return Math.round(confidence).toString();
  return "";
}

function joinCapped(arr: unknown[], cap: number): string {
  if (!Array.isArray(arr)) return "";
  const strs = arr.slice(0, cap).map((x) => String(x ?? ""));
  return strs.join(" | ");
}

function downloadCsv(filename: string, csvText: string): void {
  const blob = new Blob(["\uFEFF" + csvText], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function buildReportHtml(params: {
  timestamp: string;
  endpoint: string;
  homeTeam: string;
  awayTeam: string;
  result: AnalyzeResponse;
  httpStatus?: number | null;
  outcomeBanner: { kind: string | null; message: string | null };
  scopeDecisions: Decision[];
  scopeKindCounts: { PLAY: number; NO_BET: number; NO_PREDICTION: number; UNKNOWN: number };
  scopeMarketKeys: string[];
  selectedMarket?: string | null;
  selectedDecision?: Decision | null;
  includeAppendices: boolean;
}): string {
  const {
    timestamp,
    endpoint,
    homeTeam,
    awayTeam,
    result,
    httpStatus,
    outcomeBanner,
    scopeDecisions,
    scopeKindCounts,
    scopeMarketKeys,
    selectedMarket,
    selectedDecision,
    includeAppendices,
  } = params;
  const notes = safeArray(result?.resolver?.notes);
  const candidates = safeArray(result?.resolver?.candidates);
  const localTime = new Date(timestamp).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  const marketList = scopeMarketKeys.slice(0, 12);
  const moreMarkets = scopeMarketKeys.length > 12 ? " (+" + (scopeMarketKeys.length - 12) + " more)" : "";
  const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const style = `
    body { font-family: system-ui, Arial, sans-serif; font-size: 12px; line-height: 1.4; color: #111; max-width: 800px; margin: 0 auto; padding: 16px; }
    h1 { font-size: 18px; margin: 0 0 8px 0; }
    h2 { font-size: 14px; margin: 16px 0 6px 0; border-bottom: 1px solid #ccc; }
    p { margin: 4px 0; }
    ul { margin: 4px 0; padding-left: 20px; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px; }
    th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
    th { background: #f5f5f5; font-weight: 600; }
    tr { break-inside: avoid; }
    pre { font-size: 10px; overflow: auto; background: #f8f8f8; padding: 10px; border: 1px solid #eee; white-space: pre-wrap; word-break: break-word; max-height: 300px; }
    .muted { color: #666; font-size: 11px; }
    .footer { margin-top: 24px; font-size: 10px; color: #888; }
  `;
  let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>AI Μέντορας — Match Report</title><style>${style}</style></head><body>`;
  html += `<h1>AI Μέντορας — Match Report</h1>`;
  html += `<p class="muted">${localTime} · ${endpoint}</p>`;
  html += `<p><strong>Match input:</strong> ${esc(homeTeam || "—")} vs ${esc(awayTeam || "—")}</p>`;
  html += `<p><strong>Status:</strong> ${esc(result?.status ?? "—")}${httpStatus != null ? " · HTTP " + httpStatus : ""}</p>`;

  html += `<h2>Resolver</h2>`;
  html += `<p>status: ${esc(result?.resolver?.status ?? "—")} · match_id: ${esc(String(result?.match_id ?? result?.resolver?.match_id ?? "—"))}</p>`;
  html += notes.length ? "<ul>" + notes.slice(0, 12).map((n) => "<li>" + esc(String(n ?? "")) + "</li>").join("") + "</ul>" : "<p>—</p>";
  html += `<p>candidates: ${candidates.length}</p>`;

  html += `<h2>Outcome</h2>`;
  html += `<p>${(outcomeBanner.kind ?? outcomeBanner.message) ? esc((outcomeBanner.kind ?? "") + ": " + (outcomeBanner.message ?? "")) : "(none)"}</p>`;

  html += `<h2>Decisions summary</h2>`;
  html += `<p>total: ${scopeDecisions.length} · PLAY ${scopeKindCounts.PLAY} | NO_BET ${scopeKindCounts.NO_BET} | NO_PREDICTION ${scopeKindCounts.NO_PREDICTION} | UNKNOWN ${scopeKindCounts.UNKNOWN}</p>`;
  html += `<p>markets: ${marketList.join(", ") || "—"}${moreMarkets}</p>`;

  html += `<h2>Decisions table</h2>`;
  html += `<table><thead><tr><th>Market</th><th>Decision</th><th>Kind</th><th>Conf%</th><th>Flags</th></tr></thead><tbody>`;
  for (const d of scopeDecisions) {
    const kind = getDecisionKind(d.decision);
    const conf = toPercentInt(d.confidence);
    const flags = flattenFlags(d).join(", ");
    html += `<tr><td>${esc(d.market ?? "")}</td><td>${esc(d.decision ?? "")}</td><td>${esc(kind)}</td><td>${esc(conf)}</td><td>${esc(flags)}</td></tr>`;
  }
  html += `</tbody></table>`;

  if (selectedMarket != null || selectedDecision != null) {
    html += `<h2>Selected decision</h2>`;
    html += `<p>market: ${esc(selectedMarket ?? "—")} · kind: ${selectedDecision ? esc(getDecisionKind(selectedDecision.decision)) : "—"}</p>`;
    html += `<p>decision: ${esc(selectedDecision?.decision ?? "—")} · confidence: ${selectedDecision ? esc(toPercentInt(selectedDecision.confidence)) : "—"}</p>`;
    html += `<p>flags: ${selectedDecision ? esc(flattenFlags(selectedDecision).join(", ")) : "—"}</p>`;
    const reasons = safeArray<string>(selectedDecision?.reasons).slice(0, 10);
    html += `<p>reasons: ${reasons.length ? esc(reasons.join("; ")) : "—"}</p>`;
  }

  html += `<h2>Evidence / Analysis</h2>`;
  html += `<p>analyzer status: ${esc(result?.analyzer?.status ?? "—")} · logic version: ${esc(result?.analyzer?.analysis_run?.logic_version ?? "—")}</p>`;
  html += `<p>evidence_pack: ${result?.evidence_pack ? "yes (domains: " + safeArray(result.evidence_pack.domains).length + ")" : "no"}</p>`;

  if (includeAppendices) {
    html += `<h2>Appendix A — Raw result JSON</h2><pre>${safeStringify(result).replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>`;
    if (selectedDecision != null) {
      html += `<h2>Appendix B — Selected decision JSON</h2><pre>${safeStringify(selectedDecision).replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>`;
    }
  }

  html += `<p class="footer">Deterministic export — no inferred predictions beyond backend fields.</p>`;
  html += `</body></html>`;
  return html;
}

function App() {
  const [home, setHome] = useState(() => getStoredString(STORAGE_KEYS.homeTeam, "PAOK"));
  const [away, setAway] = useState(() => getStoredString(STORAGE_KEYS.awayTeam, "AEK"));
  const [result, setResult] = useState<AnalyzeResponse | null>(getStoredResult);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ErrorKind | null>(null);
  const [httpStatus, setHttpStatus] = useState<number | null>(null);
  const [lastErrorDebug, setLastErrorDebug] = useState<{
    httpStatus: number | null;
    endpoint: string;
    timestamp: string;
    home: string;
    away: string;
    responsePreview: string;
  } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const [marketFilter, setMarketFilter] = useState(() => getStoredFilters().marketFilter);
  const [kindFilter, setKindFilter] = useState(() => getStoredFilters().kindFilter);
  const [flagFilter, setFlagFilter] = useState(() => getStoredFilters().flagFilter);
  const [searchText, setSearchText] = useState(() => getStoredFilters().searchText);
  const [sortBy, setSortBy] = useState<"confidence_desc" | "market_az" | "decision_az">(() => getStoredFilters().sortBy);
  const [selectedDecision, setSelectedDecision] = useState<Decision | null>(null);
  const [selectedMarket, setSelectedMarket] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>(() => getSnapshots());
  const [snapshotError, setSnapshotError] = useState<string | null>(null);
  const [exportAnalysisError, setExportAnalysisError] = useState<string | null>(null);
  const [exportPdfError, setExportPdfError] = useState<string | null>(null);
  const [csvDelimiter, setCsvDelimiter] = useState<";" | ",">(";");
  const [reportScope, setReportScope] = useState<"FILTERED" | "ALL">("FILTERED");
  const [reportIncludeAppendices, setReportIncludeAppendices] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [bundleImportMode, setBundleImportMode] = useState<"merge" | "replace">("merge");
  const [bundleDedupe, setBundleDedupe] = useState(true);
  const [isDragOver, setIsDragOver] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [view, setView] = useState<View>("HOME");
  const [toast, setToast] = useState<{ id: string; kind: "success" | "warn" | "error"; message: string } | null>(null);
  const [apiBase, setApiBase] = useState(getInitialApiBase);
  const [backendReady, setBackendReady] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"READY" | "STARTING" | "NOT_READY" | null>(null);
  const [appVersion, setAppVersion] = useState<string>("—");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bundleFileInputRef = useRef<HTMLInputElement>(null);
  const toastTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dragLeaveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showToastRef = useRef<(kind: "success" | "warn" | "error", message: string) => void>(() => {});
  const handleImportedFileRef = useRef<(file: File, source: "drop" | "file") => Promise<void>>(async () => {});
  const decisionsHeadingRef = useRef<HTMLDivElement>(null);
  const firstDecisionRowRef = useRef<HTMLDivElement>(null);
  const prevLoadingRef = useRef(loading);

  // Resolve apiBase (fixed 127.0.0.1:8000 in desktop).
  useEffect(() => {
    getBackendBaseUrl()
      .then(setApiBase)
      .catch(() => setApiBase(DEFAULT_API_BASE));
  }, []);

  // Desktop hardening: health check with backoff (1s, 2s, 4s; max 3). Non-blocking; Analyze disabled until ready.
  const healthTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!isTauri()) return;
    const delays = [1000, 2000, 4000];
    let cancelled = false;
    const base = DEFAULT_API_BASE;
    const run = (attempt: number) => {
      if (cancelled || attempt >= 3) return;
      const delay = delays[attempt];
      healthTimeoutRef.current = setTimeout(() => {
        if (cancelled) return;
        fetch(`${base}/health`, { method: "GET" })
          .then((res) => {
            if (cancelled) return;
            if (res.ok) setBackendReady(true);
            else run(attempt + 1);
          })
          .catch(() => run(attempt + 1));
      }, delay);
    };
    run(0);
    return () => {
      cancelled = true;
      if (healthTimeoutRef.current) clearTimeout(healthTimeoutRef.current);
      healthTimeoutRef.current = null;
    };
  }, []);

  // In browser (non-Tauri) allow Analyze immediately; health may still be polling.
  useEffect(() => {
    if (!isTauri()) setBackendReady(true);
  }, []);

  // Tauri: poll backend status (READY / STARTING / NOT_READY) for UI and NOT_READY fallback.
  useEffect(() => {
    if (!isTauri()) return;
    let cancelled = false;
    const poll = () => {
      if (cancelled) return;
      import("@tauri-apps/api/core")
        .then(({ invoke }) => invoke<string>("get_backend_status"))
        .then((s) => {
          if (!cancelled && (s === "READY" || s === "STARTING" || s === "NOT_READY")) setBackendStatus(s);
        })
        .catch(() => {});
    };
    poll();
    const id = setInterval(poll, 500);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  // App version (Tauri: from API; browser: fallback).
  useEffect(() => {
    if (!isTauri()) {
      setAppVersion("0.2.0");
      return;
    }
    import("@tauri-apps/api/app")
      .then(({ getVersion }) => getVersion())
      .then(setAppVersion)
      .catch(() => setAppVersion("—"));
  }, []);

  // Log build info to app log on startup (Tauri only).
  useEffect(() => {
    if (!isTauri()) return;
    import("@tauri-apps/api/core")
      .then(({ invoke }) => invoke("log_app_message", { message: `FRONTEND_START ${buildInfoFormatted}` }))
      .catch(() => {});
  }, []);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (copiedKey === null) return;
    const t = setTimeout(() => setCopiedKey(null), 1000);
    return () => clearTimeout(t);
  }, [copiedKey]);

  const handleCopy = (key: string, text: string) => {
    copyText(text).then((ok) => { if (ok) setCopiedKey(key); });
  };

  const handleCopySummary = () => {
    if (!result) return;
    const text = buildTextSummary({
      timestamp: new Date().toISOString(),
      endpoint: `${apiBase}/api/v1/analyze`,
      homeTeam: home,
      awayTeam: away,
      result,
      httpStatus,
      outcomeBanner,
      filteredDecisions,
      kindCounts,
      filteredMarketKeys,
      selectedMarket,
      selectedDecision,
    });
    copyText(text).then((ok) => { if (ok) setCopiedKey("summary"); });
  };

  const handleDownloadResultJson = () => {
    if (!result) return;
    const now = new Date();
    const ymd = now.toISOString().slice(0, 10).replace(/-/g, "");
    const hms = now.toTimeString().slice(0, 8).replace(/:/g, "");
    const safe = (s: string) => s.replace(/[^a-zA-Z0-9-_]/g, "_").slice(0, 30);
    const filename = `ai-mentor_${safe(home)}_${safe(away)}_${ymd}_${hms}.json`;
    downloadJson(filename, result);
  };

  /** Export analysis as JSON: Tauri Save dialog + fs.writeFile, or browser download. BLOCK 9.0 */
  const handleExportAnalysisJson = async () => {
    if (!result) return;
    setExportAnalysisError(null);
    const matchId = result.match_id ?? result.resolver?.match_id;
    const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const defaultFilename = matchId != null && String(matchId).trim()
      ? `analysis_${String(matchId).replace(/[^a-zA-Z0-9-_]/g, "_").slice(0, 40)}.json`
      : `analysis_${ts}.json`;

    if (isTauri()) {
      try {
        const { openSaveDialog, saveJsonFile } = await import("./utils/tauriExport");
        const path = await openSaveDialog(defaultFilename, [
          { name: "JSON", extensions: ["json"] },
        ]);
        if (path) {
          await saveJsonFile(path, JSON.stringify(result, null, 2));
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setExportAnalysisError(msg);
      }
      return;
    }
    downloadJson(defaultFilename, result);
  };

  /** Export analysis as PDF: Tauri Save dialog + fs.writeFile, or browser download. BLOCK 9.1 */
  const handleExportAnalysisPdf = async () => {
    if (!result) return;
    setExportPdfError(null);
    const matchId = result.match_id ?? result.resolver?.match_id;
    const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const defaultFilename =
      matchId != null && String(matchId).trim()
        ? `analysis_${String(matchId).replace(/[^a-zA-Z0-9-_]/g, "_").slice(0, 40)}.pdf`
        : `analysis_${ts}.pdf`;

    const doc = await buildAnalysisPdf(result);
    const arrayBuffer = doc.output("arraybuffer");
    const pdfBytes = new Uint8Array(arrayBuffer as ArrayBuffer);

    if (isTauri()) {
      try {
        const { openSaveDialog, savePdfFile } = await import("./utils/tauriExport");
        const path = await openSaveDialog(defaultFilename, [
          { name: "PDF", extensions: ["pdf"] },
        ]);
        if (path) {
          await savePdfFile(path, pdfBytes);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setExportPdfError(msg);
      }
      return;
    }
    doc.save(defaultFilename);
  };

  /** BLOCK 2: Export concise result summary as PDF (from ResultVM). */
  const handleExportResultSummary = async (vm: ResultVM) => {
    setExportPdfError(null);
    const matchId = vm.matchId ?? vm.resolver?.matchId;
    const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const defaultFilename =
      matchId != null && String(matchId).trim()
        ? `result_${String(matchId).replace(/[^a-zA-Z0-9-_]/g, "_").slice(0, 40)}.pdf`
        : `result_${ts}.pdf`;

    const doc = await buildResultSummaryPdf(vm);
    const arrayBuffer = doc.output("arraybuffer");
    const pdfBytes = new Uint8Array(arrayBuffer as ArrayBuffer);

    if (isTauri()) {
      try {
        const { openSaveDialog, savePdfFile } = await import("./utils/tauriExport");
        const path = await openSaveDialog(defaultFilename, [
          { name: "PDF", extensions: ["pdf"] },
        ]);
        if (path) {
          await savePdfFile(path, pdfBytes);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setExportPdfError(msg);
      }
      return;
    }
    doc.save(defaultFilename);
  };

  const handleDownloadSelectedDecisionJson = () => {
    if (!selectedDecision) return;
    const payload = {
      timestamp: new Date().toISOString(),
      homeTeam: home,
      awayTeam: away,
      selectedMarket: selectedMarket ?? null,
      decision: selectedDecision,
    };
    const now = new Date();
    const ymd = now.toISOString().slice(0, 10).replace(/-/g, "");
    const hms = now.toTimeString().slice(0, 8).replace(/:/g, "");
    downloadJson(`ai-mentor_decision_${ymd}_${hms}.json`, payload);
  };

  const handleSaveSnapshot = () => {
    if (!result) return;
    const snapshot: Snapshot = {
      id: Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 8),
      created_at: new Date().toISOString(),
      homeTeam: home,
      awayTeam: away,
      httpStatus: httpStatus ?? null,
      status: result?.status ?? null,
      resolver: result?.resolver ? { status: result.resolver.status, match_id: result.resolver.match_id ?? result.match_id } : undefined,
      banner: outcomeBanner.kind || outcomeBanner.message ? { kind: outcomeBanner.kind ?? null, message: outcomeBanner.message ?? null } : undefined,
      filters: { marketFilter, kindFilter, flagFilter, searchText, sortBy },
      selected: selectedMarket != null || selectedDecision != null ? { market: selectedMarket ?? null, decision: selectedDecision ?? null } : undefined,
      result,
      size_bytes: 0,
    };
    const str = JSON.stringify(snapshot);
    snapshot.size_bytes = new TextEncoder().encode(str).length;
    if (snapshot.size_bytes > SNAPSHOT_MAX_BYTES) {
      setSnapshotError(t("snapshot_too_large"));
      setTimeout(() => setSnapshotError(null), 4000);
      return;
    }
    setSnapshotError(null);
    const list = [...getSnapshots(), snapshot].slice(-SNAPSHOT_MAX_COUNT);
    saveSnapshotsList(list);
    setSnapshots(list);
  };

  const loadSnapshot = (snap: Snapshot) => {
    setHome(snap.homeTeam);
    setAway(snap.awayTeam);
    setResult(snap.result);
    setHttpStatus(snap.httpStatus ?? null);
    setErrorMessage(null);
    setLastErrorDebug(null);
    setMarketFilter(snap.filters.marketFilter);
    setKindFilter(snap.filters.kindFilter);
    setFlagFilter(snap.filters.flagFilter);
    setSearchText(snap.filters.searchText);
    setSortBy(snap.filters.sortBy);
    setSelectedMarket(snap.selected?.market ?? null);
    setSelectedDecision(snap.selected?.decision ?? null);
  };

  const deleteSnapshot = (id: string) => {
    const list = getSnapshots().filter((s) => s.id !== id);
    saveSnapshotsList(list);
    setSnapshots(list);
  };

  const deleteAllSnapshots = () => {
    if (!window.confirm(t("delete_all_confirm"))) return;
    saveSnapshotsList([]);
    setSnapshots([]);
  };

  const getCsvRows = (scope: "filtered" | "all" | "selectedMarket"): Decision[] => {
    if (scope === "filtered") return filteredDecisions;
    if (scope === "all") return decisions;
    if (scope === "selectedMarket" && selectedMarket != null) {
      return filteredDecisions.filter((d) => normalizeMarketName(d.market) === selectedMarket);
    }
    return [];
  };

  const buildCsvText = (rows: Decision[]): string => {
    const ts = new Date().toISOString();
    const delim = csvDelimiter;
    const header = ["timestamp", "homeTeam", "awayTeam", "backend_status", "http_status", "resolver_status", "match_id", "market", "kind", "decision", "confidence_pct", "flags", "reasons"].join(delim);
    const lines: string[] = [];
    if (delim === ";") lines.push("sep=;");
    lines.push(header);
    for (const d of rows) {
      const resolverStatus = result?.resolver?.status ?? "";
      const matchId = result?.match_id ?? result?.resolver?.match_id ?? "";
      const row = [
        csvEscape(ts, delim),
        csvEscape(home, delim),
        csvEscape(away, delim),
        csvEscape(result?.status ?? "", delim),
        csvEscape(httpStatus ?? "", delim),
        csvEscape(resolverStatus, delim),
        csvEscape(matchId, delim),
        csvEscape(d.market ?? "", delim),
        csvEscape(getDecisionKind(d.decision), delim),
        csvEscape(d.decision ?? "", delim),
        csvEscape(toPercentInt(d.confidence), delim),
        csvEscape(flattenFlags(d).join(" | "), delim),
        csvEscape(joinCapped(safeArray(d.reasons), 10), delim),
      ];
      lines.push(row.join(delim));
    }
    return lines.join("\r\n");
  };

  const handleDownloadCsv = (scope: "filtered" | "all" | "selectedMarket") => {
    if (!result) return;
    const rows = getCsvRows(scope);
    const csvText = buildCsvText(rows);
    const now = new Date();
    const ymd = now.toISOString().slice(0, 10).replace(/-/g, "");
    const hms = now.toTimeString().slice(0, 8).replace(/:/g, "");
    const safe = (s: string) => s.replace(/[^a-zA-Z0-9-_]/g, "_").slice(0, 20);
    const suffix = scope === "selectedMarket" ? "_" + (selectedMarket ?? "market").replace(/\s/g, "_") : "";
    const filename = `ai-mentor_decisions_${safe(home)}_${safe(away)}_${ymd}_${hms}${suffix}.csv`;
    downloadCsv(filename, csvText);
  };

  const handlePrintReport = () => {
    if (!result) return;
    setReportError(null);
    const scopeDecisions = reportScope === "ALL" ? decisions : filteredDecisions;
    const scopeGroups = buildMarketGroups(scopeDecisions);
    const scopeMarketKeys = [...scopeGroups.keys()].sort((a, b) => a.localeCompare(b));
    const scopeKindCounts = { PLAY: 0, NO_BET: 0, NO_PREDICTION: 0, UNKNOWN: 0 };
    scopeDecisions.forEach((d) => { scopeKindCounts[getDecisionKind(d.decision)] += 1; });
    const html = buildReportHtml({
      timestamp: new Date().toISOString(),
      endpoint: `${apiBase}/api/v1/analyze`,
      homeTeam: home,
      awayTeam: away,
      result,
      httpStatus,
      outcomeBanner,
      scopeDecisions,
      scopeKindCounts,
      scopeMarketKeys,
      selectedMarket,
      selectedDecision,
      includeAppendices: reportIncludeAppendices,
    });
    const w = window.open("", "_blank", "noopener,noreferrer");
    if (!w) {
      setReportError(t("popup_blocked"));
      return;
    }
    w.document.open();
    w.document.write(html);
    w.document.close();
    w.focus();
    w.print();
  };

  const readFileAsText = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (file.size > FILE_SIZE_WARN_BYTES && !window.confirm(t("confirm.file_too_large"))) {
        reject(new Error("Aborted by user"));
        return;
      }
      const r = new FileReader();
      r.onload = () => resolve(String(r.result ?? ""));
      r.onerror = () => reject(new Error("Failed to read file"));
      r.readAsText(file, "UTF-8");
    });
  };

  const showToast = (kind: "success" | "warn" | "error", message: string) => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    const id = Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 8);
    setToast({ id, kind, message });
    toastTimeoutRef.current = setTimeout(() => {
      setToast(null);
      toastTimeoutRef.current = null;
    }, 2500);
  };

  const handleImportedFile = async (file: File, _source: "drop" | "file"): Promise<void> => {
    setImportStatus(null);
    try {
      const text = await readFileAsText(file);
      const parsed = safeParseJson(text);
      if (!parsed.ok) {
        const errMsg = t("error.invalid_json");
        setImportStatus("error: " + errMsg);
        showToast("error", errMsg);
        return;
      }
      const v = parsed.value;

      if (isPlainObject(v) && Array.isArray((v as { snapshots?: unknown }).snapshots)) {
        const bundle = validateSnapshotBundle(v);
        if (!bundle.ok) {
          setImportStatus("error: " + bundle.error);
          showToast("error", bundle.error);
          return;
        }
        const { snapshots: imported, rejectedCount } = bundle.value;
        let list: Snapshot[];
        if (bundleImportMode === "replace") {
          list = imported.slice(-SNAPSHOT_MAX_COUNT);
        } else {
          const existing = getSnapshots();
          const byId = new Map<string, Snapshot>();
          for (const s of [...existing, ...imported]) {
            const existingItem = byId.get(s.id);
            if (!existingItem || (bundleDedupe && new Date(s.created_at) > new Date(existingItem.created_at)))
              byId.set(s.id, s);
          }
          list = [...byId.values()].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, SNAPSHOT_MAX_COUNT);
        }
        saveSnapshotsList(list);
        setSnapshots(list);
        const statusMsg = rejectedCount > 0
          ? t("import.imported_prefix") + " " + list.length + " " + t("import.snapshots") + " (" + rejectedCount + " " + t("import.rejected") + ")."
          : t("import.imported_prefix") + " " + list.length + " " + t("import.snapshots") + ".";
        setImportStatus(bundle.warn ? statusMsg + " " + t("import.bundle_mismatch") : statusMsg);
        showToast(bundle.warn ? "warn" : "success", bundle.warn ? statusMsg + " " + t("import.bundle_mismatch") : statusMsg);
        return;
      }

      if (isPlainObject(v) && (v as { decision?: unknown }).decision !== undefined) {
        const d = v as { homeTeam?: string; awayTeam?: string; selectedMarket?: string; decision?: unknown };
        if (!isPlainObject(d.decision)) {
          const errMsg = t("error.decision_object");
          setImportStatus("error: " + errMsg);
          showToast("error", errMsg);
          return;
        }
        setSelectedMarket(typeof d.selectedMarket === "string" ? d.selectedMarket : null);
        setSelectedDecision(d.decision as Decision);
        if (typeof d.homeTeam === "string" && d.homeTeam.trim()) setHome(d.homeTeam.trim());
        if (typeof d.awayTeam === "string" && d.awayTeam.trim()) setAway(d.awayTeam.trim());
        setImportStatus(t("import.loaded_decision"));
        showToast("success", t("import.loaded_decision"));
        return;
      }

      const resultValid = validateAnalyzeResponse(v);
      if (resultValid.ok) {
        setResult(resultValid.value);
        setHttpStatus(null);
        setErrorMessage(null);
        setReportError(null);
        setImportStatus(t("import.loaded_result"));
        showToast("success", t("import.loaded_result"));
        return;
      }

      const errMsg = t("error.unrecognized_format");
      setImportStatus("error: " + errMsg);
      showToast("error", errMsg);
    } catch (err) {
      const raw = err instanceof Error ? err.message : t("error.import_failed");
      const msg = raw === "Aborted by user" ? t("error.import_cancelled") : raw;
      setImportStatus("error: " + msg);
      showToast("error", msg);
    }
  };

  const handleImportFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    await handleImportedFile(file, "file");
  };
  showToastRef.current = showToast;
  handleImportedFileRef.current = handleImportedFile;

  const handleBundleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    setImportStatus(null);
    if (!file) return;
    try {
      const text = await readFileAsText(file);
      const parsed = safeParseJson(text);
      if (!parsed.ok) {
        setImportStatus("error: " + parsed.error);
        return;
      }
      const bundle = validateSnapshotBundle(parsed.value);
      if (!bundle.ok) {
        setImportStatus("error: " + bundle.error);
        return;
      }
      const { snapshots: imported, rejectedCount } = bundle.value;
      let list: Snapshot[];
      if (bundleImportMode === "replace") {
        list = imported.slice(-SNAPSHOT_MAX_COUNT);
      } else {
        const existing = getSnapshots();
        const byId = new Map<string, Snapshot>();
        for (const s of [...existing, ...imported]) {
          const existingItem = byId.get(s.id);
          if (!existingItem || (bundleDedupe && new Date(s.created_at) > new Date(existingItem.created_at)))
            byId.set(s.id, s);
        }
        list = [...byId.values()].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, SNAPSHOT_MAX_COUNT);
      }
      saveSnapshotsList(list);
      setSnapshots(list);
      const statusMsg = rejectedCount > 0
        ? t("import.imported_prefix") + " " + list.length + " " + t("import.snapshots") + " (" + rejectedCount + " " + t("import.rejected") + ")."
        : t("import.imported_prefix") + " " + list.length + " " + t("import.snapshots") + ".";
      setImportStatus(bundle.warn ? statusMsg + " " + t("import.bundle_mismatch") : statusMsg);
    } catch (err) {
      setImportStatus("error: " + (err instanceof Error ? err.message : t("error.import_failed")));
    }
  };

  const handleDownloadSnapshotsBundle = () => {
    const bundle = {
      bundle_version: "1",
      exported_at: new Date().toISOString(),
      app: "ai-mentor",
      snapshots: getSnapshots(),
    };
    const now = new Date();
    const ymd = now.toISOString().slice(0, 10).replace(/-/g, "");
    const hms = now.toTimeString().slice(0, 8).replace(/:/g, "");
    downloadJson(`ai-mentor_snapshots_bundle_${ymd}_${hms}.json`, bundle);
  };

  const clearImportMessage = () => setImportStatus(null);

  useEffect(() => {
    const justFinished = prevLoadingRef.current === true && loading === false;
    prevLoadingRef.current = loading;
    if (!justFinished || !result) return;
    const decisions = safeArray(result?.analyzer?.decisions);
    const timeout = setTimeout(() => {
      if (decisions.length > 0 && firstDecisionRowRef.current) {
        (firstDecisionRowRef.current as HTMLElement).focus();
      } else if (decisionsHeadingRef.current) {
        decisionsHeadingRef.current.focus();
      }
    }, 0);
    return () => clearTimeout(timeout);
  }, [result, loading]);

  useEffect(() => {
    if (!selectedDecision) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedDecision(null);
        setSelectedMarket(null);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [selectedDecision]);

  // Global drag & drop for JSON import (PATCH 9.3.1)
  useEffect(() => {
    const hasFiles = (e: DragEvent) => e.dataTransfer?.types?.includes("Files") ?? false;
    const onDragEnter = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      if (dragLeaveTimeoutRef.current) {
        clearTimeout(dragLeaveTimeoutRef.current);
        dragLeaveTimeoutRef.current = null;
      }
      setIsDragOver(true);
    };
    const onDragOver = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
    };
    const onDragLeave = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      dragLeaveTimeoutRef.current = setTimeout(() => setIsDragOver(false), 150);
    };
    const onDrop = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      setIsDragOver(false);
      if (dragLeaveTimeoutRef.current) {
        clearTimeout(dragLeaveTimeoutRef.current);
        dragLeaveTimeoutRef.current = null;
      }
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      if (!/\.json$/i.test(file.name)) {
        showToastRef.current("warn", t("only_json_supported"));
        return;
      }
      handleImportedFileRef.current(file, "drop");
    };
    window.addEventListener("dragenter", onDragEnter);
    window.addEventListener("dragover", onDragOver);
    window.addEventListener("dragleave", onDragLeave);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onDragEnter);
      window.removeEventListener("dragover", onDragOver);
      window.removeEventListener("dragleave", onDragLeave);
      window.removeEventListener("drop", onDrop);
      if (dragLeaveTimeoutRef.current) clearTimeout(dragLeaveTimeoutRef.current);
    };
  }, []);

  // Persist inputs and filters with debounce (BLOCK 8.9)
  useEffect(() => {
    const t = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEYS.homeTeam, home);
        localStorage.setItem(STORAGE_KEYS.awayTeam, away);
        localStorage.setItem(
          STORAGE_KEYS.filters,
          JSON.stringify({ marketFilter, kindFilter, flagFilter, searchText, sortBy })
        );
      } catch {
        /* ignore */
      }
    }, PERSIST_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [home, away, marketFilter, kindFilter, flagFilter, searchText, sortBy]);

  // Persist last successful result (cap size) (BLOCK 8.9)
  useEffect(() => {
    if (!result) return;
    try {
      const s = JSON.stringify(result);
      if (s.length <= LAST_RESULT_MAX_BYTES) localStorage.setItem(STORAGE_KEYS.lastResult, s);
    } catch {
      /* ignore */
    }
  }, [result]);

  const runAnalyze = async () => {
    if (loading || !backendReady) return;
    setLoading(true);
    setErrorMessage(null);
    setErrorKind(null);
    setHttpStatus(null);
    setLastErrorDebug(null);
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();
    const signal = abortRef.current.signal;
    const base = apiBase || (await getBackendBaseUrl());
    if (!base) return;
    const endpoint = `${base}/api/v1/analyze`;
    const timestamp = new Date().toISOString();
    const payload = {
      home_text: home,
      away_text: away,
      window_hours: 8760,
      mode: "PREGAME" as const,
      markets: ["1X2", "OU25", "GGNG"],
      policy: {
        min_sep_1x2: 0.1,
        min_sep_ou: 0.08,
        min_sep_gg: 0.08,
        min_confidence: 0.62,
      },
    };

    const doFetch = (): Promise<Response> =>
      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(payload),
        signal,
      });

    const isNetworkErr = (e: unknown): boolean => {
      const msg = e instanceof Error ? e.message : String(e);
      return msg === "Failed to fetch" || /econnrefused|network/i.test(String(msg));
    };

    try {
      let res: Response | null = null;
      let lastErr: unknown = null;

      for (let retry = 0; retry < 4; retry++) {
        try {
          res = await doFetch();
          lastErr = null;
          break;
        } catch (e: unknown) {
          if ((e as { name?: string })?.name === "AbortError") return;
          lastErr = e;
          if (!isNetworkErr(e) || retry >= 3) throw e;
          await new Promise((r) => setTimeout(r, 1000));
        }
      }

      if (lastErr) throw lastErr;
      if (!res) throw new Error("No response");

      const responseText = await res.text();
      const responsePreview = responseText.slice(0, 2048);
      setHttpStatus(res.status);

      let data: AnalyzeResponse = {};
      try {
        data = responseText ? (JSON.parse(responseText) as AnalyzeResponse) : {};
      } catch {
        data = {};
      }

      if (!res.ok) {
        setResult(null);
        setErrorKind("HTTP_ERROR");
        const msg =
          typeof (data as { detail?: string }).detail === "string"
            ? (data as { detail: string }).detail
            : typeof (data as { message?: string }).message === "string"
              ? (data as { message: string }).message
              : null;
        setErrorMessage(msg ? `HTTP ${res.status}: ${msg}` : `HTTP ${res.status}: ${JSON.stringify(data)}`);
        setLastErrorDebug({ httpStatus: res.status, endpoint, timestamp, home, away, responsePreview });
        return;
      }

      setErrorKind(null);
      setResult(data);
    } catch (e: unknown) {
      if ((e as { name?: string })?.name === "AbortError") return;
      setResult(null);
      setErrorKind(null);
      setHttpStatus(null);
      const msg = e instanceof Error ? e.message : String(e);
      const isNetwork =
        msg === "Failed to fetch" ||
        String(msg).toLowerCase().includes("econnrefused") ||
        String(msg).toLowerCase().includes("network");
      setErrorKind(isNetwork ? "NETWORK_ERROR" : "HTTP_ERROR");
      setErrorMessage(
        isNetwork
          ? t("error.network")
          : msg
      );
      setLastErrorDebug({
        httpStatus: null,
        endpoint,
        timestamp,
        home,
        away,
        responsePreview: msg.slice(0, 2048),
      });
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  const clearResults = () => {
    setResult(null);
    setErrorMessage(null);
    setErrorKind(null);
    setHttpStatus(null);
    setLastErrorDebug(null);
    setSelectedDecision(null);
    setSelectedMarket(null);
  };

  const resetAll = () => {
    setHome("PAOK");
    setAway("AEK");
    setMarketFilter("ALL");
    setKindFilter("ALL");
    setFlagFilter("ALL");
    setSearchText("");
    setSortBy("confidence_desc");
    setResult(null);
    setErrorMessage(null);
    setErrorKind(null);
    setHttpStatus(null);
    setLastErrorDebug(null);
    setSelectedDecision(null);
    setSelectedMarket(null);
    try {
      localStorage.removeItem(STORAGE_KEYS.lastResult);
    } catch {
      /* ignore */
    }
  };

  const copyDebugInfo = () => {
    if (!lastErrorDebug) return;
    const block = [
      `AI Mentor debug`,
      `Timestamp: ${lastErrorDebug.timestamp}`,
      `Endpoint: ${lastErrorDebug.endpoint}`,
      `HTTP status: ${lastErrorDebug.httpStatus ?? "N/A"}`,
      `Home: ${lastErrorDebug.home} | Away: ${lastErrorDebug.away}`,
      `--- Response (first 2KB) ---`,
      lastErrorDebug.responsePreview,
    ].join("\n");
    navigator.clipboard?.writeText(block).catch(() => {});
  };

  const decisions = useMemo(() => safeArray(result?.analyzer?.decisions), [result]);
  const resolverNotes = safeArray(result?.resolver?.notes).concat(safeArray(result?.notes));
  const outcomeBanner = getOutcomeBanner(result);
  const candidates = safeArray(result?.resolver?.candidates);

  const allMarkets = useMemo(
    () => [...buildMarketGroups(decisions).keys()].sort((a, b) => a.localeCompare(b)),
    [decisions]
  );
  const allFlags = useMemo(
    () => [...new Set(decisions.flatMap((d) => flattenFlags(d)))].sort((a, b) => a.localeCompare(b)),
    [decisions]
  );

  const filteredDecisions = useMemo(() => {
    let list: Decision[] = decisions;
    if (marketFilter !== "ALL")
      list = list.filter((d) => normalizeMarketName(d.market) === marketFilter);
    if (kindFilter !== "ALL")
      list = list.filter((d) => getDecisionKind(d.decision) === kindFilter);
    if (flagFilter !== "ALL")
      list = list.filter((d) => flattenFlags(d).includes(flagFilter));
    if (searchText.trim()) {
      const q = searchText.trim().toLowerCase();
      list = list.filter((d) => {
        const market = (d.market ?? "").toLowerCase();
        const dec = (d.decision ?? "").toLowerCase();
        const reasons = safeArray<string>(d.reasons).join(" ").toLowerCase();
        return market.includes(q) || dec.includes(q) || reasons.includes(q);
      });
    }
    if (sortBy === "confidence_desc")
      list = [...list].sort((a, b) => (b.confidence ?? -1) - (a.confidence ?? -1));
    else if (sortBy === "market_az")
      list = [...list].sort(
        (a, b) =>
          normalizeMarketName(a.market).localeCompare(normalizeMarketName(b.market)) ||
          (a.decision ?? "").localeCompare(b.decision ?? "")
      );
    else if (sortBy === "decision_az")
      list = [...list].sort(
        (a, b) =>
          (a.decision ?? "").localeCompare(b.decision ?? "") ||
          normalizeMarketName(a.market).localeCompare(normalizeMarketName(b.market))
      );
    return list;
  }, [decisions, marketFilter, kindFilter, flagFilter, searchText, sortBy]);

  const filteredGroups = useMemo(() => buildMarketGroups(filteredDecisions), [filteredDecisions]);
  const filteredMarketKeys = useMemo(
    () => [...filteredGroups.keys()].sort((a, b) => a.localeCompare(b)),
    [filteredGroups]
  );
  const kindCounts = useMemo(() => {
    const counts = { PLAY: 0, NO_BET: 0, NO_PREDICTION: 0, UNKNOWN: 0 };
    filteredDecisions.forEach((d) => {
      counts[getDecisionKind(d.decision)] += 1;
    });
    return counts;
  }, [filteredDecisions]);

  // BLOCK 8.8: UI state machine (IDLE | ANALYZING | RESULT | ERROR)
  const uiStateResult = useMemo(
    () =>
      getAnalyzeUIState(
        loading,
        errorMessage,
        httpStatus,
        result as Record<string, unknown> | null,
        errorKind ?? undefined
      ),
    [loading, errorMessage, httpStatus, result, errorKind]
  );
  const { state: analyzeState, errorKind: resolvedErrorKind, emptyKind } = uiStateResult;
  const resultBlockRef = useRef<HTMLDivElement>(null);
  const prevAnalyzeStateRef = useRef(analyzeState);

  // Logging hygiene: log only state transitions (DEV only).
  useEffect(() => {
    if (import.meta.env.DEV && prevAnalyzeStateRef.current !== analyzeState) {
      // eslint-disable-next-line no-console
      console.log("[AI Mentor] state:", prevAnalyzeStateRef.current, "->", analyzeState);
    }
  }, [analyzeState]);

  // BLOCK 8.9: Scroll result block to top when entering RESULT
  useEffect(() => {
    if (analyzeState === "RESULT" && prevAnalyzeStateRef.current !== "RESULT" && result) {
      resultBlockRef.current?.scrollIntoView({ behavior: "instant", block: "start" });
    }
    prevAnalyzeStateRef.current = analyzeState;
  }, [analyzeState, result]);

  // BLOCK 8.9: Enter = Analyze (from team inputs), Esc = clear results
  const runAnalyzeRef = useRef(runAnalyze);
  const clearResultsRef = useRef(clearResults);
  runAnalyzeRef.current = runAnalyze;
  clearResultsRef.current = clearResults;
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        const target = e.target as HTMLElement;
        const isTeamInput =
          target?.id === "ai-mentor-home" || target?.id === "ai-mentor-away";
        if (isTeamInput) {
          e.preventDefault();
          runAnalyzeRef.current();
        }
      }
      if (e.key === "Escape") {
        if (analyzeState === "RESULT" || analyzeState === "ERROR") {
          clearResultsRef.current();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [analyzeState]);

  // BLOCK 8.9: Remember window size (Tauri only)
  useEffect(() => {
    if (!isTauri()) return;
    const STORAGE_KEY = "ai-mentor.windowSize";
    let resizeTimeout: ReturnType<typeof setTimeout> | null = null;
    const saveSize = () => {
      if (resizeTimeout) clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        try {
          localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ width: window.innerWidth, height: window.innerHeight })
          );
        } catch {
          /* ignore */
        }
        resizeTimeout = null;
      }, 300);
    };
    const restoreSize = async () => {
      try {
        const restoreOn = localStorage.getItem(STORAGE_KEYS.restoreWindowDefaults);
        if (restoreOn === "false") return;
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const { width, height } = JSON.parse(raw) as { width?: number; height?: number };
        if (typeof width !== "number" || typeof height !== "number") return;
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        const w = getCurrentWindow();
        await w.setSize({ type: "Logical", width, height });
      } catch {
        /* ignore */
      }
    };
    restoreSize();
    window.addEventListener("resize", saveSize);
    return () => {
      window.removeEventListener("resize", saveSize);
      if (resizeTimeout) clearTimeout(resizeTimeout);
    };
  }, []);

  return (
    <div className="ai-root">
      {isDragOver && (
        <div className="ai-dropOverlay" role="presentation">
          <div className="ai-dropOverlay__box">
            <div className="ai-dropOverlay__title">{t("drop.title")}</div>
            <div className="ai-dropOverlay__sub">{t("drop.sub")}</div>
          </div>
        </div>
      )}
      {toast && (
        <div className={`ai-toast ai-toast--${toast.kind}`} role="status" aria-live="polite">
          <div className="ai-toast__msg">{toast.message}</div>
          <button type="button" className="ai-btn ai-btn--ghost ai-toast__close" onClick={() => { setToast(null); if (toastTimeoutRef.current) { clearTimeout(toastTimeoutRef.current); toastTimeoutRef.current = null; } }} aria-label={t("toast.dismiss")}>×</button>
        </div>
      )}
      <AppShell
        activeKey={viewToSidebarKey(view)}
        onSidebarSelect={(key) => {
          if (key === "home") setView("HOME");
          if (key === "predictions") setView("NEW_PREDICTION");
          if (key === "statistics") setView("SUMMARY");
          if (key === "history") setView("HISTORY");
          if (key === "settings") setView("SETTINGS");
        }}
        pageTitle={viewToPageTitle(view)}
        statusLabel={
          isTauri() && backendStatus === "NOT_READY"
            ? t("backend.status_not_ready")
            : backendReady
              ? t("topbar.status_ready")
              : t("topbar.status_starting")
        }
      >
        {view === "HOME" && <HomeScreen onNavigate={setView} />}
        {view === "RESULT" && !result && (
          <div className="ai-container">
            <div className="ai-card ai-card--warning" role="status">
              <p className="ai-muted" style={{ margin: 0 }}>{t("empty.no_result_message")}</p>
              <button type="button" className="ai-btn ai-btn--primary" style={{ marginTop: 12 }} onClick={() => setView("NEW_PREDICTION")}>
                {t("empty.no_result_btn")}
              </button>
            </div>
          </div>
        )}
        {view === "RESULT" && result && (
          <div className="ai-container">
            <div ref={resultBlockRef} className="ai-result-block" role="region" aria-label="Analysis result">
              {emptyKind != null && <EmptyResultState emptyKind={emptyKind} />}
              <div className={emptyKind != null ? "ai-result-view-separator" : ""}>
                <ResultView vm={mapApiToResultVM(result, { homeTeam: home, awayTeam: away })} onExport={handleExportResultSummary} />
              </div>
              <div className="ai-section ai-no-print">
                <div className="ai-card">
                  <details>
                    <summary className="ai-summary">{t("raw_json_show")}</summary>
                    <pre className="ai-pre ai-mono" style={{ marginTop: 8 }}>{safeStringify(result)}</pre>
                  </details>
                </div>
              </div>
              <div className="ai-section">
                <div className="ai-card">
                  <div className="ai-cardHeader"><div className="ai-cardTitle">{t("section.export")}</div></div>
                  <div className="ai-row ai-row--gap2" style={{ flexWrap: "wrap", marginBottom: 8 }}>
                    <button type="button" className="ai-btn ai-btn--ghost" onClick={handleCopySummary} aria-label={t("btn.copy_summary")}>{copiedKey === "summary" ? t("btn.copied") : t("btn.copy_summary")}</button>
                    <button type="button" className="ai-btn ai-btn--ghost" onClick={handleDownloadResultJson} aria-label={t("btn.download_result_json")}>{t("btn.download_result_json")}</button>
                    <button type="button" className="ai-btn ai-btn--ghost" onClick={handleExportAnalysisPdf} aria-label={t("btn.export_analysis_pdf")}>{t("btn.export_analysis_pdf")}</button>
                    <button type="button" className="ai-btn ai-btn--accent" onClick={handleSaveSnapshot} aria-label={t("btn.save_snapshot")}>{t("btn.save_snapshot")}</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        {view === "SUMMARY" && (
          <div className="ai-container">
            <div className="ai-card">
              <h2 className="ai-cardTitle" style={{ marginBottom: 8 }}>{t("summary.placeholder_title")}</h2>
              <p className="ai-muted" style={{ margin: 0 }}>{t("summary.placeholder_desc")}</p>
            </div>
          </div>
        )}
        {view === "HISTORY" && (
          <div className="ai-container">
            <div className="ai-card">
              <div className="ai-cardHeader"><div className="ai-cardTitle">{t("history.title")}</div></div>
              {snapshotError && (
                <p className="ai-muted" style={{ margin: "0 0 8px 0", color: "var(--error)" }} role="alert">{snapshotError}</p>
              )}
              <details open>
                <summary className="ai-summary">{t("section.snapshots")} ({snapshots.length})</summary>
                <div style={{ marginTop: 8 }}>
                  {snapshots.length === 0 ? (
                    <p className="ai-muted" style={{ margin: "8px 0" }}>{t("empty.snapshots_none")}</p>
                  ) : (
                    <>
                      {snapshots.slice().reverse().map((snap) => (
                        <div key={snap.id} className="ai-snapshotRow">
                          <span className="ai-muted" style={{ fontSize: 11 }}>
                            {new Date(snap.created_at).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })}
                            {" · "}{snap.homeTeam} vs {snap.awayTeam}
                            {" · "}{labelResolverStatus(snap.resolver?.status ?? snap.status ?? "")}
                            {" · "}{(snap.size_bytes / 1024).toFixed(1)} KB
                          </span>
                          <span className="ai-row ai-row--gap2" style={{ marginTop: 4 }}>
                            <button type="button" className="ai-btn ai-btn--ghost" onClick={() => { loadSnapshot(snap); setView("NEW_PREDICTION"); }}>{t("btn.load")}</button>
                            <button type="button" className="ai-btn ai-btn--ghost" onClick={() => downloadJson(`ai-mentor_snapshot_${snap.id}.json`, snap.result)}>{t("btn.download")}</button>
                            <button type="button" className="ai-btn ai-btn--ghost" onClick={() => deleteSnapshot(snap.id)}>{t("btn.delete")}</button>
                          </span>
                        </div>
                      ))}
                      <button type="button" className="ai-btn ai-btn--ghost" style={{ marginTop: 8 }} onClick={deleteAllSnapshots}>{t("btn.delete_all")}</button>
                    </>
                  )}
                </div>
              </details>
            </div>
          </div>
        )}
        {view === "SETTINGS" && (
          <div className="ai-container">
            <AppSettingsPanel
              analyzerVersionFromResult={result != null ? mapApiToResultVM(result, { homeTeam: home, awayTeam: away }).analyzer.logicVersion ?? null : null}
              onClose={() => setView("HOME")}
            />
          </div>
        )}
        {view === "NEW_PREDICTION" && (
      <div className="ai-container">
        <h1 className="ai-cardHeader" style={{ marginBottom: 8 }}>{t("analysis.title")}</h1>
        {isTauri() && backendStatus === "NOT_READY" && (
          <div className="ai-card ai-card--error" style={{ marginBottom: 12 }} role="alert">
            <p style={{ margin: 0 }}>{t("backend.not_ready_message")}</p>
            <div className="ai-row ai-row--gap2" style={{ marginTop: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                className="ai-btn ai-btn--primary"
                onClick={() => {
                  import("@tauri-apps/api/core").then(({ invoke }) => invoke("retry_backend_start").catch(() => {}));
                }}
              >
                {t("backend.retry")}
              </button>
              <button
                type="button"
                className="ai-btn ai-btn--ghost"
                onClick={() => {
                  import("@tauri-apps/api/core").then(({ invoke }) => invoke("open_logs_folder").catch(() => {}));
                }}
              >
                {t("backend.open_logs")}
              </button>
            </div>
          </div>
        )}
        {!backendReady && backendStatus !== "NOT_READY" && (
          <div className="ai-card ai-card--warning" style={{ marginBottom: 12 }} role="status">
            <p style={{ margin: 0 }}>{t("analysis.backend_starting")}</p>
          </div>
        )}
        <p className="ai-muted" style={{ margin: "0 0 12px 0", fontSize: 12 }}>{t("footer.build")}: {buildInfoFormatted}</p>

        <div className="ai-row ai-row--gap2" style={{ marginBottom: 12 }}>
          <label htmlFor="ai-mentor-home" className="ai-label">{t("label.home")}</label>
          <input
            id="ai-mentor-home"
            className="ai-input"
            value={home}
            onChange={(e) => setHome(e.target.value)}
            placeholder={t("analysis.home_team_placeholder")}
            disabled={loading}
            aria-label={t("label.home")}
          />
          <button
            type="button"
            className="ai-btn ai-btn--ghost"
            onClick={() => { const h = home; setHome(away); setAway(h); }}
            disabled={loading}
            aria-label={t("btn.swap")}
          >
            {t("btn.swap")}
          </button>
          <label htmlFor="ai-mentor-away" className="ai-label">{t("label.away")}</label>
          <input
            id="ai-mentor-away"
            className="ai-input"
            value={away}
            onChange={(e) => setAway(e.target.value)}
            placeholder={t("analysis.away_placeholder")}
            disabled={loading}
            aria-label={t("label.away")}
          />
        </div>

        <div className="ai-row ai-row--gap2" style={{ marginBottom: 16 }}>
          <button
            className="ai-btn ai-btn--primary"
            onClick={runAnalyze}
            disabled={loading || !backendReady}
            aria-busy={loading}
            aria-label={loading ? t("btn.analyzing") : t("btn.analyze")}
          >
            {loading ? t("btn.analyzing") : t("btn.analyze")}
          </button>
          {loading && (
            <button
              type="button"
              className="ai-btn ai-btn--ghost"
              onClick={() => abortRef.current?.abort()}
              aria-label={t("btn.cancel")}
            >
              {t("btn.cancel")}
            </button>
          )}
          <button
            type="button"
            className="ai-btn ai-btn--ghost"
            onClick={clearResults}
            aria-label={t("btn.clear_results")}
          >
            {t("btn.clear_results")}
          </button>
          <button type="button" className="ai-btn ai-btn--ghost" onClick={resetAll}>
            {t("btn.reset_all")}
          </button>
          <button
            type="button"
            className="ai-btn ai-btn--ghost"
            onClick={() => setShowSettings((s) => !s)}
            aria-expanded={showSettings}
            aria-label={t("btn.settings")}
          >
            {t("btn.settings")}
          </button>
        </div>
        {/* BLOCK 3: Settings panel (single view, no routing) */}
        {showSettings && (
          <AppSettingsPanel
            analyzerVersionFromResult={
              result != null
                ? mapApiToResultVM(result, { homeTeam: home, awayTeam: away }).analyzer.logicVersion ?? null
                : null
            }
            onClose={() => setShowSettings(false)}
          />
        )}
        {/* BLOCK 8.8: IDLE */}
        {analyzeState === "IDLE" && <IdleState />}

        {/* BLOCK 8.8: ANALYZING */}
        {analyzeState === "ANALYZING" && <LoadingState />}

        {/* BLOCK 8.8: ERROR — deterministic messages by errorKind */}
        {analyzeState === "ERROR" && resolvedErrorKind && (
          <ErrorState
            errorKind={resolvedErrorKind}
            httpStatus={httpStatus}
            detail={resolvedErrorKind === "HTTP_ERROR" ? errorMessage ?? undefined : undefined}
            onCopyDebug={copyDebugInfo}
            hasDebug={!!lastErrorDebug}
          />
        )}

        {/* BLOCK 8.8: RESULT — ResultView; empty state banner above when applicable */}
      {analyzeState === "RESULT" && result && (
        <div ref={resultBlockRef} className="ai-result-block" role="region" aria-label="Analysis result">
          {emptyKind != null && <EmptyResultState emptyKind={emptyKind} />}
          {/* BLOCK 8.7: Canonical Result View (view-model, no raw JSON dump) */}
          <div className={emptyKind != null ? "ai-result-view-separator" : ""}>
            <ResultView
              vm={mapApiToResultVM(result, { homeTeam: home, awayTeam: away })}
              onExport={handleExportResultSummary}
            />
          </div>

          {/* Show raw JSON (debug) — collapsed by default; hidden when printing (BLOCK 2) */}
          <div className="ai-section ai-no-print">
            <div className="ai-card">
              <details>
                <summary className="ai-summary">{t("raw_json_show")}</summary>
                <pre className="ai-pre ai-mono" style={{ marginTop: 8 }}>{safeStringify(result)}</pre>
              </details>
            </div>
          </div>

          {/* Export card (BLOCK 9.1 + 9.2) */}
          <div className="ai-section">
            <div className="ai-card">
              <div className="ai-cardHeader">
                <div className="ai-cardTitle">{t("section.export")}</div>
              </div>
              <div className="ai-row ai-row--gap2" style={{ flexWrap: "wrap", marginBottom: 8 }}>
                <button
                  type="button"
                  className="ai-btn ai-btn--ghost"
                  onClick={handleCopySummary}
                  aria-label={t("btn.copy_summary")}
                >
                  {copiedKey === "summary" ? t("btn.copied") : t("btn.copy_summary")}
                </button>
                <button
                  type="button"
                  className="ai-btn ai-btn--ghost"
                  onClick={handleDownloadResultJson}
                  aria-label={t("btn.download_result_json")}
                >
                  {t("btn.download_result_json")}
                </button>
                <button
                  type="button"
                  className="ai-btn ai-btn--ghost"
                  onClick={handleExportAnalysisJson}
                  aria-label={t("btn.export_analysis_json")}
                >
                  {t("btn.export_analysis_json")}
                </button>
                <button
                  type="button"
                  className="ai-btn ai-btn--ghost"
                  onClick={handleExportAnalysisPdf}
                  aria-label={t("btn.export_analysis_pdf")}
                >
                  {t("btn.export_analysis_pdf")}
                </button>
                <button
                  type="button"
                  className="ai-btn ai-btn--ghost"
                  onClick={handleDownloadSelectedDecisionJson}
                  disabled={selectedDecision == null}
                  aria-label={t("btn.download_decision_json")}
                >
                  {t("btn.download_decision_json")}
                </button>
                <button
                  type="button"
                  className="ai-btn ai-btn--accent"
                  onClick={handleSaveSnapshot}
                  aria-label={t("btn.save_snapshot")}
                >
                  {t("btn.save_snapshot")}
                </button>
              </div>
              {exportAnalysisError && (
                <p className="ai-muted" style={{ margin: "8px 0 0 0", color: "var(--error)" }} role="alert">
                  {t("export_failed")}: {exportAnalysisError}
                </p>
              )}
              {exportPdfError && (
                <p className="ai-muted" style={{ margin: "8px 0 0 0", color: "var(--error)" }} role="alert">
                  {t("pdf_export_failed")}: {exportPdfError}
                </p>
              )}

              {/* CSV (BLOCK 9.2) */}
              <div className="ai-row ai-row--gap2" style={{ flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
                <span className="ai-label">{t("label.csv_delimiter")}:</span>
                <select
                  className="ai-select"
                  value={csvDelimiter}
                  onChange={(e) => setCsvDelimiter(e.target.value as ";" | ",")}
                  aria-label={t("label.csv_delimiter")}
                >
                  <option value=";">{t("csv_semicolon")}</option>
                  <option value=",">{t("csv_comma")}</option>
                </select>
                <button type="button" className="ai-btn ai-btn--ghost" onClick={() => handleDownloadCsv("filtered")}>
                  {t("btn.download_csv_filtered")}
                </button>
                <button type="button" className="ai-btn ai-btn--ghost" onClick={() => handleDownloadCsv("all")}>
                  {t("btn.download_csv_all")}
                </button>
                <button
                  type="button"
                  className="ai-btn ai-btn--ghost"
                  onClick={() => handleDownloadCsv("selectedMarket")}
                  disabled={selectedMarket == null}
                >
                  {t("btn.download_csv_market")}
                </button>
              </div>

              {/* Print report (BLOCK 9.2) */}
              <div className="ai-row ai-row--gap2" style={{ flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
                <span className="ai-label">{t("label.report_scope")}:</span>
                <select
                  className="ai-select"
                  value={reportScope}
                  onChange={(e) => setReportScope(e.target.value as "FILTERED" | "ALL")}
                  aria-label={t("label.report_scope")}
                >
                  <option value="FILTERED">{t("report.scope_filtered")}</option>
                  <option value="ALL">{t("report.scope_all")}</option>
                </select>
                <label className="ai-row" style={{ alignItems: "center", gap: 6 }}>
                  <input
                    type="checkbox"
                    checked={reportIncludeAppendices}
                    onChange={(e) => setReportIncludeAppendices(e.target.checked)}
                    aria-label={t("label.include_appendices")}
                  />
                  <span className="ai-muted" style={{ fontSize: 12 }}>{t("label.include_appendices")}</span>
                </label>
                <button type="button" className="ai-btn ai-btn--accent" onClick={handlePrintReport}>
                  {t("btn.print_report")}
                </button>
              </div>
              {reportError && (
                <p className="ai-muted" style={{ margin: "0 0 8px 0", color: "var(--error)" }} role="alert">
                  {reportError}
                </p>
              )}

              {/* Import / Bundle (BLOCK 9.3) */}
              <div className="ai-importBox">
                <div className="ai-cardTitle" style={{ marginBottom: 6 }}>{t("section.import_bundle")}</div>
                <div className="ai-row ai-row--gap2" style={{ flexWrap: "wrap", marginBottom: 6 }}>
                  <span className="ai-label">{t("label.import_json")}:</span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json,application/json"
                    onChange={handleImportFileChange}
                    style={{ display: "none" }}
                    aria-label={t("btn.import_file")}
                  />
                  <button type="button" className="ai-btn ai-btn--ghost" onClick={() => fileInputRef.current?.click()}>
                    {t("btn.import_file")}
                  </button>
                  <button type="button" className="ai-btn ai-btn--ghost" onClick={clearImportMessage}>
                    {t("btn.clear_import_msg")}
                  </button>
                </div>
                {importStatus && (
                  <p
                    className="ai-muted"
                    style={{
                      margin: "0 0 8px 0",
                      fontSize: 12,
                      color: importStatus.startsWith("error:") ? "var(--error)" : importStatus.startsWith("Imported") || importStatus.startsWith(t("import.imported_prefix")) ? "var(--success)" : undefined,
                    }}
                    role="alert"
                  >
                    {importStatus}
                  </p>
                )}
                <div className="ai-row ai-row--gap2" style={{ flexWrap: "wrap", alignItems: "center", marginBottom: 6 }}>
                  <button type="button" className="ai-btn ai-btn--ghost" onClick={handleDownloadSnapshotsBundle}>
                    {t("btn.download_bundle")}
                  </button>
                  <input
                    ref={bundleFileInputRef}
                    type="file"
                    accept=".json,application/json"
                    onChange={handleBundleFileChange}
                    style={{ display: "none" }}
                    aria-label={t("btn.import_bundle")}
                  />
                  <button type="button" className="ai-btn ai-btn--ghost" onClick={() => bundleFileInputRef.current?.click()}>
                    {t("btn.import_bundle")}
                  </button>
                  <span className="ai-label">{t("label.bundle_import")}:</span>
                  <select
                    className="ai-select"
                    value={bundleImportMode}
                    onChange={(e) => setBundleImportMode(e.target.value as "merge" | "replace")}
                    aria-label={t("label.bundle_import")}
                  >
                    <option value="merge">{t("import.merge")}</option>
                    <option value="replace">{t("import.replace")}</option>
                  </select>
                  <label className="ai-row" style={{ alignItems: "center", gap: 6 }}>
                    <input
                      type="checkbox"
                      checked={bundleDedupe}
                      onChange={(e) => setBundleDedupe(e.target.checked)}
                      aria-label={t("label.dedupe")}
                    />
                    <span className="ai-muted" style={{ fontSize: 12 }}>{t("label.dedupe")}</span>
                  </label>
                </div>
              </div>

              {snapshotError && (
                <p className="ai-muted" style={{ margin: "0 0 8px 0", color: "var(--error)" }} role="alert">
                  {snapshotError}
                </p>
              )}
              <details>
                <summary className="ai-summary">{t("section.snapshots")} ({snapshots.length})</summary>
                <div style={{ marginTop: 8 }}>
                  {snapshots.length === 0 ? (
                    <p className="ai-muted" style={{ margin: "8px 0" }}>{t("empty.snapshots_none")}</p>
                  ) : (
                    <>
                      {snapshots.slice().reverse().map((snap) => (
                        <div key={snap.id} className="ai-snapshotRow">
                          <span className="ai-muted" style={{ fontSize: 11 }}>
                            {new Date(snap.created_at).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })}
                            {" · "}
                            {snap.homeTeam} vs {snap.awayTeam}
                            {" · "}
                            {labelResolverStatus(snap.resolver?.status ?? snap.status ?? "")}
                            {" · "}
                            {(snap.size_bytes / 1024).toFixed(1)} KB
                          </span>
                          <span className="ai-row ai-row--gap2" style={{ marginTop: 4 }}>
                            <button type="button" className="ai-btn ai-btn--ghost" onClick={() => loadSnapshot(snap)}>{t("btn.load")}</button>
                            <button type="button" className="ai-btn ai-btn--ghost" onClick={() => downloadJson(`ai-mentor_snapshot_${snap.id}.json`, snap.result)}>{t("btn.download")}</button>
                            <button type="button" className="ai-btn ai-btn--ghost" onClick={() => deleteSnapshot(snap.id)}>{t("btn.delete")}</button>
                          </span>
                        </div>
                      ))}
                      <button
                        type="button"
                        className="ai-btn ai-btn--ghost"
                        style={{ marginTop: 8 }}
                        onClick={deleteAllSnapshots}
                      >
                        {t("btn.delete_all")}
                      </button>
                    </>
                  )}
                </div>
              </details>
            </div>
          </div>

          {/* 4) Decisions — Market-centric UI (BLOCK 8.8) */}
          <div className="ai-section">
          <div className="ai-card ai-card--full">
            <div
              className="ai-cardHeader"
              ref={decisionsHeadingRef}
              tabIndex={0}
              role="region"
              aria-label={t("section.decisions")}
            >
              <div className="ai-cardTitle">{t("section.decisions")}</div>
            </div>

            {decisions.length === 0 ? (
              <p className="ai-muted" style={{ margin: "8px 0" }}>{t("empty.no_decisions")}</p>
            ) : (
              <>
                {/* Controls */}
                <div style={{ marginBottom: 12 }}>
                  <div className="ai-cardTitle" style={{ marginBottom: 6 }}>{t("section.decisions_controls")}</div>
                  <div className="ai-row ai-row--gap2">
                    <label className="ai-row" style={{ gap: 4 }}>
                      <span className="ai-label">{t("filter.market")}</span>
                      <select
                        className="ai-select"
                        value={marketFilter}
                        onChange={(e) => setMarketFilter(e.target.value)}
                      >
                        <option value="ALL">{t("filter.all")}</option>
                        {allMarkets.map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    </label>
                    <label className="ai-row" style={{ gap: 4 }}>
                      <span className="ai-label">{t("filter.kind")}</span>
                      <select
                        className="ai-select"
                        value={kindFilter}
                        onChange={(e) => setKindFilter(e.target.value)}
                      >
                        <option value="ALL">{t("filter.all")}</option>
                        <option value="PLAY">{labelDecisionKind("PLAY")}</option>
                        <option value="NO_BET">{labelDecisionKind("NO_BET")}</option>
                        <option value="NO_PREDICTION">{labelDecisionKind("NO_PREDICTION")}</option>
                        <option value="UNKNOWN">{labelDecisionKind("UNKNOWN")}</option>
                      </select>
                    </label>
                    <label className="ai-row" style={{ gap: 4 }}>
                      <span className="ai-label">{t("filter.flag")}</span>
                      <select
                        className="ai-select"
                        value={flagFilter}
                        onChange={(e) => setFlagFilter(e.target.value)}
                      >
                        <option value="ALL">{t("filter.all")}</option>
                        {allFlags.map((f) => (
                          <option key={f} value={f}>{f}</option>
                        ))}
                      </select>
                    </label>
                    <label className="ai-row" style={{ gap: 4 }}>
                      <span className="ai-label">{t("filter.sort")}</span>
                      <select
                        className="ai-select"
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                      >
                        <option value="confidence_desc">{t("sort.confidence_desc")}</option>
                        <option value="market_az">{t("sort.market_az")}</option>
                        <option value="decision_az">{t("sort.decision_az")}</option>
                      </select>
                    </label>
                    <input
                      type="text"
                      className="ai-input"
                      placeholder={t("filter.search")}
                      value={searchText}
                      onChange={(e) => setSearchText(e.target.value)}
                    />
                  </div>
                </div>

                {/* Summary */}
                <p className="ai-muted" style={{ margin: "0 0 12px 0" }}>
                  {t("total_decisions")}: {filteredDecisions.length} | {t("markets")}: {filteredMarketKeys.length} | {labelDecisionKind("PLAY")}: {kindCounts.PLAY} | {labelDecisionKind("NO_BET")}: {kindCounts.NO_BET} | {labelDecisionKind("NO_PREDICTION")}: {kindCounts.NO_PREDICTION}
                  {kindCounts.UNKNOWN > 0 ? ` | ${labelDecisionKind("UNKNOWN")}: ${kindCounts.UNKNOWN}` : ""}
                </p>

                {/* Quick filters */}
                <div className="ai-row ai-row--gap2" style={{ marginBottom: 12 }}>
                  <button
                    type="button"
                    className="ai-chip ai-quickFilter"
                    onClick={() => { setKindFilter("PLAY"); setFlagFilter("ALL"); setSearchText(""); }}
                  >
                    {t("quick_filter.play_only")}
                  </button>
                  <button
                    type="button"
                    className="ai-chip ai-quickFilter"
                    onClick={() => { setKindFilter("NO_PREDICTION"); setFlagFilter("ALL"); setSearchText(""); }}
                  >
                    {t("quick_filter.no_prediction_only")}
                  </button>
                  <button
                    type="button"
                    className="ai-chip ai-quickFilter"
                    onClick={() => { setKindFilter("ALL"); setFlagFilter("ALL"); setSearchText(""); }}
                  >
                    {t("quick_filter.clear")}
                  </button>
                </div>

                {/* Two-column: market list + details panel */}
                <div className="ai-grid">
                  <div className="ai-grid__list">
                    {filteredMarketKeys.map((marketKey, marketIdx) => {
                      const groupDecisions = filteredGroups.get(marketKey) ?? [];
                      const subCounts = { PLAY: 0, NO_BET: 0, NO_PREDICTION: 0, UNKNOWN: 0 };
                      groupDecisions.forEach((d) => { subCounts[getDecisionKind(d.decision)] += 1; });
                      const defaultOpen = marketIdx < 2;
                      return (
                        <details key={marketKey} className="ai-marketDetails" open={defaultOpen}>
                          <summary>{marketKey}</summary>
                          <p className="ai-marketDetails__sub">
                            {labelDecisionKind("PLAY")}: {subCounts.PLAY} · {labelDecisionKind("NO_BET")}: {subCounts.NO_BET} · {labelDecisionKind("NO_PREDICTION")}: {subCounts.NO_PREDICTION}
                          </p>
                          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                            {groupDecisions.map((d, idx) => {
                              const isSelected =
                                selectedDecision === d && selectedMarket === marketKey;
                              const isFirst = marketIdx === 0 && idx === 0;
                              return (
                                <div
                                  key={`${d.market ?? "m"}-${d.decision ?? "d"}-${idx}`}
                                  ref={isFirst ? firstDecisionRowRef : undefined}
                                  role="button"
                                  tabIndex={0}
                                  aria-selected={isSelected}
                                  className={`ai-clickRow ai-kbdFocus ${isSelected ? "ai-clickRow--selected" : ""}`}
                                  onClick={() => {
                                    setSelectedDecision(d);
                                    setSelectedMarket(marketKey);
                                  }}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter" || e.key === " ") {
                                      e.preventDefault();
                                      setSelectedDecision(d);
                                      setSelectedMarket(marketKey);
                                    }
                                  }}
                                >
                                  <span style={{ fontWeight: 500 }}>{d.decision ?? "—"}</span>
                                  <span className="ai-row" style={{ gap: 6 }}>
                                    {formatConfidence(d.confidence) && (
                                      <span className="ai-muted">{formatConfidence(d.confidence)}</span>
                                    )}
                                    {flattenFlags(d).map((f) => (
                                      <span key={f} className="ai-chip ai-chip--flag">{f}</span>
                                    ))}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </details>
                      );
                    })}
                  </div>

                  {/* Decision Details panel */}
                  <div className="ai-grid__details">
                    {selectedDecision != null && selectedMarket != null ? (
                      <div className="ai-card" style={{ marginTop: 0 }}>
                        <div className="ai-cardHeader" style={{ marginBottom: 8 }}>
                          <div className="ai-cardTitle">
                            {selectedMarket} — {labelDecisionKind(selectedDecision.decision ?? "")}
                            <button
                              type="button"
                              className="ai-btn ai-btn--ghost ai-copyBtn"
                              onClick={() => handleCopy("market", selectedMarket ?? "")}
                              aria-label={t("btn.copy_summary")}
                            >
                              {copiedKey === "market" ? t("btn.copied") : t("btn.copy")}
                            </button>
                          </div>
                          <button
                            type="button"
                            className="ai-btn ai-btn--ghost"
                            onClick={() => { setSelectedDecision(null); setSelectedMarket(null); }}
                          >
                            {t("btn.close")}
                          </button>
                        </div>
                        <dl style={{ margin: "0 0 12px 0", fontSize: 13 }}>
                          <dt style={{ fontWeight: 600, marginTop: 8 }}>{t("label.decisions")}</dt>
                          <dd style={{ margin: "2px 0 0 0" }}>
                            {selectedDecision.decision ?? "—"}
                            <button
                              type="button"
                              className="ai-btn ai-btn--ghost ai-copyBtn"
                              onClick={() => handleCopy("decision", selectedDecision.decision ?? "")}
                              aria-label={t("btn.copy_summary")}
                            >
                              {copiedKey === "decision" ? t("btn.copied") : t("btn.copy")}
                            </button>
                          </dd>
                          <dt style={{ fontWeight: 600, marginTop: 8 }}>{t("label.confidence")}</dt>
                          <dd style={{ margin: "2px 0 0 0" }}>{formatConfidence(selectedDecision.confidence) || "—"}</dd>
                          <dt style={{ fontWeight: 600, marginTop: 8 }}>{t("label.flags")}</dt>
                          <dd style={{ margin: "2px 0 0 0" }}>
                            {flattenFlags(selectedDecision).length > 0
                              ? flattenFlags(selectedDecision).map((f) => <span key={f} className="ai-chip ai-chip--flag" style={{ marginRight: 4 }}>{f}</span>)
                              : "—"}
                          </dd>
                          <dt style={{ fontWeight: 600, marginTop: 8 }}>{t("label.reasons")}</dt>
                          <dd style={{ margin: "2px 0 0 0" }}>
                            {safeArray<string>(selectedDecision.reasons).length > 0 ? (
                              <ul style={{ margin: 0, paddingLeft: 20 }}>
                                {safeArray<string>(selectedDecision.reasons).map((r, i) => (
                                  <li key={i}>{String(r)}</li>
                                ))}
                              </ul>
                            ) : "—"}
                          </dd>
                        </dl>
                        {(selectedDecision.probabilities && Object.keys(selectedDecision.probabilities).length > 0) && (
                          <details>
                            <summary className="ai-summary">Probabilities</summary>
                            <pre className="ai-pre ai-mono">{safeStringify(selectedDecision.probabilities)}</pre>
                          </details>
                        )}
                        {(selectedDecision.policy && Object.keys(selectedDecision.policy).length > 0) && (
                          <details>
                            <summary className="ai-summary">Policy</summary>
                            <pre className="ai-pre ai-mono">{safeStringify(selectedDecision.policy)}</pre>
                          </details>
                        )}
                        {selectedDecision.evidence_refs != null && (
                          <details>
                            <summary className="ai-summary">Evidence refs</summary>
                            <pre className="ai-pre ai-mono">{safeStringify(selectedDecision.evidence_refs)}</pre>
                          </details>
                        )}
                        <details>
                          <summary className="ai-summary">Decision raw JSON</summary>
                          <pre className="ai-pre ai-mono">{safeStringify(selectedDecision)}</pre>
                        </details>
                      </div>
                    ) : (
                      <p className="ai-muted" style={{ margin: "8px 0" }}>{t("empty.select_decision_prompt")}</p>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
          </div>
        </div>
      )}
      <footer className="ai-footer" style={{ marginTop: 24, paddingTop: 12, borderTop: "1px solid var(--border)", fontSize: 12, color: "var(--muted)" }}>
        {t("footer.app_version")} {appVersion} · {t("footer.build")}: {buildInfoFormatted}
        {" · "}
        <button
          type="button"
          className="ai-btn ai-btn--ghost"
          style={{ padding: "0 4px", fontSize: "inherit", verticalAlign: "baseline" }}
          onClick={() => setShowSettings((s) => !s)}
          aria-expanded={showSettings}
          aria-label={t("btn.settings")}
        >
          {t("btn.settings")}
        </button>
      </footer>
      </div>
        )}
      </AppShell>
    </div>
  );
}

export default App;
