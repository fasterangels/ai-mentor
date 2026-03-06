/**
 * Minimal unit tests for footballDecisionAdapter.
 * Run with: pnpm exec vitest run (if vitest is added to the project).
 */
import { describe, it, expect } from "vitest";
import { footballAnalysisToMarketDecisions } from "./footballDecisionAdapter";

describe("footballAnalysisToMarketDecisions", () => {
  it("given analysis with meta.model_prediction and decision GO => market 1X2, decision HOME, probabilities present", () => {
    const analysis = {
      meta: {
        model_prediction: { home_prob: 0.6, draw_prob: 0.2, away_prob: 0.2 },
      },
      decision: { decision: "GO", reasons: ["value_edge"] },
    };
    const decisions = footballAnalysisToMarketDecisions(analysis);
    expect(decisions).toHaveLength(1);
    expect(decisions[0].market).toBe("1X2");
    expect(decisions[0].decision).toBe("HOME");
    expect(decisions[0].probabilities).toEqual({ HOME: 0.6, DRAW: 0.2, AWAY: 0.2 });
    expect(decisions[0].reasons).toContain("value_edge");
  });
});
