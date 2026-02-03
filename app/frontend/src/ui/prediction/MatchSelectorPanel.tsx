import React from "react";
import { t } from "../../i18n";
import SegmentedControl from "./SegmentedControl";

export type PredictionMode = "PREGAME" | "LIVE";

export interface MatchSelectorPanelProps {
  mode: PredictionMode;
  onModeChange: (mode: PredictionMode) => void;
  league: string;
  onLeagueChange: (value: string) => void;
  homeTeam: string;
  onHomeTeamChange: (value: string) => void;
  awayTeam: string;
  onAwayTeamChange: (value: string) => void;
  dateTime: string;
  onDateTimeChange: (value: string) => void;
  disabled?: boolean;
}

export default function MatchSelectorPanel({
  mode,
  onModeChange,
  league,
  onLeagueChange,
  homeTeam,
  onHomeTeamChange,
  awayTeam,
  onAwayTeamChange,
  dateTime,
  onDateTimeChange,
  disabled,
}: MatchSelectorPanelProps) {
  const isLive = mode === "LIVE";

  return (
    <section className="ai-matchPanel" aria-label={t("analysis.title")}>
      <header className="ai-matchPanel__header">
        <div>
          <h2 className="ai-matchPanel__title">{t("analysis.title")}</h2>
          <p className="ai-matchPanel__subtitle">{t("home.welcome_title")}</p>
        </div>
        <SegmentedControl
          value={mode}
          onChange={(value) => onModeChange(value as PredictionMode)}
          options={[
            { value: "PREGAME", label: t("predictions.mode_pregame") },
            { value: "LIVE", label: t("predictions.mode_live") },
          ]}
          aria-label={t("predictions.mode_pregame")}
        />
      </header>

      <div className="ai-matchPanel__body">
        <div className="ai-matchPanel__row">
          <label className="ai-label">
            <span>{t("predictions.league_label")}</span>
            <select
              className="ai-select"
              value={league}
              onChange={(e) => onLeagueChange(e.target.value)}
              disabled={disabled}
            >
              <option value="Super League">Super League</option>
              <option value="Premier League">Premier League</option>
              <option value="Champions League">Champions League</option>
            </select>
          </label>
        </div>

        <div className="ai-matchPanel__row ai-matchPanel__row--teams">
          <label htmlFor="ai-mentor-home" className="ai-label">
            {t("predictions.home_team")}
          </label>
          <input
            id="ai-mentor-home"
            className="ai-input"
            value={homeTeam}
            onChange={(e) => onHomeTeamChange(e.target.value)}
            placeholder={t("analysis.home_team_placeholder")}
            disabled={disabled}
            aria-label={t("predictions.home_team")}
          />
          <span className="ai-matchPanel__vs">vs</span>
          <label htmlFor="ai-mentor-away" className="ai-label">
            {t("predictions.away_team")}
          </label>
          <input
            id="ai-mentor-away"
            className="ai-input"
            value={awayTeam}
            onChange={(e) => onAwayTeamChange(e.target.value)}
            placeholder={t("analysis.away_placeholder")}
            disabled={disabled}
            aria-label={t("predictions.away_team")}
          />
        </div>

        <div className="ai-matchPanel__row ai-matchPanel__row--datetime">
          <label htmlFor="ai-mentor-datetime" className="ai-label">
            {t("predictions.date_label")}
          </label>
          <input
            id="ai-mentor-datetime"
            type="datetime-local"
            className="ai-input ai-matchPanel__datetime"
            value={isLive ? "" : dateTime}
            onChange={(e) => onDateTimeChange(e.target.value)}
            disabled={disabled || isLive}
          />
          {isLive && (
            <span className="ai-matchPanel__liveHelper">
              {t("predictions.live_helper")}
            </span>
          )}
        </div>
      </div>
    </section>
  );
}

