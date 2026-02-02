/**
 * App shell — top bar: page title, search (UI only), status indicator (visual only).
 */
import { t } from "../../i18n";

export interface TopbarProps {
  pageTitle: string;
  statusLabel?: string;
}

export default function Topbar({ pageTitle, statusLabel }: TopbarProps) {
  const defaultStatus = t("topbar.status_ready");
  return (
    <header className="ai-shell-topbar" role="banner">
      <h1 className="ai-shell-topbar__title">{pageTitle}</h1>
      <div className="ai-shell-topbar__center">
        <input
          type="search"
          className="ai-shell-topbar__search"
          placeholder={t("topbar.search_placeholder")}
          aria-label={t("topbar.search_placeholder")}
          readOnly
          tabIndex={-1}
        />
      </div>
      <div className="ai-shell-topbar__status" role="status" aria-label={t("label.status")}>
        <span className="ai-shell-topbar__status-dot" />
        <span className="ai-shell-topbar__status-label">{statusLabel ?? defaultStatus}</span>
      </div>
    </header>
  );
}
