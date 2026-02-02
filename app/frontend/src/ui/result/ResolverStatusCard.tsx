import { t, labelResolverStatus } from "../../i18n";
import type { ResolverVM } from "./types";

export interface ResolverStatusCardProps {
  resolver: ResolverVM;
}

export default function ResolverStatusCard({ resolver }: ResolverStatusCardProps) {
  const status = resolver.status || "UNKNOWN";
  const isResolved = /^RESOLVED$/i.test(status);
  const isAmbiguous = /^AMBIGUOUS$/i.test(status);
  const isNotFound = /^NOT_FOUND$/i.test(status);

  const statusClass =
    isResolved ? "ai-chip--success" : isNotFound || isAmbiguous ? "ai-chip--warn" : "";

  return (
    <div className="ai-card" style={{ flex: "1 1 280px", minWidth: 0 }}>
      <div className="ai-cardHeader">
        <div className="ai-cardTitle">{t("section.resolver")}</div>
      </div>
      <p style={{ margin: "4px 0", fontSize: 14 }}>
        <span className="ai-status-label">{t("label.status")}:</span>{" "}
        <span className={statusClass ? `ai-chip ${statusClass}` : ""}>{labelResolverStatus(status)}</span>
        {resolver.matchId != null && resolver.matchId !== "" && (
          <> · {t("label.match_id")}: {resolver.matchId}</>
        )}
      </p>
      {resolver.notes.length > 0 && (
        <ul style={{ margin: "8px 0 0 0", paddingLeft: 20 }}>
          {resolver.notes.map((n, i) => (
            <li key={i}>{String(n)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
