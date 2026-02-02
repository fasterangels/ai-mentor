import { t } from "../../i18n";
import type { EvidenceVM } from "./types";

export interface EvidenceListProps {
  items: EvidenceVM[];
}

export default function EvidenceList({ items }: EvidenceListProps) {
  return (
    <div className="ai-section">
      <div className="ai-card">
        <div className="ai-cardHeader">
          <div className="ai-cardTitle">{t("section.evidence_pack")}</div>
        </div>
        {items.length === 0 ? (
          <p className="ai-muted" style={{ margin: 0 }}>{t("empty.no_evidence")}</p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 20, listStyle: "disc" }}>
            {items.map((item, i) => (
              <li key={i} style={{ marginBottom: 6 }}>
                <strong>{item.title}</strong>: {item.detail}
                {item.source != null && item.source !== "" && (
                  <span className="ai-muted" style={{ fontSize: 12 }}> · {item.source}</span>
                )}
                {item.confidence != null && (
                  <span className="ai-muted" style={{ fontSize: 12 }}> · confidence: {String(item.confidence)}</span>
                )}
                {item.tags != null && item.tags.length > 0 && (
                  <span style={{ marginLeft: 4 }}>
                    {item.tags.map((t, j) => (
                      <span key={j} className="ai-chip ai-chip--flag" style={{ marginRight: 4 }}>{t}</span>
                    ))}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
