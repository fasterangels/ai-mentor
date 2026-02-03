/**
 * App shell — top bar: page title, optional search, optional status indicator.
 * Pure UI; backend lifecycle is handled outside and passed in via props.
 */
import { t } from "../../i18n";

export interface TopbarProps {
  pageTitle: string;
  statusLabel?: string;
  /** Whether to show the read-only search input. Defaults to true. */
  showSearch?: boolean;
  /** Whether to show the status pill (e.g. backend ready). Defaults to true. */
  showStatus?: boolean;
}

export default function Topbar({
  pageTitle,
  statusLabel,
  showSearch = true,
  showStatus = true,
}: TopbarProps) {
  const defaultStatus = t("topbar.status_ready");
  return (
    <header className="ai-shell-topbar" role="banner">
      <h1 className="ai-shell-topbar__title">{pageTitle}</h1>
      {showSearch && (
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
      )}
      {showStatus && (
        <div className="ai-shell-topbar__status" role="status" aria-label={t("label.status")}>
          <span className="ai-shell-topbar__status-dot" />
          <span className="ai-shell-topbar__status-label">{statusLabel ?? defaultStatus}</span>
        </div>
      )}
    </header>
  );
}
