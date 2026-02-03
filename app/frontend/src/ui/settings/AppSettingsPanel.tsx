/**
 * Settings — grouped sections for offline-first desktop. No account, no login.
 * General | Predictions | Data & History | Appearance. localStorage only.
 */
import { useCallback, useEffect, useState } from "react";
import { t, setLang, getLang } from "../../i18n";

export const SETTINGS_STORAGE_KEYS = {
  restoreWindowDefaults: "ai-mentor.restoreWindowDefaults",
  exportFileNameTemplate: "ai-mentor.exportFileNameTemplate",
  language: "ai-mentor.language",
  timezone: "ai-mentor.timezone",
  defaultStartView: "ai-mentor.defaultStartView",
  liveModeEnabled: "ai-mentor.liveModeEnabled",
  defaultAnalysisMode: "ai-mentor.defaultAnalysisMode",
  showNoPredictionExplanations: "ai-mentor.showNoPredictionExplanations",
  keepHistory: "ai-mentor.keepHistory",
  autoLoadLastPrediction: "ai-mentor.autoLoadLastPrediction",
  theme: "ai-mentor.theme",
  layoutDensity: "ai-mentor.layoutDensity",
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

function previewFileName(template: string): string {
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return template
    .replace(/\{matchId\}/gi, "match123")
    .replace(/\{timestamp\}/gi, ts)
    .replace(/\{date\}/gi, new Date().toISOString().slice(0, 10));
}

export interface AppSettingsPanelProps {
  analyzerVersionFromResult: string | null;
  onClose: () => void;
  onClearHistory?: () => void;
}

function SettingsSection({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="ai-settings-section">
      <h2 className="ai-settings-section__title">
        <span className="ai-settings-section__icon" aria-hidden>{icon}</span>
        {title}
      </h2>
      <div className="ai-settings-section__body">{children}</div>
    </section>
  );
}

export default function AppSettingsPanel({
  analyzerVersionFromResult,
  onClose,
  onClearHistory,
}: AppSettingsPanelProps) {
  const [language, setLanguageState] = useState(() =>
    getStoredString(SETTINGS_STORAGE_KEYS.language, getLang())
  );
  const [timezone, setTimezone] = useState(() =>
    getStoredString(SETTINGS_STORAGE_KEYS.timezone, "browser")
  );
  const [defaultStartView, setDefaultStartView] = useState(() =>
    getStoredString(SETTINGS_STORAGE_KEYS.defaultStartView, "home")
  );
  const [restoreWindow, setRestoreWindow] = useState(() =>
    getStoredBoolean(SETTINGS_STORAGE_KEYS.restoreWindowDefaults, DEFAULT_RESTORE_WINDOW)
  );

  const [liveModeEnabled, setLiveModeEnabled] = useState(() =>
    getStoredBoolean(SETTINGS_STORAGE_KEYS.liveModeEnabled, false)
  );
  const [defaultAnalysisMode, setDefaultAnalysisMode] = useState(() =>
    getStoredString(SETTINGS_STORAGE_KEYS.defaultAnalysisMode, "pregame")
  );
  const [showNoPredictionExplanations, setShowNoPredictionExplanations] = useState(() =>
    getStoredBoolean(SETTINGS_STORAGE_KEYS.showNoPredictionExplanations, true)
  );

  const [keepHistory, setKeepHistory] = useState(() =>
    getStoredBoolean(SETTINGS_STORAGE_KEYS.keepHistory, true)
  );
  const [autoLoadLast, setAutoLoadLast] = useState(() =>
    getStoredBoolean(SETTINGS_STORAGE_KEYS.autoLoadLastPrediction, false)
  );

  const [layoutDensity, setLayoutDensity] = useState(() =>
    getStoredString(SETTINGS_STORAGE_KEYS.layoutDensity, "comfortable")
  );

  const exportTemplate = getStoredString(
    SETTINGS_STORAGE_KEYS.exportFileNameTemplate,
    DEFAULT_EXPORT_TEMPLATE
  );
  const preview = previewFileName(exportTemplate) + ".pdf";

  const persist = useCallback((key: string, value: string | boolean) => {
    try {
      localStorage.setItem(key, String(value));
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.restoreWindowDefaults, restoreWindow);
  }, [restoreWindow, persist]);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.language, language);
    setLang(language as "el" | "en");
  }, [language, persist]);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.timezone, timezone);
  }, [timezone, persist]);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.defaultStartView, defaultStartView);
  }, [defaultStartView, persist]);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.liveModeEnabled, liveModeEnabled);
  }, [liveModeEnabled, persist]);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.defaultAnalysisMode, defaultAnalysisMode);
  }, [defaultAnalysisMode, persist]);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.showNoPredictionExplanations, showNoPredictionExplanations);
  }, [showNoPredictionExplanations, persist]);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.keepHistory, keepHistory);
  }, [keepHistory, persist]);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.autoLoadLastPrediction, autoLoadLast);
  }, [autoLoadLast, persist]);

  useEffect(() => {
    persist(SETTINGS_STORAGE_KEYS.layoutDensity, layoutDensity);
  }, [layoutDensity, persist]);

  const handleClearHistory = useCallback(() => {
    if (window.confirm(t("settings.clear_history_confirm"))) {
      onClearHistory?.();
    }
  }, [onClearHistory]);

  return (
    <div className="ai-settings-page">
      <header className="ai-settings-header">
        <h1 className="ai-settings-title">{t("settings.title")}</h1>
        <button
          type="button"
          className="ai-btn ai-btn--ghost"
          onClick={onClose}
          aria-label={t("settings.close")}
        >
          {t("btn.close")}
        </button>
      </header>

      <div className="ai-settings-sections">
        <SettingsSection
          title={t("settings.section_general")}
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
          }
        >
          <div className="ai-settings-row">
            <label className="ai-settings-label">{t("settings.language")}</label>
            <select
              className="ai-select"
              value={language}
              onChange={(e) => setLanguageState(e.target.value)}
              aria-label={t("settings.language")}
            >
              <option value="el">Ελληνικά</option>
              <option value="en">English</option>
            </select>
          </div>
          <div className="ai-settings-row">
            <label className="ai-settings-label">{t("settings.timezone")}</label>
            <select
              className="ai-select"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              aria-label={t("settings.timezone")}
            >
              <option value="browser">{t("settings.timezone_browser")}</option>
              <option value="Europe/Athens">Europe/Athens</option>
              <option value="Europe/London">Europe/London</option>
              <option value="UTC">UTC</option>
            </select>
          </div>
          <div className="ai-settings-row">
            <label className="ai-settings-label">{t("settings.default_start_view")}</label>
            <select
              className="ai-select"
              value={defaultStartView}
              onChange={(e) => setDefaultStartView(e.target.value)}
              aria-label={t("settings.default_start_view")}
            >
              <option value="home">{t("settings.view_home")}</option>
              <option value="predictions">{t("settings.view_predictions")}</option>
              <option value="history">{t("settings.view_history")}</option>
            </select>
          </div>
          <div className="ai-settings-row ai-settings-row--toggle">
            <input
              type="checkbox"
              id="ai-settings-restore-window"
              checked={restoreWindow}
              onChange={() => setRestoreWindow((p) => !p)}
              aria-describedby="ai-settings-restore-desc"
            />
            <label htmlFor="ai-settings-restore-window" id="ai-settings-restore-desc">
              {t("settings.restore_window")}
            </label>
          </div>
          <div className="ai-settings-row">
            <span className="ai-settings-meta">{t("settings.analyzer_version")}:</span>{" "}
            <span className="ai-muted">{analyzerVersionFromResult ?? "—"}</span>
          </div>
        </SettingsSection>

        <SettingsSection
          title={t("settings.section_predictions")}
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          }
        >
          <div className="ai-settings-row ai-settings-row--toggle">
            <input
              type="checkbox"
              id="ai-settings-live-mode"
              checked={liveModeEnabled}
              onChange={() => setLiveModeEnabled((p) => !p)}
            />
            <label htmlFor="ai-settings-live-mode">{t("settings.live_mode_enabled")}</label>
          </div>
          <div className="ai-settings-row">
            <label className="ai-settings-label">{t("settings.default_analysis_mode")}</label>
            <select
              className="ai-select"
              value={defaultAnalysisMode}
              onChange={(e) => setDefaultAnalysisMode(e.target.value)}
              aria-label={t("settings.default_analysis_mode")}
            >
              <option value="pregame">{t("settings.mode_pregame")}</option>
              <option value="live">{t("settings.mode_live")}</option>
            </select>
          </div>
          <div className="ai-settings-row ai-settings-row--toggle">
            <input
              type="checkbox"
              id="ai-settings-no-pred-explanations"
              checked={showNoPredictionExplanations}
              onChange={() => setShowNoPredictionExplanations((p) => !p)}
            />
            <label htmlFor="ai-settings-no-pred-explanations">{t("settings.show_no_prediction_explanations")}</label>
          </div>
        </SettingsSection>

        <SettingsSection
          title={t("settings.section_data")}
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
          }
        >
          <div className="ai-settings-row ai-settings-row--toggle">
            <input
              type="checkbox"
              id="ai-settings-keep-history"
              checked={keepHistory}
              onChange={() => setKeepHistory((p) => !p)}
            />
            <label htmlFor="ai-settings-keep-history">{t("settings.keep_history")}</label>
          </div>
          <div className="ai-settings-row">
            <button
              type="button"
              className="ai-btn ai-btn--ghost"
              onClick={handleClearHistory}
              aria-label={t("settings.clear_history")}
            >
              {t("settings.clear_history")}
            </button>
          </div>
          <div className="ai-settings-row ai-settings-row--toggle">
            <input
              type="checkbox"
              id="ai-settings-auto-load"
              checked={autoLoadLast}
              onChange={() => setAutoLoadLast((p) => !p)}
            />
            <label htmlFor="ai-settings-auto-load">{t("settings.auto_load_last")}</label>
          </div>
          <div className="ai-settings-row">
            <span className="ai-settings-meta">{t("settings.export_template")}</span>
            <span className="ai-muted" style={{ fontSize: 12 }}>{t("settings.preview")}: {preview}</span>
          </div>
        </SettingsSection>

        <SettingsSection
          title={t("settings.section_appearance")}
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
          }
        >
          <div className="ai-settings-row">
            <label className="ai-settings-label">{t("settings.theme")}</label>
            <select className="ai-select" disabled aria-label={t("settings.theme")}>
              <option value="dark">{t("settings.theme_dark")}</option>
            </select>
          </div>
          <div className="ai-settings-row">
            <label className="ai-settings-label">{t("settings.layout_density")}</label>
            <div className="ai-settings-density">
              <button
                type="button"
                className={`ai-btn ai-btn--ghost ${layoutDensity === "compact" ? "ai-btn--active" : ""}`}
                onClick={() => setLayoutDensity("compact")}
                aria-pressed={layoutDensity === "compact"}
              >
                {t("settings.density_compact")}
              </button>
              <button
                type="button"
                className={`ai-btn ai-btn--ghost ${layoutDensity === "comfortable" ? "ai-btn--active" : ""}`}
                onClick={() => setLayoutDensity("comfortable")}
                aria-pressed={layoutDensity === "comfortable"}
              >
                {t("settings.density_comfortable")}
              </button>
            </div>
          </div>
        </SettingsSection>
      </div>
    </div>
  );
}
