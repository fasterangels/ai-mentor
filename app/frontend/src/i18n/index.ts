/**
 * Tiny i18n layer (no libraries). Default EL, fallback EN.
 */
import { el } from "./el";
import { en } from "./en";

export type Lang = "el" | "en";

let lang: Lang = "el";

export function setLang(next: Lang): void {
  lang = next;
}

export function getLang(): Lang {
  return lang;
}

export function t(key: string): string {
  const dict = lang === "el" ? el : en;
  return dict[key] ?? en[key] ?? key;
}

// --- Status/enum mappers (backend values → display labels) ---

const RESOLVER_MAP: Record<string, string> = {
  RESOLVED: "Επιλύθηκε",
  AMBIGUOUS: "Αμφίσημο",
  NOT_FOUND: "Δεν βρέθηκε",
  UNKNOWN: "—",
};

const ANALYZER_OUTCOME_MAP: Record<string, string> = {
  PREDICTION_AVAILABLE: "Διαθέσιμη απόφαση",
  OK: "Διαθέσιμη απόφαση",
  NO_PREDICTION: "Χωρίς πρόβλεψη",
  NO_BET: "Χωρίς πρόβλεψη",
  NO_DECISION: "Χωρίς πρόβλεψη",
  UNKNOWN: "—",
};

const DECISION_KIND_MAP: Record<string, string> = {
  PLAY: "Παίζεται",
  NO_BET: "Δεν παίζεται",
  NO_PREDICTION: "Χωρίς πρόβλεψη",
  NO_DECISION: "Χωρίς πρόβλεψη",
  UNKNOWN: "—",
};

export function labelResolverStatus(code: string): string {
  const key = (code ?? "").trim().toUpperCase() || "UNKNOWN";
  return RESOLVER_MAP[key] ?? t(`enum.resolver.${key}`) ?? code;
}

export function labelAnalyzerOutcome(code: string): string {
  const key = (code ?? "").trim().toUpperCase() || "UNKNOWN";
  if (ANALYZER_OUTCOME_MAP[key]) return ANALYZER_OUTCOME_MAP[key];
  if (/^PREDICTION_AVAILABLE|^OK$/i.test(key)) return ANALYZER_OUTCOME_MAP.PREDICTION_AVAILABLE;
  if (/^NO_PREDICTION|NO_BET|NO_DECISION$/i.test(key)) return ANALYZER_OUTCOME_MAP.NO_PREDICTION;
  return ANALYZER_OUTCOME_MAP.UNKNOWN;
}

export function labelDecisionKind(code: string): string {
  const key = (code ?? "").trim().toUpperCase() || "UNKNOWN";
  return DECISION_KIND_MAP[key] ?? (key.length > 0 ? "Παίζεται" : "—");
}

export function labelMarket(code: string): string {
  const key = (code ?? "").trim();
  if (!key) return "—";
  // Common market codes → Greek labels (optional)
  const MARKET_MAP: Record<string, string> = {
    "1X2": "1X2",
    "OU25": "Over/Under 2.5",
    "GGNG": "GG/NG",
  };
  return MARKET_MAP[key] ?? key;
}

/** Human-readable labels for backend note/warning/flag codes (e.g. NO_KICKOFF_HINT_USING_BOUNDED_WINDOW). */
const NOTE_WARNING_MAP: Record<string, string> = {
  NO_KICKOFF_HINT_USING_BOUNDED_WINDOW: "Δεν υπάρχει ακριβής ώρα έναρξης· χρησιμοποιείται εκτιμώμενο χρονικό παράθυρο.",
  NO_KICKOFF_HINT: "Δεν υπάρχει ακριβής ώρα έναρξης.",
  BOUNDED_WINDOW: "Εκτιμώμενο χρονικό παράθυρο.",
};

export function labelNoteOrWarning(code: string): string {
  const key = (code ?? "").trim();
  if (!key) return "";
  const upper = key.toUpperCase().replace(/-/g, "_");
  if (NOTE_WARNING_MAP[upper]) return NOTE_WARNING_MAP[upper];
  if (/NO_KICKOFF_HINT.*BOUNDED|BOUNDED.*WINDOW/i.test(upper)) return NOTE_WARNING_MAP.NO_KICKOFF_HINT_USING_BOUNDED_WINDOW;
  return t(`hint.${upper}`) !== `hint.${upper}` ? t(`hint.${upper}`) : key;
}
