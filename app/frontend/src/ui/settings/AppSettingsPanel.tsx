/**
 * BLOCK 3: Settings surface — read-only defaults + local persistence.
 * Single view: analyzer version (read-only), restore window on launch (toggle), export file name template (preview only).
 * localStorage only; no backend calls.
 */
import { useCallback, useEffect, useState } from "react";

export const SETTINGS_STORAGE_KEYS = {
  restoreWindowDefaults: "ai-mentor.restoreWindowDefaults",
  exportFileNameTemplate: "ai-mentor.exportFileNameTemplate",
} as const;

const DEFAULT_RESTORE_WINDOW = true;
const DEFAULT_EXPORT_TEMPLATE = "result_{matchId}";

function getStoredBoolean(key: string, defaultValue: boolean): boolean {
  try {
    const v = localStorage.getItem(key);
    if (v === null) return defaultValue;
    return v !== "false" && v !== "0";
  } catch {
    return defaultValue;
  }
}

function getStoredString(key: string, defaultValue: string): string {
  try {
    const v = localStorage.getItem(key);
    return v != null && v.trim() !== "" ? v.trim() : defaultValue;
  } catch {
    return defaultValue;
  }
}

/** Preview: replace {matchId} with sample, {timestamp} with sample. */
function previewFileName(template: string): string {
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return template
    .replace(/\{matchId\}/gi, "match123")
    .replace(/\{timestamp\}/gi, ts)
    .replace(/\{date\}/gi, new Date().toISOString().slice(0, 10));
}

export interface AppSettingsPanelProps {
  /** Analyzer version from last result (read-only). */
  analyzerVersionFromResult: string | null;
  onClose: () => void;
}

export default function AppSettingsPanel({
  analyzerVersionFromResult,
  onClose,
}: AppSettingsPanelProps) {
  const [restoreWindow, setRestoreWindow] = useState(() =>
    getStoredBoolean(SETTINGS_STORAGE_KEYS.restoreWindowDefaults, DEFAULT_RESTORE_WINDOW)
  );
  const exportTemplate = getStoredString(
    SETTINGS_STORAGE_KEYS.exportFileNameTemplate,
    DEFAULT_EXPORT_TEMPLATE
  );
  const preview = previewFileName(exportTemplate) + ".pdf";

  useEffect(() => {
    try {
      localStorage.setItem(
        SETTINGS_STORAGE_KEYS.restoreWindowDefaults,
        restoreWindow ? "true" : "false"
      );
    } catch {
      /* ignore */
    }
  }, [restoreWindow]);

  const handleRestoreToggle = useCallback(() => {
    setRestoreWindow((prev) => !prev);
  }, []);

  return (
    <div className="ai-card" style={{ marginTop: 16 }}>
      <div className="ai-cardHeader" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div className="ai-cardTitle">Settings</div>
        <button
          type="button"
          className="ai-btn ai-btn--ghost"
          onClick={onClose}
          aria-label="Close settings"
        >
          Close
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 8 }}>
        {/* Analyzer version (read-only) */}
        <div>
          <span className="ai-status-label">Analyzer version (from last result):</span>{" "}
          <span className="ai-muted">
            {analyzerVersionFromResult != null && analyzerVersionFromResult !== ""
              ? analyzerVersionFromResult
              : "—"}
          </span>
        </div>

        {/* Restore window on launch */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            id="ai-settings-restore-window"
            checked={restoreWindow}
            onChange={handleRestoreToggle}
            aria-describedby="ai-settings-restore-desc"
          />
          <label htmlFor="ai-settings-restore-window" id="ai-settings-restore-desc">
            Restore window size on launch
          </label>
        </div>

        {/* Export file name template (preview only) */}
        <div>
          <span className="ai-status-label">Export file name template (preview):</span>
          <p className="ai-muted" style={{ margin: "4px 0 0 0", fontSize: 12 }}>
            Template: <code style={{ fontSize: 11 }}>{exportTemplate}.pdf</code>
          </p>
          <p className="ai-muted" style={{ margin: "4px 0 0 0", fontSize: 12 }}>
            Preview: <code style={{ fontSize: 11 }}>{preview}</code>
          </p>
        </div>
      </div>
    </div>
  );
}
