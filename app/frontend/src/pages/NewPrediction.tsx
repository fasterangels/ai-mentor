import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { runShadowPipeline } from "@/api/analyzer";

const COMPETITIONS = [
  { id: "league-a", name: "Λίγκα Α" },
  { id: "league-b", name: "Λίγκα Β" },
];

const TEAMS = [
  { id: "team-1", name: "Ομάδα Α" },
  { id: "team-2", name: "Ομάδα Β" },
  { id: "team-3", name: "Ομάδα Γ" },
];

export function NewPrediction() {
  const navigate = useNavigate();
  const [competitionId, setCompetitionId] = useState<string>("");
  const [homeTeamId, setHomeTeamId] = useState<string>("");
  const [awayTeamId, setAwayTeamId] = useState<string>("");
  const [matchDate, setMatchDate] = useState<string>("");
  const [mode, setMode] = useState<"PREGAME" | "LIVE">("PREGAME");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const report = await runShadowPipeline({
        connector_name: "sample_platform",
        match_id: "sample_platform_match_001",
        final_home_goals: 0,
        final_away_goals: 0,
        status: "FINAL",
      });
      if (report.error) {
        setError(report.detail || report.error);
        return;
      }
      const homeName = TEAMS.find((t) => t.id === homeTeamId)?.name ?? "—";
      const awayName = TEAMS.find((t) => t.id === awayTeamId)?.name ?? "—";
      const compName = COMPETITIONS.find((c) => c.id === competitionId)?.name ?? "—";
      navigate("/prediction-result", {
        state: {
          decisions: report.analysis?.decisions ?? [],
          match: {
            home: homeName,
            away: awayName,
            date: matchDate ? new Date(matchDate).toLocaleDateString("el-GR") : new Date().toLocaleDateString("el-GR"),
            competition: compName,
          },
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Σφάλμα δικτύου");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Κατηγορία / Λίγκα
          </label>
          <select
            value={competitionId}
            onChange={(e) => setCompetitionId(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="">— Επιλέξτε —</option>
            {COMPETITIONS.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Ομάδα
          </label>
          <select
            value={homeTeamId}
            onChange={(e) => setHomeTeamId(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="">— Επιλέξτε —</option>
            {TEAMS.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Αντίπαλος
          </label>
          <select
            value={awayTeamId}
            onChange={(e) => setAwayTeamId(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="">— Επιλέξτε —</option>
            {TEAMS.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Ημερομηνία
          </label>
          <input
            type="datetime-local"
            value={matchDate}
            onChange={(e) => setMatchDate(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Κατάσταση
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="mode"
                checked={mode === "PREGAME"}
                onChange={() => setMode("PREGAME")}
              />
              <span className="text-sm">Pre-Game</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="mode"
                checked={mode === "LIVE"}
                onChange={() => setMode("LIVE")}
              />
              <span className="text-sm">Live</span>
            </label>
          </div>
        </div>
        {error && (
          <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">
            {error}
          </div>
        )}
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700"
          >
            Ακύρωση
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-gray-800 text-white rounded-md text-sm font-medium disabled:opacity-50"
          >
            {submitting ? "Εκτέλεση..." : "Εκτέλεση"}
          </button>
        </div>
      </form>
    </div>
  );
}
