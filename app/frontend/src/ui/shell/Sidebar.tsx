/**
 * App shell — fixed dark left sidebar. Icons + labels; active state highlight.
 * No routing; onSelect callback for view switching (placeholder allowed).
 */
import { t } from "../../i18n";

export interface SidebarProps {
  activeKey?: string;
  onSelect?: (key: string) => void;
}

type MenuItem = { key: string; labelKey: string; icon: React.ReactNode };

const MENU_ITEMS: MenuItem[] = [
  {
    key: "home",
    labelKey: "nav.home",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
  },
  {
    key: "predictions",
    labelKey: "nav.predictions",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    key: "statistics",
    labelKey: "nav.statistics",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="9" y1="9" x2="15" y2="9" />
        <line x1="9" y1="15" x2="15" y2="15" />
      </svg>
    ),
  },
  {
    key: "history",
    labelKey: "nav.history",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
  },
  {
    key: "settings",
    labelKey: "nav.settings",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 1v6m0 6v6m8.66-15l-3 5.2M9.34 15.8l-3 5.2M23 12h-6m-6 0H1m19.66 3l-3-5.2M6.34 8.2l-3-5.2" />
      </svg>
    ),
  },
];

export default function Sidebar({ activeKey = "home", onSelect }: SidebarProps) {
  return (
    <aside className="ai-shell-sidebar" role="navigation" aria-label={t("aria.main_menu")}>
      <div className="ai-shell-sidebar__brand">
        <span className="ai-shell-sidebar__logo">AI Μέντορας</span>
      </div>
      <nav className="ai-shell-sidebar__nav">
        {MENU_ITEMS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`ai-shell-sidebar__item ${activeKey === item.key ? "ai-shell-sidebar__item--active" : ""}`}
            onClick={() => onSelect?.(item.key)}
            aria-current={activeKey === item.key ? "page" : undefined}
            aria-label={t(item.labelKey)}
          >
            <span className="ai-shell-sidebar__icon" aria-hidden>
              {item.icon}
            </span>
            <span className="ai-shell-sidebar__label">{t(item.labelKey)}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
