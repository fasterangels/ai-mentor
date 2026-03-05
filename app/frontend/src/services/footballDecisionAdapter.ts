import type { MarketDecision } from "@/types/api";

type FootballPrediction = {
  home_prob?: number;
  draw_prob?: number;
  away_prob?: number;
};

type FootballMeta = {
  calibrated_prediction?: FootballPrediction;
  model_prediction?: FootballPrediction;
  value_reason_codes?: string[];
  decision?: FootballDecision;
};

type FootballDecision = {
  decision?: string;
  reasons?: string[];
};

type FootballAnalysis = {
  meta?: FootballMeta;
  decision?: FootballDecision;
};

export function footballAnalysisToMarketDecisions(analysis: FootballAnalysis): MarketDecision[] {
  const meta = analysis.meta ?? {};
  const pred = meta.calibrated_prediction ?? meta.model_prediction ?? {};

  const home = Number(pred.home_prob ?? 0.33);
  const draw = Number(pred.draw_prob ?? 0.33);
  const away = Number(pred.away_prob ?? 0.33);

  const maxOutcome = home >= draw && home >= away ? "HOME" : draw >= away ? "DRAW" : "AWAY";
  const maxProb = Math.max(home, draw, away);
  const sorted = [home, draw, away].sort((a, b) => b - a);
  const separation = sorted[0] - sorted[1];

  const decisionPayload = analysis.decision ?? meta.decision ?? {};
  const dec = decisionPayload.decision ?? "LOW_CONFIDENCE";
  const decision: string = dec === "GO" ? maxOutcome : "NO_BET";

  const reasons: string[] = [];
  const dr: string[] = decisionPayload.reasons ?? [];
  for (const r of dr) reasons.push(String(r));
  const vr: string[] = meta.value_reason_codes ?? [];
  for (const r of vr) reasons.push(String(r));

  const confidence = maxProb;
  const risk = Math.max(0, Math.min(1, 1 - maxProb));

  const result: MarketDecision = {
    market: "1X2",
    decision,
    probabilities: { HOME: home, DRAW: draw, AWAY: away },
    separation,
    confidence,
    risk,
    reasons,
  };
  return [result];
}
