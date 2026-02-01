import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { MARKET_LABELS, DECISION_LABELS } from "@/types/ui";
import type { MarketDecision } from "@/types/api";

/** Mock result when backend has no session state; replace with real API when available. */
const defaultDecisions: MarketDecision[] = [
  {
    market: "1X2",
    decision: "NO_BET",
    probabilities: { HOME: 0.35, DRAW: 0.32, AWAY: 0.33 },
    separation: 0.02,
    confidence: 0.45,
    risk: 0.35,
    reasons: ["SEPARATION_BELOW_THRESHOLD", "INSUFFICIENT_DATA_FOR_MARKET"],
  },
  {
    market: "OU25",
    decision: "OVER",
    probabilities: { OVER: 0.58, UNDER: 0.42 },
    separation: 0.16,
    confidence: 0.68,
    risk: 0.32,
    reasons: ["EXPECTED_GOALS_ABOVE_THRESHOLD"],
  },
  {
    market: "GGNG",
    decision: "GG",
    probabilities: { GG: 0.62, NG: 0.38 },
    separation: 0.24,
    confidence: 0.72,
    risk: 0.28,
    reasons: ["BOTH_TEAMS_SCORING_TREND"],
  },
];

export function PredictionResult() {
  const location = useLocation();
  const [decisions, setDecisions] = useState<MarketDecision[]>(defaultDecisions);
  const [matchHeader, setMatchHeader] = useState({
    home: "Ομάδα Α",
    away: "Ομάδα Β",
    date: new Date().toLocaleDateString("el-GR"),
    competition: "Λίγκα Α",
  });

  useEffect(() => {
    const state = location.state as { decisions?: MarketDecision[]; match?: typeof matchHeader } | null;
    if (state?.decisions?.length) setDecisions(state.decisions);
    if (state?.match) setMatchHeader(state.match);
  }, [location.state]);

  return (
    <div className="space-y-6 max-w-3xl">
      <section className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-500 uppercase mb-2">Αγώνας</h2>
        <p className="font-semibold text-gray-900">
          {matchHeader.home} vs {matchHeader.away}
        </p>
        <p className="text-sm text-gray-600 mt-1">
          {matchHeader.date} · {matchHeader.competition}
        </p>
      </section>

      <section>
        <h2 className="text-sm font-medium text-gray-500 uppercase mb-3">Αγορές</h2>
        <div className="space-y-4">
          {decisions.map((d) => (
            <div
              key={d.market}
              className="bg-white border border-gray-200 rounded-lg p-4"
            >
              <h3 className="font-medium text-gray-900 mb-2">
                {MARKET_LABELS[d.market] ?? d.market}
              </h3>
              <div className="flex flex-wrap gap-4 mb-2">
                {Object.entries(d.probabilities).map(([k, v]) => (
                  <span key={k} className="text-sm text-gray-600">
                    {DECISION_LABELS[k] ?? k}: {(v * 100).toFixed(0)}%
                  </span>
                ))}
              </div>
              <p className="text-sm">
                {d.decision === "NO_BET" ? (
                  <span className="text-amber-600 font-medium">
                    {DECISION_LABELS.NO_BET ?? "Χωρίς απόφαση"}
                  </span>
                ) : (
                  <span className="text-gray-900">
                    Επικρατέστερη: {DECISION_LABELS[d.decision] ?? d.decision} · Διάσταση: {(d.separation * 100).toFixed(0)}% · Εμπιστοσύνη: {(d.confidence * 100).toFixed(0)}% · Κίνδυνος: {(d.risk * 100).toFixed(0)}%
                  </span>
                )}
              </p>
              {d.reasons.length > 0 && (
                <ul className="mt-2 text-xs text-gray-500 list-disc list-inside">
                  {d.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-500 uppercase mb-2">Τελική Απόφαση</h2>
        <p className="text-sm text-gray-700">
          Επιλογές ανά αγορά όπως παραπάνω. Χωρίς απόφαση (NO_BET) όπου το separation ή η εμπιστοσύνη είναι κάτω από το όριο.
        </p>
      </section>
    </div>
  );
}
