/**
 * Statistics / Performance Summary — KPIs, time tabs (Day/Week/Month), bar chart, detail table.
 * Data from snapshots only; no backend calls. Success/failure from optional snapshot.success.
 */
import React, { useMemo, useState } from "react";
import { t } from "../../i18n";
import SegmentedControl from "../prediction/SegmentedControl";

export type SummaryTimeSegment = "day" | "week" | "month";

export interface SummarySnapshot {
  id: string;
  created_at: string;
  success?: boolean | null;
}

export interface SummaryPageProps {
  snapshots: SummarySnapshot[];
}

function toDateKey(iso: string): string {
  try {
    const d = new Date(iso);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  } catch {
    return iso.slice(0, 10) || "";
  }
}

function getRange(segment: SummaryTimeSegment): { start: Date; end: Date } {
  const end = new Date();
  end.setHours(23, 59, 59, 999);
  const start = new Date();
  if (segment === "day") {
    start.setHours(0, 0, 0, 0);
    return { start, end };
  }
  if (segment === "week") {
    start.setDate(start.getDate() - 6);
    start.setHours(0, 0, 0, 0);
    return { start, end };
  }
  start.setMonth(start.getMonth() - 1);
  start.setDate(1);
  start.setHours(0, 0, 0, 0);
  return { start, end };
}

function filterByRange(snapshots: SummarySnapshot[], segment: SummaryTimeSegment): SummarySnapshot[] {
  const { start, end } = getRange(segment);
  return snapshots.filter((s) => {
    const t = new Date(s.created_at).getTime();
    return t >= start.getTime() && t <= end.getTime();
  });
}

interface DayRow {
  dateKey: string;
  dateLabel: string;
  total: number;
  wins: number;
  losses: number;
  successPct: number;
  result: "ok" | "fail" | "neutral";
}

function buildDayRows(snapshots: SummarySnapshot[], segment: SummaryTimeSegment): DayRow[] {
  const filtered = filterByRange(snapshots, segment);
  const byDay = new Map<string, { total: number; wins: number; losses: number }>();
  for (const s of filtered) {
    const key = toDateKey(s.created_at);
    const row = byDay.get(key) ?? { total: 0, wins: 0, losses: 0 };
    row.total += 1;
    if (s.success === true) row.wins += 1;
    else if (s.success === false) row.losses += 1;
    byDay.set(key, row);
  }
  const keys = Array.from(byDay.keys()).sort();
  return keys.map((dateKey) => {
    const r = byDay.get(dateKey)!;
    const successPct = r.total > 0 ? Math.round((r.wins / r.total) * 100) : 0;
    let result: "ok" | "fail" | "neutral" = "neutral";
    if (r.wins > r.losses) result = "ok";
    else if (r.losses > r.wins) result = "fail";
    const dateLabel = (() => {
      try {
        const [y, m, d] = dateKey.split("-").map(Number);
        return new Date(y, m - 1, d).toLocaleDateString(undefined, { dateStyle: "short" });
      } catch {
        return dateKey;
      }
    })();
    return { dateKey, dateLabel, total: r.total, wins: r.wins, losses: r.losses, successPct, result };
  });
}

