/**
 * Home dashboard — category selector only.
 * No backend status, no analysis content; just navigation into sections.
 */
import { t } from "../../i18n";
import HomeActionCard, { type HomeCardTone } from "./HomeActionCard";

export type HomeNavigateView = "NEW_PREDICTION" | "SUMMARY" | "HISTORY" | "SETTINGS";

export interface HomeScreenProps {
  onNavigate?: (view: HomeNavigateView) => void;
}

function buildIcon(path: string) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={path} />
    </svg>
  );
}

export default function HomeScreen({ onNavigate }: HomeScreenProps) {
  const cards: Array<{
    key: HomeCardTone;
    title: string;
    description: string;
    iconPath: string;
    view: HomeNavigateView;
  }> = [
    {
      key: "predictions",
      title: t("nav.predictions"),
      description: t("home.category_predictions_desc"),
      iconPath: "M3 12l4-2 4 2 4-2 4 2v6H3z",
      view: "NEW_PREDICTION",
    },
    {
      key: "history",
      title: t("nav.history"),
      description: t("home.category_history_desc"),
      iconPath: "M3 5h18M7 3v4M17 3v4M5 9h14v10H5z",
      view: "HISTORY",
    },
    {
      key: "statistics",
      title: t("nav.statistics"),
      description: t("home.category_statistics_desc"),
      iconPath: "M4 19V9m5 10V5m5 14V11m5 8V7",
      view: "SUMMARY",
    },
    {
      key: "settings",
      title: t("nav.settings"),
      description: t("home.category_settings_desc"),
      iconPath: "M12 8a4 4 0 1 0 4 4 4 4 0 0 0-4-4zm8.66 1.5-1.73-.29a6.9 6.9 0 0 0-.84-2.03l1.02-1.43-1.66-1.66-1.43 1.02a6.9 6.9 0 0 0-2.03-.84L13.5 2.34 12 2l-1.5.34-.29 1.73a6.9 6.9 0 0 0-2.03.84L6.75 3.89 5.09 5.55l1.02 1.43a6.9 6.9 0 0 0-.84 2.03L3.54 9.5 3.2 11l.34 1.5 1.73.29a6.9 6.9 0 0 0 .84 2.03l-1.02 1.43 1.66 1.66 1.43-1.02a6.9 6.9 0 0 0 2.03.84l.29 1.73L12 21l1.5-.34.29-1.73a6.9 6.9 0 0 0 2.03-.84l1.43 1.02 1.66-1.66-1.02-1.43a6.9 6.9 0 0 0 .84-2.03l1.73-.29L20.8 11z",
      view: "SETTINGS",
    },
  ];

  return (
    <div className="ai-home">
      <div className="ai-home-grid">
        {cards.map((card) => (
          <HomeActionCard
            key={card.key}
            tone={card.key}
            title={card.title}
            description={card.description}
            icon={buildIcon(card.iconPath)}
            onClick={() => onNavigate?.(card.view)}
          />
        ))}
      </div>
    </div>
  );
}
