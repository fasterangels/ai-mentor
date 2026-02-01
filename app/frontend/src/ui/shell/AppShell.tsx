/**
 * App shell — permanent frame: fixed dark sidebar + top bar + main content.
 * Wraps all views; no routing logic here.
 */
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export interface AppShellProps {
  /** Which sidebar item is active (e.g. "home", "predictions"). */
  activeKey?: string;
  /** Called when user selects a sidebar item (placeholder allowed). */
  onSidebarSelect?: (key: string) => void;
  /** Top bar page title. */
  pageTitle: string;
  /** Status text in top bar (e.g. "Ready", "Online"). */
  statusLabel?: string;
  /** Main content area. */
  children: React.ReactNode;
}

export default function AppShell({
  activeKey = "home",
  onSidebarSelect,
  pageTitle,
  statusLabel = "Ready",
  children,
}: AppShellProps) {
  return (
    <div className="ai-shell">
      <Sidebar activeKey={activeKey} onSelect={onSidebarSelect} />
      <div className="ai-shell-main">
        <Topbar pageTitle={pageTitle} statusLabel={statusLabel} />
        <main className="ai-shell-content" role="main">
          {children}
        </main>
      </div>
    </div>
  );
}