export default function SummaryPage({ snapshots }: SummaryPageProps) {
  const [segment, setSegment] = useState<SummaryTimeSegment>("week");

  const filtered = useMemo(() => filterByRange(snapshots, segment), [snapshots, segment]);
  const dayRows = useMemo(() => buildDayRows(snapshots, segment), [snapshots, segment]);

  const total = filtered.length;
  const wins = filtered.filter((s) => s.success === true).length;
  const losses = filtered.filter((s) => s.success === false).length;
  const successPct = total > 0 ? Math.round((wins / total) * 100) : 0;
  const failurePct = total > 0 ? Math.round((losses / total) * 100) : 0;

  const chartData = useMemo(() => {
    return dayRows.map((row) => ({ label: row.dateLabel, wins: row.wins, losses: row.losses }));
  }, [dayRows]);

  const maxBar = useMemo(() => {
    let m = 0;
    for (const d of chartData) m = Math.max(m, d.wins + d.losses);
    return m || 1;
  }, [chartData]);

  return (
    <div className="ai-summary-page">
      <header className="ai-summary-header">
        <h1 className="ai-summary-title">{t("stats.title")}</h1>
        <SegmentedControl
          value={segment}
          onChange={(v) => setSegment(v as SummaryTimeSegment)}
          options={[
            { value: "day", label: t("stats.tab_day") },
            { value: "week", label: t("stats.tab_week") },
            { value: "month", label: t("stats.tab_month") },
          ]}
          aria-label={t("stats.title")}
        />
      </header>

      <section className="ai-summary-kpis">
        <div className="ai-summary-kpi">
          <span className="ai-summary-kpi__label">{t("stats.kpi_total")}</span>
          <span className="ai-summary-kpi__value">{total}</span>
        </div>
        <div className="ai-summary-kpi">
          <span className="ai-summary-kpi__label">{t("stats.kpi_success_pct")}</span>
          <span className="ai-summary-kpi__value ai-summary-kpi__value--success">{successPct}%</span>
        </div>
        <div className="ai-summary-kpi">
          <span className="ai-summary-kpi__label">{t("stats.kpi_failure_pct")}</span>
          <span className="ai-summary-kpi__value ai-summary-kpi__value--failure">{failurePct}%</span>
        </div>
        <div className="ai-summary-kpi">
          <span className="ai-summary-kpi__label">{t("stats.kpi_period_result")}</span>
          <span className="ai-summary-kpi__value">{total > 0 ? `${successPct}%` : "—"}</span>
        </div>
      </section>

      <section className="ai-summary-chart">
        <h2 className="ai-summary-chart__title">{t("stats.chart_title")}</h2>
        {chartData.length === 0 ? (
          <p className="ai-summary-muted">{t("stats.no_data")}</p>
        ) : (
          <div className="ai-summary-bars">
            {chartData.map((d, i) => (
              <div key={d.label + i} className="ai-summary-bar-wrap">
                <div className="ai-summary-bar-label">{d.label}</div>
                <div className="ai-summary-bar-track">
                  <div
                    className="ai-summary-bar ai-summary-bar--success"
                    style={{ width: `${maxBar ? (d.wins / maxBar) * 100 : 0}%` }}
                  />
                  <div
                    className="ai-summary-bar ai-summary-bar--failure"
                    style={{ width: `${maxBar ? (d.losses / maxBar) * 100 : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="ai-summary-table-wrap">
        <h2 className="ai-summary-table-title">{t("stats.table_title")}</h2>
        {dayRows.length === 0 ? (
          <p className="ai-summary-muted">{t("stats.no_data")}</p>
        ) : (
          <div className="ai-summary-table-scroll">
            <table className="ai-summary-table">
              <thead>
                <tr>
                  <th scope="col">{t("stats.col_date")}</th>
                  <th scope="col">{t("stats.col_predictions")}</th>
                  <th scope="col">{t("stats.col_wins")}</th>
                  <th scope="col">{t("stats.col_losses")}</th>
                  <th scope="col">{t("stats.col_success_pct")}</th>
                  <th scope="col">{t("stats.col_result")}</th>
                </tr>
              </thead>
              <tbody>
                {dayRows.map((row, idx) => (
                  <tr key={row.dateKey} className="ai-summary-table-row">
                    <td className="ai-summary-table-cell">{row.dateLabel}</td>
                    <td className="ai-summary-table-cell">{row.total}</td>
                    <td className="ai-summary-table-cell">{row.wins}</td>
                    <td className="ai-summary-table-cell">{row.losses}</td>
                    <td className="ai-summary-table-cell ai-summary-table-cell--pct">
                      <span className="ai-summary-pct-bar-wrap">
                        <span className="ai-summary-pct-track">
                          <span className="ai-summary-pct-bar" style={{ width: `${row.successPct}%` }} />
                        </span>
                        <span className="ai-summary-pct-value">{row.successPct}%</span>
                      </span>
                    </td>
                    <td className="ai-summary-table-cell ai-summary-table-cell--result">
                      {row.result === "ok" && <span className="ai-summary-result-icon ai-summary-result-icon--ok" aria-hidden>✔</span>}
                      {row.result === "fail" && <span className="ai-summary-result-icon ai-summary-result-icon--fail" aria-hidden>✖</span>}
                      {row.result === "neutral" && <span className="ai-summary-muted">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
