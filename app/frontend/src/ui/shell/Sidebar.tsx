/**
 * App shell — fixed dark left sidebar. Icons + labels; active state highlight.
 * No routing; onSelect callback for view switching (placeholder allowed).
 */
export interface SidebarProps {
  activeKey?: string;
  onSelect?: (key: string) => void;
}

const MENU_ITEMS: { key: string; label: string; icon: string }[] = [
  { key: "home", label: "Αρχική", icon: "⌂" },
  { key: "predictions", label: "Προβλέψεις", icon: "◆" },
  { key: "statistics", label: "Στατιστικά", icon: "▣" },
  { key: "history", label: "Ιστορικό", icon: "☰" },
  { key: "settings", label: "Ρυθμίσεις", icon: "⚙" },
];

export default function Sidebar({ activeKey = "home", onSelect }: SidebarProps) {
  return (
    <aside className="ai-shell-sidebar" role="navigation" aria-label="Main menu">
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
            aria-label={item.label}
          >
            <span className="ai-shell-sidebar__icon" aria-hidden>{item.icon}</span>
            <span className="ai-shell-sidebar__label">{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
