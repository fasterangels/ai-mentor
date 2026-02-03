/**
 * History page — single table view: Date | Teams | Prediction | Odds | Final | Success.
 * Uses existing snapshot data; no backend changes. Empty state when no rows.
 */
import React from "react";
import { t } from "../../i18n";

export interface HistoryRow {
  id: string;
  created_at: string;
  homeTeam: string;
  awayTeam: string;
  /** When present, show ✔ (green) or ✖ (red). When absent, show —. */
  success?: boolean | null;
  result: {
    analyzer?: {
      decisions?: Array<{ decision?: string; confidence?: number; market?: string }>;
    };
  };
}

export interface HistoryTableProps {
  rows: HistoryRow[];
  onRowClick?: (row: HistoryRow) => void;
}

function getPlayPredictions(row: HistoryRow): string[] {
  const decisions = row.result?.analyzer?.decisions ?? [];
  return decisions
    .filter((d) => {
      const dec = (d.decision ?? "").trim().toUpperCase();
      return dec && dec !== "NO_BET" && dec !== "NO_PREDICTION" && dec !== "NO_DECISION";
    })
    .map((d) => (d.decision ?? "").trim())
    .filter(Boolean);
}

export default function HistoryTable({ rows, onRowClick }: HistoryTableProps) {
  if (rows.length === 0) {
    return (
      <div className="ai-history-empty" role="status">
        <h2 className="ai-history-empty__title">{t("history.empty_title")}</h2>
        <p className="ai-history-empty__body">{t("history.empty_body")}</p>
      </div>
    );
  }

  return (
    <div className="ai-history-wrap">
      <table className="ai-history-table">
        <thead>
          <tr>
            <th scope="col">{t("history.col_date")}</th>
            <th scope="col">{t("history.col_teams")}</th>
            <th scope="col">{t("history.col_prediction")}</th>
            <th scope="col">{t("history.col_odds")}</th>
            <th scope="col">{t("history.col_final_result")}</th>
            <th scope="col">{t("history.col_success")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const predictions = getPlayPredictions(row);
            const predictionLabel = predictions.length
              ? predictions.join(" | ")
              : t("history.no_value");
            const dateLabel = (() => {
              try {
                return new Date(row.created_at).toLocaleDateString(undefined, {
                  dateStyle: "short",
                });
              } catch {
                return row.created_at || t("history.no_value");
              }
            })();

            return (
              <tr
                key={row.id}
                className="ai-history-row"
                onClick={() => onRowClick?.(row)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onRowClick?.(row);
                  }
                }}
                aria-label={`${row.homeTeam} vs ${row.awayTeam}, ${dateLabel}`}
              >
                <td className="ai-history-cell ai-history-cell--date">{dateLabel}</td>
                <td className="ai-history-cell ai-history-cell--teams">
                  <span className="ai-history-teams">
                    {row.homeTeam || t("history.no_value")} vs {row.awayTeam || t("history.no_value")}
                  </span>
                </td>
                <td className="ai-history-cell ai-history-cell--prediction">
                  {predictions.length > 0 ? (
                    <span className="ai-history-badges">
                      {predictions.map((p, i) => (
                        <span key={`${row.id}-${i}`} className="ai-history-badge">
                          {p}
                        </span>
                      ))}
                    </span>
                  ) : (
                    <span className="ai-history-muted">{t("history.no_value")}</span>
                  )}
                </td>
                <td className="ai-history-cell ai-history-cell--odds">
                  <span className="ai-history-muted">{t("history.no_value")}</span>
                </td>
                <td className="ai-history-cell ai-history-cell--final">
                  <span className="ai-history-muted">{t("history.no_value")}</span>
                </td>
                <td className="ai-history-cell ai-history-cell--success">
                  {row.success === true && (
                    <span className="ai-history-success-icon ai-history-success-icon--ok" aria-hidden title={t("history.col_success")}>
                      ✔
                    </span>
                  )}
                  {row.success === false && (
                    <span className="ai-history-success-icon ai-history-success-icon--fail" aria-hidden title={t("history.col_success")}>
                      ✖
                    </span>
                  )}
                  {(row.success !== true && row.success !== false) && (
                    <span className="ai-history-muted" aria-hidden>—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
