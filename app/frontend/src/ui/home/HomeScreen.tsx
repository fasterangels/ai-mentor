/**
 * Home screen (Αρχική) — welcome header + 2x2 action cards. Navigation wired via onNavigate.
 */
import { t } from "../../i18n";
import HomeActionCard from "./HomeActionCard";

export type HomeNavigateView = "NEW_PREDICTION" | "RESULT" | "SUMMARY" | "HISTORY";

export interface HomeScreenProps {
  onNavigate?: (view: HomeNavigateView) => void;
}

export default function HomeScreen({ onNavigate }: HomeScreenProps) {
  return (
    <div className="ai-home">
      <header className="ai-home-header">
        <h2 className="ai-home-title">{t("home.welcome_title")}</h2>
        <p className="ai-home-subtitle">{t("home.welcome_subtitle")}</p>
      </header>
      <div className="ai-home-grid">
        <HomeActionCard
          title={t("home.card_new_prediction_title")}
          description={t("home.card_new_prediction_desc")}
          buttonLabel={t("home.card_new_prediction_btn")}
          primary
          onClick={() => onNavigate?.("NEW_PREDICTION")}
        />
        <HomeActionCard
          title={t("home.card_result_title")}
          description={t("home.card_result_desc")}
          buttonLabel={t("home.card_result_btn")}
          onClick={() => onNavigate?.("RESULT")}
        />
        <HomeActionCard
          title={t("home.card_summary_title")}
          description={t("home.card_summary_desc")}
          buttonLabel={t("home.card_summary_btn")}
          onClick={() => onNavigate?.("SUMMARY")}
        />
        <HomeActionCard
          title={t("home.card_history_title")}
          description={t("home.card_history_desc")}
          buttonLabel={t("home.card_history_btn")}
          onClick={() => onNavigate?.("HISTORY")}
        />
      </div>
    </div>
  );
}
