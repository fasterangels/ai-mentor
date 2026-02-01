/**
 * App shell — top bar: page title, search (UI only), status indicator (visual only).
 */
export interface TopbarProps {
  pageTitle: string;
  statusLabel?: string;
}

export default function Topbar({ pageTitle, statusLabel = "Ready" }: TopbarProps) {
  return (
    <header className="ai-shell-topbar" role="banner">
      <h1 className="ai-shell-topbar__title">{pageTitle}</h1>
      <div className="ai-shell-topbar__center">
        <input
          type="search"
          className="ai-shell-topbar__search"
          placeholder="Αναζήτηση…"
          aria-label="Search"
          readOnly
          tabIndex={-1}
        />
      </div>
      <div className="ai-shell-topbar__status" role="status" aria-label="Status">
        <span className="ai-shell-topbar__status-dot" />
        <span className="ai-shell-topbar__status-label">{statusLabel}</span>
      </div>
    </header>
  );
}
