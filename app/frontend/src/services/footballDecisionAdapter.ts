import type { MarketDecision } from "@/types/api";

export function footballAnalysisToMarketDecisions(analysis: any): MarketDecision[] {
  // Build only 1X2 decision for now; keep other markets absent.
  const meta = analysis?.meta ?? {};
  const pred = meta.calibrated_prediction ?? meta.model_prediction ?? {};
  const home = Number(pred.home_prob ?? 0.33);
  const draw = Number(pred.draw_prob ?? 0.33);
  const away = Number(pred.away_prob ?? 0.33);

  const maxOutcome = home >= draw && home >= away ? "HOME" : draw >= away ? "DRAW" : "AWAY";
  const maxProb = Math.max(home, draw, away);
  const sorted = [home, draw, away].sort((a, b) => b - a);
  const separation = sorted[0] - sorted[1];

  const decisionPayload = analysis?.decision ?? meta?.decision ?? {};
  const dec = decisionPayload?.decision ?? "LOW_CONFIDENCE";
  // Map GO/NO_GO/LOW_CONFIDENCE to MarketDecision decision:
  // - GO => pick maxOutcome
  // - NO_GO or LOW_CONFIDENCE => NO_BET
  const decision = dec === "GO" ? (maxOutcome as any) : ("NO_BET" as any);

  const reasons: string[] = [];
  const dr = decisionPayload?.reasons ?? [];
  for (const r of dr) reasons.push(String(r));
  const vr = meta?.value_reason_codes ?? [];
  for (const r of vr) reasons.push(String(r));

  // confidence: use maxProb
  // risk: simple proxy (1 - maxProb)
  const confidence = maxProb;
  const risk = Math.max(0, Math.min(1, 1 - maxProb));

  return [
    {
      market: "1X2" as any,
      decision,
      probabilities: { HOME: home, DRAW: draw, AWAY: away },
      separation,
      confidence,
      risk,
      reasons,
    },
  ];
}
