import { t } from "../../i18n";
import type { ResultVM } from "./types";

export interface MatchHeaderProps {
  vm: ResultVM;
}

export default function MatchHeader({ vm }: MatchHeaderProps) {
  return (
    <div className="ai-section">
      <div className="ai-card">
        <div className="ai-cardHeader">
          <div className="ai-cardTitle">{t("section.match")}</div>
        </div>
        <p style={{ margin: "4px 0" }}>
          {t("label.home")}: {vm.homeTeam || "—"} · {t("label.away")}: {vm.awayTeam || "—"}
          {vm.matchId != null && vm.matchId !== "" && (
            <> · {t("label.match_id")}: {vm.matchId}</>
          )}
        </p>
      </div>
    </div>
  );
}
