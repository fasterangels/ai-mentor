# Final smoke test (manual, no framework)

Run through this checklist before release. All items must pass.

- [ ] **App launches (desktop)** — Double-click or start the Tauri app; window opens without a terminal/console.
- [ ] **Analyze works (success + NO_PREDICTION)** — Run Analyze; request completes with either success or NO_PREDICTION (no crash).
- [ ] **Structured result renders correctly** — Resolver, Evidence Pack, Analyzer Decision, and NO_PREDICTION (when applicable) sections display.
- [ ] **Export JSON works** — Click "Export analysis (JSON)"; file is saved (desktop) or downloaded (browser) with valid JSON.
- [ ] **Export PDF works** — Click "Export analysis (PDF)"; PDF is saved/downloaded with readable report content.
- [ ] **No runtime errors in console** — DevTools console shows no errors during the above flows.
