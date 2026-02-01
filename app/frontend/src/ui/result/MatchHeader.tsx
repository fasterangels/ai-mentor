import type { ResultVM } from "./types";

export interface MatchHeaderProps {
  vm: ResultVM;
}

export default function MatchHeader({ vm }: MatchHeaderProps) {
  return (
    <div className="ai-section">
      <div className="ai-card">
        <div className="ai-cardHeader">
          <div className="ai-cardTitle">Match</div>
        </div>
        <p style={{ margin: "4px 0" }}>
          Home: {vm.homeTeam || "—"} · Away: {vm.awayTeam || "—"}
          {vm.matchId != null && vm.matchId !== "" && (
            <> · Match ID: {vm.matchId}</>
          )}
        </p>
      </div>
    </div>
  );
}
