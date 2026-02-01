/** UI-specific types for decision-support MVP */

export type PageTitle =
  | "Αρχική"
  | "Νέα Πρόβλεψη"
  | "Αποτέλεσμα Πρόβλεψης"
  | "Σύνοψη Απόδοσης"
  | "Ιστορικό Προβλέψεων"
  | "Ρυθμίσεις";

export interface NavItem {
  path: string;
  label: PageTitle;
  icon?: string;
}

export type PeriodTab = "DAY" | "WEEK" | "MONTH";

export const PERIOD_LABELS: Record<PeriodTab, string> = {
  DAY: "Ημέρα",
  WEEK: "Εβδομάδα",
  MONTH: "Μήνας",
};

export const MARKET_LABELS: Record<string, string> = {
  "1X2": "1X2",
  OU25: "Over / Under 2.5",
  GGNG: "GG / NG",
};

export const DECISION_LABELS: Record<string, string> = {
  HOME: "1",
  DRAW: "X",
  AWAY: "2",
  OVER: "Over",
  UNDER: "Under",
  GG: "GG",
  NG: "NG",
  NO_BET: "Χωρίς απόφαση",
};
